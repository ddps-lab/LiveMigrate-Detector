package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

type QueueValue struct {
	vcpu     int
	instance string
}

var (
	MAX_THREADS = 50

	instanceTypeLimit = map[*regexp.Regexp]int{
		regexp.MustCompile(`^dl\d`):                  192,
		regexp.MustCompile(`^f\d`):                   256,
		regexp.MustCompile(`^(g|vt)\d`):              500,
		regexp.MustCompile(`^inf\d`):                 500,
		regexp.MustCompile(`^(p2|p3|p4)\d`):          500,
		regexp.MustCompile(`^p5\d`):                  192,
		regexp.MustCompile(`^(a|c|d|h|i|m|r|t|z)\d`): 800,
		regexp.MustCompile(`^tm\d`):                  256,
		regexp.MustCompile(`^x\d`):                   128,
	}
	queue      []*QueueValue
	lock       sync.Mutex
	cond       = sync.NewCond(&lock)
	httpClient = &http.Client{
		Timeout: 10 * time.Second,
	}
)

// const amiID = "ami-0a7d80731ae1b2435"

const amiID = "ami-0b05d988257befbbe"

// const amiID = "ami-043b59f1d11f8f189"

// const amiID = "ami-0ec1bf4a8f92e7bd1"

// createSecurityGroup 함수는 8080 포트를 개방하는 보안 그룹을 생성합니다.
func createSecurityGroup(client *ec2.Client) (*ec2.CreateSecurityGroupOutput, error) {
	groupName := fmt.Sprintf("spot-sg-%d", time.Now().Unix())
	sgInput := &ec2.CreateSecurityGroupInput{
		GroupName:   aws.String(groupName),
		Description: aws.String("Allow port 8080 for spot instance web server"),
	}
	sgResult, err := client.CreateSecurityGroup(context.TODO(), sgInput)
	if err != nil {
		return nil, err
	}

	// Ingress 규칙 추가
	_, err = client.AuthorizeSecurityGroupIngress(context.TODO(), &ec2.AuthorizeSecurityGroupIngressInput{
		GroupId: sgResult.GroupId,
		IpPermissions: []types.IpPermission{
			{
				IpProtocol: aws.String("tcp"),
				FromPort:   aws.Int32(0),
				ToPort:     aws.Int32(65535),
				IpRanges: []types.IpRange{
					{
						CidrIp: aws.String("0.0.0.0/0"),
					},
				},
			},
		},
	})
	if err != nil {
		// 규칙 추가 실패 시 생성된 보안 그룹 삭제
		client.DeleteSecurityGroup(context.TODO(), &ec2.DeleteSecurityGroupInput{GroupId: sgResult.GroupId})
		return nil, err
	}

	return sgResult, nil
}

// getUserDataScript 함수는 인스턴스 시작 시 실행될 셸 스크립트를 반환합니다.
func getUserDataScript() string {
	script := `#!/bin/bash
set -ex
apt update && apt install -y git
git clone https://github.com/ddps-lab/LiveMigrate-Detector.git
cd LiveMigrate-Detector
git checkout fix
cd cpu_feature_collector
./collector > output.txt
nohup python3 -m http.server 8080 &
`
	return base64.StdEncoding.EncodeToString([]byte(script))
}

// requestSpotInstance 함수는 스팟 인스턴스를 요청합니다.
func requestSpotInstance(client *ec2.Client, instanceType types.InstanceType, securityGroupID, userData string) (*ec2.RequestSpotInstancesOutput, error) {
	return client.RequestSpotInstances(context.TODO(), &ec2.RequestSpotInstancesInput{
		InstanceCount:                aws.Int32(1),
		Type:                         types.SpotInstanceTypeOneTime, // 일회성 요청
		InstanceInterruptionBehavior: types.InstanceInterruptionBehaviorTerminate,
		LaunchSpecification: &types.RequestSpotLaunchSpecification{
			ImageId:      aws.String(amiID),
			InstanceType: instanceType, // 저렴한 인스턴스 타입
			SecurityGroupIds: []string{
				securityGroupID,
			},
			UserData: aws.String(userData),
			BlockDeviceMappings: []types.BlockDeviceMapping{
				{
					DeviceName: aws.String("/dev/sda1"),
					Ebs: &types.EbsBlockDevice{
						VolumeSize:          aws.Int32(8),        // 8GB로 크기 지정
						VolumeType:          types.VolumeTypeGp2, // 가장 일반적이고 저렴한 SSD 타입 중 하나
						DeleteOnTermination: aws.Bool(true),      // 인스턴스 종료 시 EBS 볼륨도 함께 삭제 (중요!)
					},
				},
			},
		},
		ValidUntil: aws.Time(time.Now().Add(5 * time.Minute)),
	})
}

func Must[T any](val T, err error) T {
	if err != nil {
		panic(err)
	}
	return val
}

func getInstanceType(instance string) *regexp.Regexp {
	for k := range instanceTypeLimit {
		if k.MatchString(instance) {
			return k
		}
	}
	return nil
}

func getInstance() *QueueValue {
	lock.Lock()
	defer lock.Unlock()

	for len(queue) > 0 {
		for i := 0; i < len(queue); i++ {
			v := queue[i]
			instanceType := getInstanceType(v.instance)
			if instanceType == nil || instanceTypeLimit[instanceType] >= v.vcpu {
				queue = append(queue[:i], queue[i+1:]...)
				i--

				if _, err := os.Stat(fmt.Sprintf("result/%s.csv", v.instance)); err == nil {
					log.Printf("instance %s is already collected\n", v.instance)
				} else if instanceType != nil {
					log.Printf("instance %s is available\n", v.instance)
					instanceTypeLimit[instanceType] -= v.vcpu
					return v
				} else {
					log.Printf("instance type %s not found\n", v.instance)
				}
			} else {
				// log.Printf("instance %s is not available because of resource limit\n", v.instance)
			}
		}
		cond.Wait()
	}

	return nil
}

