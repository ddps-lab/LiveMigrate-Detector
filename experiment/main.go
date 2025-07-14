package main

import (
	"archive/tar"
	"bufio"
	"compress/gzip"
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"github.com/aws/aws-sdk-go-v2/service/ec2/types"
	"github.com/aws/aws-sdk-go-v2/service/servicequotas"
)

// =====================================================
// 설정 상수들 - 여기서 쉽게 변경 가능
// =====================================================
const (
	AWS_REGION = "us-west-2" // AWS 리전
	USE_SPOT   = true        // 스팟 인스턴스 사용 여부

	AMI_ID = "ami-0dddef6e36aee75f7" // Ubuntu 22.04 LTS + 0-ami.sh (1-collect-info)

	// DISK_SIZE int32 = 32 // 1-collect-info
	DISK_SIZE int32 = 140 // 2-restore-check

	MAX_THREADS                 = 47               // 최대 동시 실행 스레드 수
	SPOT_REQUEST_TIMEOUT        = 5 * time.Hour    // 스팟 인스턴스 요청 유효시간 (긴 실험 대응)
	INSTANCE_START_TIMEOUT      = 1 * time.Minute  // 인스턴스 시작 대기 시간
	EXPERIMENT_MAX_TIMEOUT      = 5 * time.Hour    // 실험 최대 실행 시간
	RESULT_CHECK_INTERVAL       = 30 * time.Second // 결과 확인 간격
	SECURITY_GROUP_WAIT_TIMEOUT = 10 * time.Minute // Security Group 삭제 대기 시간
	HTTP_CLIENT_TIMEOUT         = 30 * time.Minute // HTTP 클라이언트 타임아웃
)

// =====================================================
// 타입 정의들
// =====================================================
type QueueValue struct {
	instance string
}

type ExperimentManager struct {
	ec2Client         *ec2.Client
	cfg               aws.Config
	instanceTypeLimit map[*regexp.Regexp]int
	vCPUCache         map[string]int32
	vCPUCacheMutex    sync.Mutex
	httpClient        *http.Client
	scriptContent     string
	scriptFileName    string
	allInstanceIDs    []string
	instanceIDsMutex  sync.Mutex
}

type QuotaManager struct {
	queue []*QueueValue
	lock  sync.Mutex
	cond  *sync.Cond
}

func NewQuotaManager() *QuotaManager {
	qm := &QuotaManager{
		queue: make([]*QueueValue, 0),
	}
	qm.cond = sync.NewCond(&qm.lock)
	return qm
}

// =====================================================
// 전역 변수들 (최소화)
// =====================================================
var (
	experimentManager *ExperimentManager
	quotaManager      *QuotaManager
)

// =====================================================
// 유틸리티 함수들
// =====================================================

// Type conversion utilities
func toInstanceTypeSlice(instanceTypes []string) []types.InstanceType {
	result := make([]types.InstanceType, len(instanceTypes))
	for i, it := range instanceTypes {
		result[i] = types.InstanceType(it)
	}
	return result
}

// getFileNameWithoutExt returns filename without extension
func getFileNameWithoutExt(filename string) string {
	base := filepath.Base(filename)
	ext := filepath.Ext(base)
	return strings.TrimSuffix(base, ext)
}

// safeHTTPGet safely performs HTTP GET request with proper cleanup
func safeHTTPGet(url string) ([]byte, error) {
	if experimentManager == nil || experimentManager.httpClient == nil {
		return nil, fmt.Errorf("experiment manager not initialized")
	}

	resp, err := experimentManager.httpClient.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	return io.ReadAll(resp.Body)
}

// extractTarGz extracts tar.gz archive to specified directory
func extractTarGz(src []byte, destDir string) error {
	gzipReader, err := gzip.NewReader(strings.NewReader(string(src)))
	if err != nil {
		return fmt.Errorf("failed to create gzip reader: %w", err)
	}
	defer gzipReader.Close()

	tarReader := tar.NewReader(gzipReader)

	for {
		header, err := tarReader.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			return fmt.Errorf("failed to read tar entry: %w", err)
		}

		destPath := filepath.Join(destDir, header.Name)

		switch header.Typeflag {
		case tar.TypeDir:
			if err := os.MkdirAll(destPath, 0755); err != nil {
				return fmt.Errorf("failed to create directory %s: %w", destPath, err)
			}
		case tar.TypeReg:
			if err := os.MkdirAll(filepath.Dir(destPath), 0755); err != nil {
				return fmt.Errorf("failed to create parent directory for %s: %w", destPath, err)
			}

			outFile, err := os.Create(destPath)
			if err != nil {
				return fmt.Errorf("failed to create file %s: %w", destPath, err)
			}

			if _, err := io.Copy(outFile, tarReader); err != nil {
				outFile.Close()
				return fmt.Errorf("failed to extract file %s: %w", destPath, err)
			}
			outFile.Close()

			if err := os.Chmod(destPath, os.FileMode(header.Mode)); err != nil {
				log.Printf("Warning: failed to set permissions for %s: %v", destPath, err)
			}
		}
	}

	return nil
}

