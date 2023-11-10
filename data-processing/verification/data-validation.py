import pandas as pd
from pathlib import Path

import sys
import copy
import boto3

from pprint import pprint

from io import StringIO

root_path = str(Path(__file__).resolve().parent.parent.parent)

sys.path.append(str(Path(root_path).joinpath('data-processing')))
import GspreadUtils
import Transferable
import GroupbyISA

ec2_client = boto3.client('ec2', region_name='us-west-2')
ec2_resource = boto3.resource('ec2', region_name='us-west-2')
s3_client = boto3.client('s3')

bucket_name = 'migration-compatibility'
prefix = 'func_tracking/redis/'

def readCSV():
    df = pd.read_csv(f'{root_path}/data-processing/verification/redis.csv')
    migration_success = df[df['migration_success'] == True]
    migration_failed = df[df['migration_success'] == False]

    selected_columns = ['source', 'destination']
    migration_success = migration_success[selected_columns]
    migration_failed = migration_failed[selected_columns]

    return migration_success, migration_failed


def calTransferableMap(GROUP_NUMBER, df):
    df = copy.deepcopy(df)
    df = df.drop('instance groups', axis=1)

    matrix = Transferable.transferable_check(GROUP_NUMBER, df)
    transferableGroups = []

    for i in range(len(matrix)):
        tempGroup = []
        for j in range(len(matrix[i])):
            if (matrix[i][j]):
                tempGroup.append(j + 2)
        transferableGroups.append(tempGroup)

    return transferableGroups
    

def validateSuccessPrediction(df, transferableGroups, migration_success):
    global falseNegative
    global truePositive

    check = False
    for _, row in migration_success.iterrows():
        src_index = list(df[df['instance groups'].str.contains(row.source)].index)
        dst_index = list(df[df['instance groups'].str.contains(row.destination)].index)

        # 마이그레이션 실험 대상과 isa set 데이터 수집 대상에서 몇몇 인스턴스가 없음
        if(len(src_index) <= 0 or len(dst_index) <= 0):
            continue

        src_index = src_index[0]
        dst_index = dst_index[0]

        if((dst_index + 2) in transferableGroups[src_index]):
            truePositive += 1
        else:
            falseNegative += 1
            check = True
            print(f'[fail] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination})')
    
    if check:
        print(df)
    print


def validateFailurePrediction(df, transferableGroups, migration_failed):
    global falsePositive
    global trueNegative
    for _, row in migration_failed.iterrows():
        src_index = list(df[df['instance groups'].str.contains(row.source)].index)
        dst_index = list(df[df['instance groups'].str.contains(row.destination)].index)

        # 마이그레이션 실험 대상과 isa set 데이터 수집 대상에서 몇몇 인스턴스가 없음
        if(len(src_index) <= 0 or len(dst_index) <= 0):
            continue

        src_index = src_index[0]
        dst_index = dst_index[0]

        # transferable 그룹인데 실패
        if((dst_index + 2) in transferableGroups[src_index]):
            falsePositive += 1
        else:
            trueNegative += 1


def validateForAllInstances():
    result = dict()
    global truePositive, falsePositive, trueNegative, falseNegative

    isa_lookup = GspreadUtils.read_gspread('us-west-2 x86 isa set(23.08.31)')

    # func tracking 결과 조회
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    objects = response.get('Contents', [])

    # 객체 이름만 리스트로 저장
    file_names = [obj['Key'].split('/')[-1] for obj in objects]
    file_names = set(file_names)
    file_names.discard('')
    for file_name in file_names:
        validate = dict()

        instanceType = file_name.split('.csv')[0]
        response = s3_client.get_object(Bucket=bucket_name, Key=prefix + file_name)
        file_content = response['Body'].read().decode('utf-8')

        isa_from_workload = pd.read_csv(StringIO(file_content))

        group = GroupbyISA.groupby_isa(isa_lookup, isa_from_workload)
        
        transferableGroups = calTransferableMap(len(group), group)

        validateForSpecificInstance(group, transferableGroups, instanceType)

        validate['TN(마이그레이션 실패 예측 및 실제 실패)'] = trueNegative
        validate['FN(마이그레이션 실패 예측 및 실제 성공)'] = falseNegative
        validate['FP(마이그레이션 성공 예측 및 실제 실패)'] = falsePositive
        validate['TP(마이그레이션 성공 예측 및 실제 성공)'] = truePositive
        validate['recall'] = truePositive / (truePositive + falseNegative)

        result[instanceType] = validate
        truePositive = falsePositive = trueNegative = falseNegative = 0

    pprint(result)


def validateForSpecificInstance(df, transferableGroups, instanceType):
    migration_success, migration_failed = readCSV()

    migration_success = migration_success[migration_success['source'] == instanceType]
    migration_failed = migration_failed[migration_failed['source'] == instanceType]

    validateSuccessPrediction(df, transferableGroups, migration_success)
    validateFailurePrediction(df, transferableGroups, migration_failed)


if __name__ == "__main__":
    truePositive = 0
    falsePositive = 0
    trueNegative = 0
    falseNegative = 0

    validateForAllInstances()

    # df = GspreadUtils.read_gspread('adx(r4.large)')
    # transferableGroups = calTransferableMap(len(df), df)
    # validateForSpecificInstance(df, transferableGroups, 'r4.large')

    # print(f'TP(마이그레이션 성공 예측 및 실제 성공) : {truePositive}')
    # print(f'TN(마이그레이션 실패 예측 및 실제 실패) : {trueNegative}')
    # print(f'FP(마이그레이션 성공 예측 및 실제 실패) : {falsePositive}')
    # print(f'FN(마이그레이션 실패 예측 및 실제로 성공) : {falseNegative}')
    # print(f'recall : {truePositive / (truePositive + falseNegative):.3f}')
