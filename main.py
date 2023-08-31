import subprocess
import time
import datetime
import boto3

ec2_client = boto3.client('ec2', region_name='us-west-2')
ec2_resource = boto3.resource('ec2', region_name='us-west-2')

INSTNACE_COUNT = 450

def isDone():
    # S3 버킷 정보
    bucket_name = 'us-west-2-cpuid-x86'

    # S3 클라이언트 생성
    s3 = boto3.client('s3')

    while True:
        # 버킷 내 객체 개수 조회
        response = s3.list_objects_v2(Bucket=bucket_name)
        object_count = response['KeyCount']

        # 2023.07.16 일자에 수집한 데이터는 개수에서 제함.
        if (object_count - 464 == INSTNACE_COUNT):
            break

        time.sleep(10)


def createInfrastructure():
    # create infrastructure by group
    with open(f'terraform.log', 'w') as f:
        subprocess.run(['terraform', 'apply', '-auto-approve'],
                       cwd='./infrastructure', stdout=f, stderr=f, encoding='utf-8')


def destroyInfrastructure():
    # destroy infrastructure by groups
    with open(f'terraform.log', 'a') as f:
        p = subprocess.run(['terraform', 'destroy', '-auto-approve'],
                           cwd='./infrastructure', stdout=f, stderr=f)


if __name__ == '__main__':
    start_time = datetime.datetime.now()

    createInfrastructure()
    time.sleep(60)
    isDone()
    destroyInfrastructure()

    end_time = datetime.datetime.now()

    elapsed_time = end_time - start_time
    total_seconds = elapsed_time.total_seconds()
    print(f'total time : {total_seconds}')