func releaseInstance(v *QueueValue) {
	lock.Lock()
	defer lock.Unlock()

	instanceType := getInstanceType(v.instance)
	if instanceType == nil {
		panic(fmt.Sprintf("instance type not found: %s", v.instance))
	}
	instanceTypeLimit[instanceType] += v.vcpu
	if len(queue) == 0 {
		cond.Broadcast()
	} else {
		cond.Signal()
	}
	log.Printf("instance %s is released\n", v.instance)
}

func run(client *ec2.Client, securityGroupID *string) {
	for {
		instance := getInstance()
		if instance == nil {
			break
		}

		result, err := requestSpotInstance(client, types.InstanceType(instance.instance), *securityGroupID, getUserDataScript())
		if err != nil {
			log.Printf("Failed to request spot instance: %v\n", err)
			releaseInstance(instance)
			continue
		}
		spotRequestID := *result.SpotInstanceRequests[0].SpotInstanceRequestId

		waiter := ec2.NewSpotInstanceRequestFulfilledWaiter(client)
		describeSpotReqInput := &ec2.DescribeSpotInstanceRequestsInput{
			SpotInstanceRequestIds: []string{spotRequestID},
		}
		err = waiter.Wait(context.TODO(), describeSpotReqInput, 5*time.Minute)
		if err != nil {
			log.Printf("Spot instance request wait timeout: %v\n", err)
			releaseInstance(instance)
			continue
		}

		descSpotReq, err := client.DescribeSpotInstanceRequests(context.TODO(), describeSpotReqInput)
		if err != nil || len(descSpotReq.SpotInstanceRequests) == 0 {
			log.Printf("Failed to get instance ID: %v\n", err)
			releaseInstance(instance)
			continue
		}
		instanceID := *descSpotReq.SpotInstanceRequests[0].InstanceId

		featureResult := func() []byte {
			defer func() {
				if _, err := client.TerminateInstances(context.TODO(), &ec2.TerminateInstancesInput{
					InstanceIds: []string{instanceID},
				}); err != nil {
					log.Printf("Failed to terminate instance: %v\n", err)
				}
			}()

			instanceWaiter := ec2.NewInstanceRunningWaiter(client)
			describeInstanceInput := &ec2.DescribeInstancesInput{
				InstanceIds: []string{instanceID},
			}
			err = instanceWaiter.Wait(context.TODO(), describeInstanceInput, 5*time.Minute)
			if err != nil {
				log.Printf("Instance did not reach 'running' state: %v\n", err)
				return nil
			}

			descInstances, err := client.DescribeInstances(context.TODO(), describeInstanceInput)
			if err != nil || len(descInstances.Reservations) == 0 || len(descInstances.Reservations[0].Instances) == 0 {
				log.Printf("Failed to get instance information: %v\n", err)
				return nil
			}
			publicIP := *descInstances.Reservations[0].Instances[0].PublicIpAddress

			outputURL := fmt.Sprintf("http://%s:8080/output.txt", publicIP)
			log.Printf("Fetching result file from '%s'...", outputURL)

			var outputContent []byte
			for i := 0; i < 30; i++ { // Maximum 5 minutes (30 * 10 seconds)
				time.Sleep(10 * time.Second)
				log.Printf("Attempting to fetch result file (%d/30)...", i+1)

				resp, err := httpClient.Get(outputURL)
				if err == nil && resp.StatusCode == http.StatusOK {
					defer resp.Body.Close()
					outputContent, err = io.ReadAll(resp.Body)
					if err == nil {
						log.Println("Successfully fetched result file!")
						break
					}
				}
			}

			if outputContent == nil {
				log.Printf("Failed to fetch result file.\n")
				return nil
			}

			return outputContent
		}()

		if len(featureResult) != 0 {
			os.WriteFile(fmt.Sprintf("result/%s.csv", instance.instance), featureResult, 0644)
		}

		// ec2 instance start
		releaseInstance(instance)
	}
}

func main() {
	b, err := os.ReadFile("../../crawler/cpu-instance.json")
	if err != nil {
		panic(err)
	}

	var data map[string][]map[string]string
	if err := json.Unmarshal(b, &data); err != nil {
		panic(err)
	}

	re := regexp.MustCompile(`[0-9]`)
	for cpu, instances := range data {
		if !re.MatchString(cpu) {
			continue
		}
		for _, instance := range instances {
			queue = append(queue, &QueueValue{
				vcpu:     Must(strconv.Atoi(instance["vcpu"])),
				instance: instance["instance"],
			})
		}
	}

	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		panic(err)
	}
	// cfg.Region = "us-east-1"
	cfg.Region = "us-east-2"
	// cfg.Region = "us-west-1"
	// cfg.Region = "us-west-2"
	client := ec2.NewFromConfig(cfg)

	sgResult, err := createSecurityGroup(client)
	if err != nil {
		panic(err)
	}
	securityGroupID := sgResult.GroupId

	defer func() {
		if _, err := client.DeleteSecurityGroup(context.TODO(), &ec2.DeleteSecurityGroupInput{
			GroupId: securityGroupID,
		}); err != nil {
			panic(err)
		}
	}()

	var wg sync.WaitGroup
	for range MAX_THREADS {
		wg.Add(1)
		go func() {
			defer wg.Done()
			run(client, securityGroupID)
		}()
	}
	wg.Wait()
}
