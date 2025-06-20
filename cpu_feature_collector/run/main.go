package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"regexp"
	"strconv"
	"sync"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

type QueueValue struct {
	vcpu     int
	instance string
}

var (
	MAX_THREADS = 32

	instanceTypeLimit = map[*regexp.Regexp]int{
		regexp.MustCompile(`^dl\d`):                  192,
		regexp.MustCompile(`^f\d`):                   256,
		regexp.MustCompile(`^(g|vt)\d`):              1000,
		regexp.MustCompile(`^inf\d`):                 1000,
		regexp.MustCompile(`^(p2|p3|p4)\d`):          1000,
		regexp.MustCompile(`^p5\d`):                  192,
		regexp.MustCompile(`^(a|c|d|h|i|m|r|t|z)\d`): 1600,
		regexp.MustCompile(`^tm\d`):                  256,
		regexp.MustCompile(`^x\d`):                   128,
	}
	queue []*QueueValue
	lock  sync.Mutex
	cond  = sync.NewCond(&lock)
)

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

				if instanceType != nil {
					log.Printf("instance %s is available\n", v.instance)
					instanceTypeLimit[instanceType] -= v.vcpu
					return v
				} else {
					log.Printf("instance type %s not found\n", v.instance)
				}
			} else {
				log.Printf("instance %s is not available because of resource limit\n", v.instance)
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
			panic(err)
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
