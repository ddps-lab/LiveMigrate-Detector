import pandas as pd
from pathlib import Path

import sys
import copy

root_path = str(Path(__file__).resolve().parent.parent.parent)

sys.path.append(str(Path(root_path).joinpath('data-processing')))
import GspreadUtils
import Transferable


def readCSV():
    # df = pd.read_csv(f'{root_path}/data-processing/verification/matrix_multiplication.csv')
    # df = pd.read_csv(f'{root_path}/data-processing/verification/redis.csv')
    # df = pd.read_csv(f'{root_path}/data-processing/verification/xgboost.csv')
    df = pd.read_csv(f'{root_path}/data-processing/verification/rubin.csv')
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
    global falseNagative
    global truePositive
    for index, row in migration_success.iterrows():
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
            falseNagative += 1
            # print(f'[fail] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination})')


def validateFailurePrediction(df, transferableGroups, migration_failed):
    global falsePositive
    global trueNagative
    for index, row in migration_failed.iterrows():
        src_index = list(df[df['instance groups'].str.contains(row.source)].index)
        dst_index = list(df[df['instance groups'].str.contains(row.destination)].index)

        # 마이그레이션 실험 대상과 isa set 데이터 수집 대상에서 몇몇 인스턴스가 없음
        if(len(src_index) <= 0 or len(dst_index) <= 0):
            continue

        src_index = src_index[0]
        dst_index = dst_index[0]

        # transferable 그룹인데 실패
        if((dst_index + 2) in transferableGroups[src_index]):
            # print(f'[fail] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination})')
            falsePositive += 1
        else:
            trueNagative += 1
            # print(f'[fail] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination})')

def validateForAllInstances(df, transferableGroups):
    migration_success, migration_failed = readCSV()

    validateSuccessPrediction(df, transferableGroups, migration_success)
    validateFailurePrediction(df, transferableGroups, migration_failed)


def validateForSpecificInstance(df, transferableGroups, instanceType):
    migration_success, migration_failed = readCSV()

    migration_success = migration_success[migration_success['source'] == instanceType]
    migration_failed = migration_failed[migration_failed['source'] == instanceType]

    validateSuccessPrediction(df, transferableGroups, migration_success)
    validateFailurePrediction(df, transferableGroups, migration_failed)


if __name__ == "__main__":
    truePositive = 0
    falsePositive = 0
    trueNagative = 0
    falseNagative = 0

    df = GspreadUtils.read_gspread('rubin(m5a.large)')
    transferableGroups = calTransferableMap(len(df), df)
    validateForSpecificInstance(df, transferableGroups, 'm5a.large')

    print(f'TP(마이그레이션 성공 예측 및 실제 성공) : {truePositive}')
    print(f'TN(마이그레이션 실패 예측 및 실제 실패) : {trueNagative}')
    print(f'FP(마이그레이션 성공 예측 및 실제 실패) : {falsePositive}')
    print(f'FN(마이그레이션 실패 예측 및 실제로 성공) : {falseNagative}')
    print(f'recall : {truePositive / (truePositive + falseNagative):.3f}')