// =====================================================
// ExperimentManager 메서드들
// =====================================================

func NewExperimentManager() (*ExperimentManager, error) {
	cfg, err := config.LoadDefaultConfig(context.TODO())
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}
	cfg.Region = AWS_REGION

	return &ExperimentManager{
		ec2Client:         ec2.NewFromConfig(cfg),
		cfg:               cfg,
		instanceTypeLimit: make(map[*regexp.Regexp]int),
		vCPUCache:         make(map[string]int32),
		httpClient:        &http.Client{Timeout: HTTP_CLIENT_TIMEOUT},
		allInstanceIDs:    make([]string, 0),
	}, nil
}

func (em *ExperimentManager) SetScript(scriptContent, scriptFileName string) {
	em.scriptContent = scriptContent
	em.scriptFileName = scriptFileName
}

func (em *ExperimentManager) AddInstanceID(instanceID string) {
	em.instanceIDsMutex.Lock()
	defer em.instanceIDsMutex.Unlock()
	em.allInstanceIDs = append(em.allInstanceIDs, instanceID)
}

// batchGetVCPUs gets vCPU counts for multiple instance types in a single API call
func (em *ExperimentManager) batchGetVCPUs(instanceTypes []string) (map[string]int32, error) {
	em.vCPUCacheMutex.Lock()
	defer em.vCPUCacheMutex.Unlock()

	// Check cache and collect uncached types
	result := make(map[string]int32)
	var uncachedTypes []string

	for _, instanceType := range instanceTypes {
		if vCPU, exists := em.vCPUCache[instanceType]; exists {
			result[instanceType] = vCPU
		} else {
			uncachedTypes = append(uncachedTypes, instanceType)
		}
	}

	// Query AWS for uncached types
	if len(uncachedTypes) > 0 {
		awsResult, err := em.ec2Client.DescribeInstanceTypes(context.TODO(), &ec2.DescribeInstanceTypesInput{
			InstanceTypes: toInstanceTypeSlice(uncachedTypes),
		})
		if err != nil {
			return nil, fmt.Errorf("failed to describe instance types: %w", err)
		}

		for _, instanceTypeInfo := range awsResult.InstanceTypes {
			instanceType := string(instanceTypeInfo.InstanceType)
			if instanceTypeInfo.VCpuInfo != nil {
				vCPU := *instanceTypeInfo.VCpuInfo.DefaultVCpus
				em.vCPUCache[instanceType] = vCPU
				result[instanceType] = vCPU
			}
		}
	}

	// Ensure all requested instance types have vCPU info
	for _, instanceType := range instanceTypes {
		if _, exists := result[instanceType]; !exists {
			return nil, fmt.Errorf("vCPU info not found for instance type: %s", instanceType)
		}
	}
	return result, nil
}

// getInstanceVCPU gets vCPU count for a specific instance type with caching
func (em *ExperimentManager) getInstanceVCPU(instanceType string) (int32, error) {
	vCPUs, err := em.batchGetVCPUs([]string{instanceType})
	if err != nil {
		return 0, fmt.Errorf("failed to get vCPU for %s: %w", instanceType, err)
	}

	if vCPU, exists := vCPUs[instanceType]; exists {
		return vCPU, nil
	}

	// This should theoretically not be reached due to the check in batchGetVCPUs
	return 0, fmt.Errorf("vCPU info not found for %s after batch get", instanceType)
}

// getInstanceFamily finds the regex pattern that matches the instance type
func (em *ExperimentManager) getInstanceFamily(instanceType string) *regexp.Regexp {
	for pattern := range em.instanceTypeLimit {
		if pattern.MatchString(instanceType) {
			return pattern
		}
	}
	return nil
}

// =====================================================
// AWS 설정 및 초기화 함수들
// =====================================================

