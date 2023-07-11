import pandas as pd
from pathlib import Path

import sys

import transferable_h

root_path = str(Path(__file__).resolve().parent.parent.parent)

sys.path.append(str(Path(root_path).joinpath('data-processing')))
import GspreadUtils

# CSV 파일 읽기
df = pd.read_csv(f'{root_path}/data-processing/verification/matrix_multiplication.csv')

# 'migration_success' 열이 'true'인 행 추출
migration_success = df[df['migration_success'] == True]
migration_failed = df[df['migration_success'] == False]

selected_columns = ['source', 'destination']
migration_success = migration_success[selected_columns]
migration_failed = migration_failed[selected_columns]

df = GspreadUtils.read_gspread('groupby isa')

cnt = 0
for index, row in migration_success.iterrows():
    src_index = list(df[df['instance groups'].str.contains(row.source)].index)
    dst_index = list(df[df['instance groups'].str.contains(row.destination)].index)

    # print(f'idx : {src_index} type : {row.source}')

    # 마이그레이션 실험 대상과 isa set 데이터 수집 대상에서 몇몇 인스턴스가 없음
    if(len(src_index) <= 0 or len(dst_index) <= 0):
        continue

    src_index = src_index[0]
    dst_index = dst_index[0]

    # 같은 그룹에 있지 않은 경우
    if(src_index != dst_index):
        # print(f'src : {source_index}, dst : {dst_index}')
        
        # transferable 그룹이 아닌 경우
        if((dst_index + 2) not in transferable_h.transferableGroups[src_index]):
            print(f'[success] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination}) {transferable_h.transferableGroups[src_index]}')
            cnt += 1
print(cnt)

cnt = 0
for index, row in migration_failed.iterrows():
    src_index = list(df[df['instance groups'].str.contains(row.source)].index)
    dst_index = list(df[df['instance groups'].str.contains(row.destination)].index)

    # print(f'idx : {src_index} type : {row.source}')

    # 마이그레이션 실험 대상과 isa set 데이터 수집 대상에서 몇몇 인스턴스가 없음
    if(len(src_index) <= 0 or len(dst_index) <= 0):
        continue

    src_index = src_index[0]
    dst_index = dst_index[0]

    # transferable 그룹인데 실패
    if((dst_index + 2) in transferable_h.transferableGroups[src_index]):
        print(f'[fail] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination}) {transferable_h.transferableGroups[src_index]}')
        cnt += 1
print(cnt)