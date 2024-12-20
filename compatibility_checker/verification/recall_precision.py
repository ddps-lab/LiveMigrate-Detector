import pandas as pd
from pathlib import Path

import sys
import copy
import boto3

from pprint import pprint

from io import StringIO

root_path = str(Path(__file__).resolve().parent.parent.parent)

sys.path.append(str(Path(root_path).joinpath('compatibility_checker')))
import GspreadUtils
import Transferable
import GroupbyISA

ec2_client = boto3.client('ec2', region_name='us-west-2')
ec2_resource = boto3.resource('ec2', region_name='us-west-2')
s3_client = boto3.client('s3')

bucket_name = 'migration-compatibility'

def readCSV():
    df = pd.read_csv(f'{root_path}/compatibility_checker/verification/pyxgboost.csv')
    migration_success = df[df['migration_success'] == True]
    migration_failed = df[df['migration_success'] == False]

    selected_columns = ['source', 'destination']
    migration_success = migration_success[selected_columns]
    migration_failed = migration_failed[selected_columns]

    return migration_success, migration_failed


def criu_cpu_info_check():
    recall = 0
    precision = 0

    # instances =["m5a.large", "m5a.2xlarge", "m5a.8xlarge", "c5a.large", "c6a.large", "m4.large", "h1.2xlarge", "x1e.xlarge", "r4.large", "i3.large", "c5a.24xlarge", "c6a.24xlarge", "c4.8xlarge", "h1.8xlarge", "h1.16xlarge", "x1e.8xlarge", "m4.16xlarge", "r4.8xlarge", "r4.16xlarge", "c6i.large", "c5.large", "m5n.large", "m5.large", "c6i.16xlarge", "c5d.9xlarge", "m5zn.6xlarge", "c5.9xlarge"]
    instances = ["m5a.xlarge", "m5a.2xlarge", "m5a.8xlarge", "c5a.xlarge", "c6a.xlarge", "m4.xlarge", "h1.2xlarge", "x1e.xlarge", "r4.xlarge", "i3.xlarge", "c5a.24xlarge", "c6a.24xlarge", "c4.8xlarge", "h1.8xlarge", "h1.16xlarge", "x1e.8xlarge", "m4.16xlarge", "r4.8xlarge", "r4.16xlarge", "c6i.xlarge", "c5.xlarge", "m5n.xlarge", "c5d.2xlarge", "c6i.16xlarge", "c5d.9xlarge", "m5zn.6xlarge", "c5.9xlarge"]
    df = pd.read_csv(f'{root_path}/compatibility_checker/verification/criu_cpuinfo_check.csv')
    compatible = df[df['compatibility'] == True]
    incompatible = df[df['compatibility'] == False]

    selected_columns = ['source', 'destination']
    compatible = compatible[selected_columns]
    incompatible = incompatible[selected_columns]

    migration_success, migration_failed = readCSV()

    # TN(마이그레이션 실패 예측 및 실제 실패)
    # FN(마이그레이션 실패 예측 및 실제 성공)
    true_negative = pd.merge(incompatible, migration_failed, how='outer', on=['source', 'destination'], indicator=True)
    false_negative = true_negative[true_negative['_merge'] == 'left_only']
    true_negative = true_negative[true_negative['_merge'] == 'both']

    # TP(마이그레이션 성공 예측 및 실제 성공)
    # FP(마이그레이션 성공 예측 및 실제 실패)
    true_positive = pd.merge(compatible, migration_success, how='outer', on=['source', 'destination'], indicator=True)
    false_positive = true_positive[true_positive['_merge'] == 'left_only']
    true_positive = true_positive[true_positive['_merge'] == 'both']

    # '_merge' 열 제거
    if len(true_negative) < 1:
        true_negative = true_negative.drop(columns=['_merge'])
    if len(false_negative) < 1:
        false_negative = false_negative.drop(columns=['_merge'])
    if len(true_positive) < 1:
        true_positive = true_positive.drop(columns=['_merge'])
    if len(false_positive) < 1:
        false_positive = false_positive.drop(columns=['_merge'])
    
    result = dict()
    except_precision = 0
    for instanceType in instances:
        validate = dict()

        TN = (true_negative['source'] == instanceType).sum()
        FN = (false_negative['source'] == instanceType).sum()
        FP = (false_positive['source'] == instanceType).sum()
        TP = (true_positive['source'] == instanceType).sum()

        validate['TN(마이그레이션 실패 예측 및 실제 실패)'] = TN
        validate['FN(마이그레이션 실패 예측 및 실제 성공)'] = FN
        validate['FP(마이그레이션 성공 예측 및 실제 실패)'] = FP
        validate['TP(마이그레이션 성공 예측 및 실제 성공)'] = TP

        if TP + FN == 0:
            validate['recall'] = 0
        else:
            validate['recall'] = TP / (TP + FN)
            recall += TP / (TP + FN)

        if TP + FP == 0:
            except_precision += 1
        else:
            validate['precision'] = TP / (TP + FP)
            precision += TP / (TP + FP)

        result[instanceType] = validate

        TN = FN = FP = TP = 0

    print(f'total recall : {recall / 27:.3f}')
    print(f'total precision : {precision / (27 - except_precision):.3f}')


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
            # print(f'[FN] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination})')
    

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
            # print(f'[FP] src : {src_index}({row.source}), dst : {dst_index + 2}({row.destination})')
        else:
            trueNegative += 1
            # print(f'[TN] src : {src_index}({row.source}), dst : {dst_index + 2}({row.destination})')


def validateForAllInstances(prefix):
    result = dict()
    recall = 0
    precision = 0

    global truePositive, falsePositive, trueNegative, falseNegative

    isa_lookup = GspreadUtils.read_gspread('us-west-2 x86 isa set(23.08.31)')

    # func tracking 결과 조회
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    objects = response.get('Contents', [])

    except_precision = 0

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
        # if instanceType == 'm5a.large':
            # GspreadUtils.write_gspread('result', group)

        
        transferableGroups = calTransferableMap(len(group), group)

        validateForSpecificInstance(group, transferableGroups, instanceType)

        validate['TN(마이그레이션 실패 예측 및 실제 실패)'] = trueNegative
        validate['FN(마이그레이션 실패 예측 및 실제 성공)'] = falseNegative
        validate['FP(마이그레이션 성공 예측 및 실제 실패)'] = falsePositive
        validate['TP(마이그레이션 성공 예측 및 실제 성공)'] = truePositive

        if truePositive + falseNegative == 0:
            validate['recall'] = 0
        else:
            validate['recall'] = truePositive / (truePositive + falseNegative)
            recall += truePositive / (truePositive + falseNegative)
        
        if truePositive + falsePositive == 0:
            except_precision += 1
        else:
            validate['precision'] = truePositive / (truePositive + falsePositive)
            precision += truePositive / (truePositive + falsePositive)

        result[instanceType] = validate
        truePositive = falsePositive = trueNegative = falseNegative = 0

    pprint(result)

    print(f'total recall : {recall / 27:.3f}')
    print(f'total precision : {precision / (27 - except_precision):.3f}')


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

    # criu_cpu_info_check()

    print('Select evaluation option')
    print('1. entire scanning\n2. function tracking\n3. bytecode tracking')
    option = int(input()) - 1

    if option == 0:
        prefix = 'entire-scanning/pyxgboost/'
    elif option == 1:
        prefix = 'func_tracking/pyxgboost/'
    elif option == 2:
        prefix = 'bytecode_tracking/pyxgboost/'
    else:
        print('invalid option')
        exit()

    validateForAllInstances(prefix)