// createSecurityGroup creates a security group that allows all traffic
func createSecurityGroup(client *ec2.Client) (*ec2.CreateSecurityGroupOutput, error) {
	groupName := fmt.Sprintf("experiment-sg-%d", time.Now().Unix())
	sgInput := &ec2.CreateSecurityGroupInput{
		GroupName:   aws.String(groupName),
		Description: aws.String("Allow all traffic for experiment"),
	}

	sgResult, err := client.CreateSecurityGroup(context.TODO(), sgInput)
	if err != nil {
		return nil, fmt.Errorf("failed to create security group: %w", err)
	}

	// Add ingress rules
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
		// Delete security group if rule addition fails
		client.DeleteSecurityGroup(context.TODO(), &ec2.DeleteSecurityGroupInput{GroupId: sgResult.GroupId})
		return nil, fmt.Errorf("failed to add ingress rules: %w", err)
	}

	log.Printf("Created security group: %s", *sgResult.GroupId)
	return sgResult, nil
}

// waitForInstanceTermination waits for all instances to be terminated
func waitForInstanceTermination(client *ec2.Client) {
	if len(experimentManager.allInstanceIDs) == 0 {
		return
	}

	log.Printf("Waiting for %d instances to terminate before deleting security group...", len(experimentManager.allInstanceIDs))

	ctx, cancel := context.WithTimeout(context.Background(), SECURITY_GROUP_WAIT_TIMEOUT)
	defer cancel()

	waiter := ec2.NewInstanceTerminatedWaiter(client)
	describeInput := &ec2.DescribeInstancesInput{
		InstanceIds: experimentManager.allInstanceIDs,
	}

	if err := waiter.Wait(ctx, describeInput, SECURITY_GROUP_WAIT_TIMEOUT); err != nil {
		log.Printf("Warning: Some instances may not have terminated within timeout: %v", err)
	} else {
		log.Println("All instances have been terminated")
	}
}

// deleteSecurityGroupSafely deletes security group after waiting for instances to terminate
func deleteSecurityGroupSafely(client *ec2.Client, securityGroupID *string) {
	waitForInstanceTermination(client)

	if _, err := client.DeleteSecurityGroup(context.TODO(), &ec2.DeleteSecurityGroupInput{
		GroupId: securityGroupID,
	}); err != nil {
		log.Printf("Failed to delete security group: %v", err)
	} else {
		log.Printf("Successfully deleted security group: %s", *securityGroupID)
	}
}

// loadSpotQuotas loads spot instance quotas from AWS Service Quotas
func (em *ExperimentManager) loadSpotQuotas() error {
	log.Println("Loading spot instance quotas from AWS...")

	servicequotasClient := servicequotas.NewFromConfig(em.cfg)
	paginator := servicequotas.NewListServiceQuotasPaginator(servicequotasClient, &servicequotas.ListServiceQuotasInput{
		ServiceCode: aws.String("ec2"),
	})

	re := regexp.MustCompile(`\w+`)
	exclusions := map[string]bool{
		"All": true, "Spot": true, "Instance": true,
		"Requests": true, "Standard": true, "and": true,
	}

	quotaCount := 0
	for paginator.HasMorePages() {
		page, err := paginator.NextPage(context.TODO())
		if err != nil {
			return fmt.Errorf("failed to get service quotas: %w", err)
		}

		for _, quota := range page.Quotas {
			name := *quota.QuotaName
			if strings.Contains(name, "Spot Instance Requests") {
				var instances []string
				for _, match := range re.FindAllString(name, -1) {
					if _, ok := exclusions[match]; !ok {
						instances = append(instances, strings.ToLower(match))
					}
				}

				if len(instances) > 0 {
					quotaValue := int(*quota.Value)

					// Create regex pattern for instance families (e.g., "c" -> "^(c)\d?\." or "p2,p3,p4" -> "^(p2|p3|p4)\d?\.")
					pattern := regexp.MustCompile(fmt.Sprintf("^(%s)\\d*\\w*\\.", strings.Join(instances, "|")))

					em.instanceTypeLimit[pattern] = quotaValue
					log.Printf("  ├─ %s: %d (pattern: %s)", strings.Join(instances, ","), quotaValue, pattern.String())
					quotaCount++
				}
			}
		}
	}

	if quotaCount == 0 {
		return fmt.Errorf("no spot instance quotas found")
	}

	log.Printf("Successfully loaded quotas for %d instance families", quotaCount)
	return nil
}

