package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/ec2"
	"github.com/aws/aws-sdk-go-v2/service/ec2/types"
)

const amiID = "ami-0c55b159cbfafe1f0"

// createSecurityGroup 함수는 1234 포트를 개방하는 보안 그룹을 생성합니다.
func createSecurityGroup(client *ec2.Client) (*ec2.CreateSecurityGroupOutput, error) {
	groupName := fmt.Sprintf("spot-sg-%d", time.Now().Unix())
	sgInput := &ec2.CreateSecurityGroupInput{
		GroupName:   aws.String(groupName),
		Description: aws.String("Allow port 1234 for spot instance web server"),
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
				FromPort:   aws.Int32(1234),
				ToPort:     aws.Int32(1234),
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
git clone https://github.com/ddps-lab/LiveMigrate-Detector.git
cd LiveMigrate-Detector/cpu_feature_collector
gcc 
nohup python3 -m http.server 1234 &
`
	return base64.StdEncoding.EncodeToString([]byte(script))
}

// requestSpotInstance 함수는 스팟 인스턴스를 요청합니다.
func requestSpotInstance(client *ec2.Client, instanceType types.InstanceType, securityGroupID, userData string) (*ec2.RequestSpotInstancesOutput, error) {
	return client.RequestSpotInstances(context.TODO(), &ec2.RequestSpotInstancesInput{
		InstanceCount: aws.Int32(1),
		Type:          types.SpotInstanceTypeOneTime, // 일회성 요청
		LaunchSpecification: &types.RequestSpotLaunchSpecification{
			ImageId:      aws.String(amiID),
			InstanceType: instanceType, // 저렴한 인스턴스 타입
			SecurityGroupIds: []string{
				securityGroupID,
			},
			UserData: aws.String(userData),
		},
		ValidUntil: aws.Time(time.Now().Add(3 * time.Minute)),
	})
}
