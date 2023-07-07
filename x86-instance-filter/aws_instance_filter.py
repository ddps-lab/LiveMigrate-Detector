import os
import pandas as pd

import boto3

# EC2 클라이언트 생성
ec2_client = boto3.client('ec2', region_name = 'us-west-2')

createable_x86_64_instances = []
createable_arm64_instances = []
unsupported_instances = []
next_token = None

while True:
    # 인스턴스 타입 정보 가져오기
    if next_token:
        response = ec2_client.describe_instance_types(NextToken=next_token)
    else:
        response = ec2_client.describe_instance_types()

    # 현재 페이지의 인스턴스 유형 이름 추가
    for instance_type in response['InstanceTypes']:
        if instance_type['CurrentGeneration']:
            architectures = instance_type['ProcessorInfo']['SupportedArchitectures']
            if 'x86_64' in architectures:
                createable_x86_64_instances.append(instance_type['InstanceType'])

    # 다음 페이지 토큰 설정
    next_token = response.get('NextToken', None)

    # 다음 페이지 토큰이 없으면 종료
    if not next_token:
        break

df = pd.DataFrame(createable_x86_64_instances, columns=['InstanceType'])

output_csv_file = f"{os.path.dirname(__file__)}/AWS x86 instances(us-west-2, 23.07.07).csv"
df.to_csv(output_csv_file, index=False)