// subtractRunningSpotInstances subtracts currently running spot instances from quotas based on vCPU
func (em *ExperimentManager) subtractRunningSpotInstances() error {
	log.Println("Checking currently running spot instances...")

	// Describe all running spot instances
	result, err := em.ec2Client.DescribeInstances(context.TODO(), &ec2.DescribeInstancesInput{
		Filters: []types.Filter{
			{
				Name:   aws.String("instance-state-name"),
				Values: []string{"running", "pending"},
			},
			{
				Name:   aws.String("instance-lifecycle"),
				Values: []string{"spot"},
			},
		},
	})
	if err != nil {
		return fmt.Errorf("failed to describe instances: %w", err)
	}

	// Collect unique instance types for vCPU lookup
	uniqueInstanceTypesMap := make(map[string]bool)
	var runningSpotInstances []struct {
		instanceType string
		pattern      *regexp.Regexp
	}

	for _, reservation := range result.Reservations {
		for _, instance := range reservation.Instances {
			instanceType := string(instance.InstanceType)
			uniqueInstanceTypesMap[instanceType] = true

			// Find matching pattern
			if pattern := em.getInstanceFamily(instanceType); pattern != nil {
				runningSpotInstances = append(runningSpotInstances, struct {
					instanceType string
					pattern      *regexp.Regexp
				}{instanceType, pattern})
				log.Printf("  ├─ Found running spot instance: %s (pattern: %s)", instanceType, pattern.String())
			} else {
				log.Printf("  ├─ Warning: No quota pattern found for running spot instance type %s", instanceType)
			}
		}
	}

	if len(runningSpotInstances) == 0 {
		log.Println("No running spot instances found")
		return nil
	}

	// Get vCPU information for instance types
	var uniqueInstanceTypes []string
	for instanceType := range uniqueInstanceTypesMap {
		uniqueInstanceTypes = append(uniqueInstanceTypes, instanceType)
	}

	vCPUMap, err := em.batchGetVCPUs(uniqueInstanceTypes)
	if err != nil {
		return fmt.Errorf("failed to get vCPU info for running instances: %w", err)
	}

	// Count running spot vCPUs by pattern
	runningSpotVCPUs := make(map[*regexp.Regexp]int32)
	totalSpotInstances := 0
	totalVCPUs := int32(0)

	for _, spotInstance := range runningSpotInstances {
		if vCPU, exists := vCPUMap[spotInstance.instanceType]; exists {
			runningSpotVCPUs[spotInstance.pattern] += vCPU
			totalVCPUs += vCPU
			totalSpotInstances++
			log.Printf("  ├─ %s: %d vCPUs", spotInstance.instanceType, vCPU)
		} else {
			// This case should not happen if batchGetVCPUs is correct
			log.Printf("  ├─ Warning: vCPU info not found for %s", spotInstance.instanceType)
		}
	}

	// Subtract vCPUs from quotas
	for pattern, vCPUCount := range runningSpotVCPUs {
		if em.instanceTypeLimit[pattern] >= int(vCPUCount) {
			em.instanceTypeLimit[pattern] -= int(vCPUCount)
			log.Printf("  ├─ Adjusted quota for pattern %s: -%d vCPUs (remaining: %d vCPUs)",
				pattern.String(), vCPUCount, em.instanceTypeLimit[pattern])
		} else {
			log.Printf("  ├─ Warning: Running vCPUs (%d) exceed quota (%d) for pattern %s",
				vCPUCount, em.instanceTypeLimit[pattern], pattern.String())
			em.instanceTypeLimit[pattern] = 0
		}
	}

	log.Printf("Found %d running spot instances using %d total vCPUs, quotas adjusted accordingly",
		totalSpotInstances, totalVCPUs)

	return nil
}

// =====================================================
// 인스턴스 관리 함수들
// =====================================================

// getUserDataScript returns the user data script to be executed on instance startup
func (em *ExperimentManager) getUserDataScript() string {
	// Base64 encode the user script to avoid issues with special characters
	encodedScript := base64.StdEncoding.EncodeToString([]byte(em.scriptContent))

	script := fmt.Sprintf(`#!/bin/bash
set -ex

# Create result directory
mkdir -p /home/ubuntu/result

# Decode and execute user script
echo '%s' | base64 -d > /home/ubuntu/user_script.sh
chmod +x /home/ubuntu/user_script.sh

# Execute user script and mark completion
cd /home/ubuntu
script -q -e -c './user_script.sh' /home/ubuntu/user_script.log
echo "EXPERIMENT_COMPLETED" > /home/ubuntu/experiment_status.txt

mv /home/ubuntu/user_script.log /home/ubuntu/result/user_script.log

# Create tar.gz archive of results
tar -czf result.tar.gz -C /home/ubuntu/result .

# Start HTTP server to serve the archive
nohup python3 -m http.server 8080 &
`, encodedScript)
	return base64.StdEncoding.EncodeToString([]byte(script))
}

// requestSpotInstance requests a spot instance
func requestSpotInstance(client *ec2.Client, instanceType types.InstanceType, securityGroupID, userData string) (*ec2.RequestSpotInstancesOutput, error) {
	return client.RequestSpotInstances(context.TODO(), &ec2.RequestSpotInstancesInput{
		InstanceCount:                aws.Int32(1),
		Type:                         types.SpotInstanceTypeOneTime,
		InstanceInterruptionBehavior: types.InstanceInterruptionBehaviorTerminate,
		LaunchSpecification: &types.RequestSpotLaunchSpecification{
			ImageId:          aws.String(AMI_ID),
			InstanceType:     instanceType,
			SecurityGroupIds: []string{securityGroupID},
			UserData:         aws.String(userData),
			BlockDeviceMappings: []types.BlockDeviceMapping{
				{
					DeviceName: aws.String("/dev/sda1"),
					Ebs: &types.EbsBlockDevice{
						VolumeSize:          aws.Int32(DISK_SIZE),
						VolumeType:          types.VolumeTypeGp2,
						DeleteOnTermination: aws.Bool(true),
					},
				},
			},
		},
		ValidUntil: aws.Time(time.Now().Add(SPOT_REQUEST_TIMEOUT)),
	})
}

// requestSpotInstanceAndWait requests a spot instance and waits for it to be fulfilled, returns instanceID
func requestSpotInstanceAndWait(client *ec2.Client, instanceType types.InstanceType, securityGroupID, userData string) (string, error) {
	log.Printf("Requesting spot instance for %s", instanceType)

	// Request spot instance
	result, err := requestSpotInstance(client, instanceType, securityGroupID, userData)
	if err != nil {
		return "", fmt.Errorf("failed to request spot instance: %w", err)
	}
	spotRequestID := *result.SpotInstanceRequests[0].SpotInstanceRequestId

	// Wait for spot request fulfillment
	waiter := ec2.NewSpotInstanceRequestFulfilledWaiter(client)
	describeSpotReqInput := &ec2.DescribeSpotInstanceRequestsInput{
		SpotInstanceRequestIds: []string{spotRequestID},
	}

	if err := waiter.Wait(context.TODO(), describeSpotReqInput, INSTANCE_START_TIMEOUT); err != nil {
		// Cancel the spot request before returning error
		_, cancelErr := client.CancelSpotInstanceRequests(context.TODO(), &ec2.CancelSpotInstanceRequestsInput{
			SpotInstanceRequestIds: []string{spotRequestID},
		})
		if cancelErr != nil {
			log.Printf("Warning: Failed to cancel spot request %s: %v", spotRequestID, cancelErr)
		} else {
			log.Printf("Cancelled spot request %s", spotRequestID)
		}
		return "", fmt.Errorf("spot instance request timeout: %w", err)
	}

	// Get instance ID
	descSpotReq, err := client.DescribeSpotInstanceRequests(context.TODO(), describeSpotReqInput)
	if err != nil || len(descSpotReq.SpotInstanceRequests) == 0 {
		return "", fmt.Errorf("failed to get instance ID from spot request: %w", err)
	}

	instanceID := *descSpotReq.SpotInstanceRequests[0].InstanceId
	log.Printf("✓ Spot instance fulfilled: %s", instanceID)
	return instanceID, nil
}

// requestOnDemandInstance requests an on-demand instance and returns instanceID
func requestOnDemandInstance(client *ec2.Client, instanceType types.InstanceType, securityGroupID, userData string) (string, error) {
	log.Printf("Requesting on-demand instance for %s", instanceType)

	result, err := client.RunInstances(context.TODO(), &ec2.RunInstancesInput{
		ImageId:          aws.String(AMI_ID),
		InstanceType:     instanceType,
		MinCount:         aws.Int32(1),
		MaxCount:         aws.Int32(1),
		SecurityGroupIds: []string{securityGroupID},
		UserData:         aws.String(userData),
		BlockDeviceMappings: []types.BlockDeviceMapping{
			{
				DeviceName: aws.String("/dev/sda1"),
				Ebs: &types.EbsBlockDevice{
					VolumeSize:          aws.Int32(DISK_SIZE),
					VolumeType:          types.VolumeTypeGp2,
					DeleteOnTermination: aws.Bool(true),
				},
			},
		},
	})
	if err != nil {
		return "", fmt.Errorf("failed to request on-demand instance: %w", err)
	}

	instanceID := *result.Instances[0].InstanceId
	log.Printf("✓ On-demand instance created: %s", instanceID)
	return instanceID, nil
}

// =====================================================
// 큐 관리 함수들
// =====================================================

func (qm *QuotaManager) getInstance() *QueueValue {
	qm.lock.Lock()
	defer qm.lock.Unlock()

	for len(qm.queue) > 0 {
		for i := 0; i < len(qm.queue); i++ {
			v := qm.queue[i]
			instanceFamily := experimentManager.getInstanceFamily(v.instance)

			if instanceFamily == nil {
				log.Printf("Warning: Unknown instance family for %s", v.instance)
				qm.queue = append(qm.queue[:i], qm.queue[i+1:]...)
				i--
				continue
			}

			// Get vCPU count for this instance type
			vCPU, err := experimentManager.getInstanceVCPU(v.instance)
			if err != nil {
				log.Printf("Error: Failed to get vCPU for %s, skipping: %v", v.instance, err)
				qm.queue = append(qm.queue[:i], qm.queue[i+1:]...)
				i--
				continue
			}

			if experimentManager.instanceTypeLimit[instanceFamily] >= int(vCPU) {
				qm.queue = append(qm.queue[:i], qm.queue[i+1:]...)
				i--

				log.Printf("Processing %s → pattern: %s, vCPUs: %d (available: %d)",
					v.instance, instanceFamily.String(), vCPU, experimentManager.instanceTypeLimit[instanceFamily])
				experimentManager.instanceTypeLimit[instanceFamily] -= int(vCPU)
				return v
			}
		}
		qm.cond.Wait()
	}

	return nil
}

func (qm *QuotaManager) releaseInstance(v *QueueValue) {
	qm.lock.Lock()
	defer qm.lock.Unlock()

	instanceFamily := experimentManager.getInstanceFamily(v.instance)
	if instanceFamily == nil {
		log.Printf("Error: Cannot release instance %s - unknown family", v.instance)
		return
	}

	// Get vCPU count for this instance type
	vCPU, err := experimentManager.getInstanceVCPU(v.instance)
	if err != nil {
		log.Printf("Error: Failed to get vCPU for %s on release: %v", v.instance, err)
		// Don't return quota if we can't determine vCPU count, to be safe
		return
	}
	experimentManager.instanceTypeLimit[instanceFamily] += int(vCPU)
	log.Printf("Released %s (pattern: %s, vCPUs: %d, available: %d)",
		v.instance, instanceFamily.String(), vCPU, experimentManager.instanceTypeLimit[instanceFamily])

	if len(qm.queue) == 0 {
		qm.cond.Broadcast()
	} else {
		qm.cond.Signal()
	}
}

// =====================================================
// 메인 실행 함수들
// =====================================================

func run(client *ec2.Client, securityGroupID *string) {
	for {
		instance := quotaManager.getInstance()
		if instance == nil {
			break
		}

		if shouldRelease := processInstance(client, instance, securityGroupID); shouldRelease {
			quotaManager.releaseInstance(instance)
		} else {
			log.Printf("Quota for %s will not be released because the instance did not terminate correctly.", instance.instance)
		}
	}
}

func processInstance(client *ec2.Client, instance *QueueValue, securityGroupID *string) bool {
	log.Printf("Starting instance request for %s", instance.instance)

	var instanceID string
	var err error

	if USE_SPOT {
		// Try spot instance, fallback to on-demand if it fails
		instanceID, err = requestSpotInstanceAndWait(client, types.InstanceType(instance.instance), *securityGroupID, experimentManager.getUserDataScript())
		if err != nil {
			log.Printf("Spot instance failed for %s: %v", instance.instance, err)
			log.Printf("Falling back to on-demand instance for %s", instance.instance)
		}
	}
	if len(instanceID) == 0 {
		instanceID, err = requestOnDemandInstance(client, types.InstanceType(instance.instance), *securityGroupID, experimentManager.getUserDataScript())
		if err != nil {
			log.Printf("On-demand instance failed for %s: %v", instance.instance, err)
			return true // No instance was created.
		}
	}

	// Track instance ID for cleanup
	experimentManager.AddInstanceID(instanceID)

	// Process the instance and download results
	downloadAndExtractResults(client, instance, instanceID)

	// Terminate instance and wait for it to be terminated
	log.Printf("Terminating instance %s (%s)", instance.instance, instanceID)
	if _, err := client.TerminateInstances(context.TODO(), &ec2.TerminateInstancesInput{
		InstanceIds: []string{instanceID},
	}); err != nil {
		log.Printf("Failed to initiate termination for instance %s: %v", instanceID, err)
		return false // Do NOT release quota.
	}

	log.Printf("Waiting for instance %s to terminate...", instance.instance)
	termWaiter := ec2.NewInstanceTerminatedWaiter(client)
	describeInput := &ec2.DescribeInstancesInput{InstanceIds: []string{instanceID}}

	const instanceTerminationTimeout = 5 * time.Minute
	ctx, cancel := context.WithTimeout(context.Background(), instanceTerminationTimeout)
	defer cancel()

	if err := termWaiter.Wait(ctx, describeInput, instanceTerminationTimeout); err != nil {
		log.Printf("Error waiting for instance %s to terminate: %v", instanceID, err)
		return false // Do NOT release quota.
	}

	log.Printf("Instance %s terminated successfully.", instance.instance)
	return true // OK to release quota.
}

func downloadAndExtractResults(client *ec2.Client, instance *QueueValue, instanceID string) bool {
	// Wait for instance to be running
	instanceWaiter := ec2.NewInstanceRunningWaiter(client)
	describeInstanceInput := &ec2.DescribeInstancesInput{
		InstanceIds: []string{instanceID},
	}

	err := instanceWaiter.Wait(context.TODO(), describeInstanceInput, INSTANCE_START_TIMEOUT)
	if err != nil {
		log.Printf("Instance %s did not reach running state: %v", instanceID, err)
		return false
	}

	// Get public IP
	descInstances, err := client.DescribeInstances(context.TODO(), describeInstanceInput)
	if err != nil || len(descInstances.Reservations) == 0 || len(descInstances.Reservations[0].Instances) == 0 {
		log.Printf("Failed to get instance information for %s: %v", instanceID, err)
		return false
	}
	publicIP := *descInstances.Reservations[0].Instances[0].PublicIpAddress

	// Wait for experiment to complete
	statusURL := fmt.Sprintf("http://%s:8080/experiment_status.txt", publicIP)
	resultURL := fmt.Sprintf("http://%s:8080/result.tar.gz", publicIP)
	log.Printf("Waiting for experiment to complete on %s...", instance.instance)

	ctx, cancel := context.WithTimeout(context.Background(), EXPERIMENT_MAX_TIMEOUT)
	defer cancel()

	ticker := time.NewTicker(RESULT_CHECK_INTERVAL)
	defer ticker.Stop()

	experimentStartTime := time.Now()

	for {
		select {
		case <-ctx.Done():
			log.Printf("  └─ ✗ Experiment timed out for %s", instance.instance)
			return false
		case <-ticker.C:
			// 인스턴스가 아직 실행 중인지 확인 (스팟 인스턴스 종료 대응)
			desc, err := client.DescribeInstances(ctx, &ec2.DescribeInstancesInput{
				InstanceIds: []string{instanceID},
			})
			if err != nil {
				log.Printf("  └─ ✗ Failed to check status for instance %s: %v. Retrying next cycle.", instanceID, err)
				continue
			}
			if len(desc.Reservations) == 0 || len(desc.Reservations[0].Instances) == 0 {
				log.Printf("  └─ ✗ Could not find instance %s(%s). Aborting experiment.", instance.instance, instanceID)
				return false
			}
			instanceState := desc.Reservations[0].Instances[0].State.Name
			if instanceState != types.InstanceStateNameRunning {
				log.Printf("  └─ ✗ Instance %s(%s) is no longer running (state: %s). Aborting experiment.", instance.instance, instanceID, instanceState)
				return false
			}

			statusContent, err := safeHTTPGet(statusURL)
			if err == nil && strings.Contains(string(statusContent), "EXPERIMENT_COMPLETED") {
				log.Printf("  ├─ Experiment completed for %s, downloading results...", instance.instance)

				// Download result file
				resultContent, err := safeHTTPGet(resultURL)
				if err != nil {
					log.Printf("Failed to download results for %s: %v", instance.instance, err)
					return false
				}
				log.Printf("  ├─ ✓ Downloaded results for %s, extracting...", instance.instance)

				// Create result directory
				resultDir := fmt.Sprintf("result/%s/%s", experimentManager.scriptFileName, instance.instance)
				if err := os.MkdirAll(resultDir, 0755); err != nil {
					log.Printf("Failed to create result directory for %s: %v", instance.instance, err)
					return false
				}

				// Extract tar.gz
				if err := extractTarGz(resultContent, resultDir); err != nil {
					log.Printf("Failed to extract results for %s: %v", instance.instance, err)
					return false
				}

				log.Printf("  └─ ✅ Successfully extracted results for %s in %s", instance.instance, resultDir)
				return true
			}
			elapsed := time.Since(experimentStartTime)
			log.Printf("  ├─ Waiting for %s... (elapsed: %v, max: %v)",
				instance.instance, elapsed.Round(time.Second), EXPERIMENT_MAX_TIMEOUT)
		}
	}
}

// =====================================================
// 파일 처리 함수들
// =====================================================

func loadInstancesFromFile(filename string) ([]*QueueValue, error) {
	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to open %s: %w", filename, err)
	}
	defer file.Close()

	var instances []*QueueValue
	scanner := bufio.NewScanner(file)
	lineNumber := 0

	for scanner.Scan() {
		lineNumber++
		line := strings.TrimSpace(scanner.Text())

		// Skip empty lines and comments
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		instances = append(instances, &QueueValue{
			instance: line,
		})
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading %s at line %d: %w", filename, lineNumber, err)
	}

	return instances, nil
}

func readScriptFile(filename string) (string, error) {
	content, err := os.ReadFile(filename)
	if err != nil {
		return "", fmt.Errorf("failed to read script file %s: %w", filename, err)
	}
	return string(content), nil
}

// =====================================================
// 메인 함수
// =====================================================

func main() {
	log.Println("🚀 AWS EC2 Experiment Runner")
	log.Printf("Region: %s, AMI: %s, Max Threads: %d", AWS_REGION, AMI_ID, MAX_THREADS)

	if len(os.Args) != 2 {
		fmt.Println("Usage: go run main.go <script.sh>")
		fmt.Println("Example: go run main.go my_experiment.sh")
		os.Exit(1)
	}

	scriptFile := os.Args[1]
	scriptFileName := getFileNameWithoutExt(scriptFile) // 전역 변수에 저장

	// Read the script file
	var err error
	scriptContent, err := readScriptFile(scriptFile)
	if err != nil {
		log.Fatalf("❌ %v", err)
	}
	log.Printf("📄 Loaded script: %s", scriptFile)

	// Load instances from instance.txt
	instances, err := loadInstancesFromFile("instance.txt")
	if err != nil {
		log.Fatalf("❌ %v", err)
	}

	// Filter out already processed instances
	var filteredInstances []*QueueValue
	for _, instance := range instances {
		resultDir := fmt.Sprintf("result/%s/%s", scriptFileName, instance.instance)
		if _, err := os.Stat(resultDir); err == nil {
			log.Printf("Skipping %s (already processed)", instance.instance)
		} else {
			filteredInstances = append(filteredInstances, instance)
		}
	}

	// Initialize managers
	quotaManager = NewQuotaManager()
	quotaManager.queue = filteredInstances
	log.Printf("📋 Loaded %d instances from instance.txt (%d already processed, %d to process)",
		len(instances), len(instances)-len(filteredInstances), len(filteredInstances))

	// Check if all instances are already processed
	if len(filteredInstances) == 0 {
		log.Println("✅ All instances are already processed!")
		// return
	}

	// AWS configuration
	experimentManager, err = NewExperimentManager()
	if err != nil {
		log.Fatalf("❌ Failed to initialize experiment manager: %v", err)
	}
	experimentManager.SetScript(scriptContent, scriptFileName)

	// Load spot instance quotas
	if err := experimentManager.loadSpotQuotas(); err != nil {
		log.Fatalf("❌ Failed to load spot quotas: %v", err)
	}

	// Subtract currently running spot instances from quotas
	if err := experimentManager.subtractRunningSpotInstances(); err != nil {
		log.Printf("⚠️ Warning: Failed to load running spot instances: %v", err)
	}

	if len(filteredInstances) == 0 {
		return
	}

	// Create security group
	sgResult, err := createSecurityGroup(experimentManager.ec2Client)
	if err != nil {
		log.Fatalf("❌ %v", err)
	}
	securityGroupID := sgResult.GroupId

	// Ensure cleanup
	defer deleteSecurityGroupSafely(experimentManager.ec2Client, securityGroupID)

	// Start worker goroutines
	log.Printf("🔄 Starting %d worker threads...", MAX_THREADS)
	var wg sync.WaitGroup
	for range MAX_THREADS {
		wg.Add(1)
		go func() {
			defer wg.Done()
			run(experimentManager.ec2Client, securityGroupID)
		}()
	}
	wg.Wait()

	log.Println("✅ All experiments completed!")
	log.Printf("📁 Results saved in result/%s/ directory", scriptFileName)
}
