import pandas as pd
from pathlib import Path

import sys

import transferable_h

root_path = str(Path(__file__).resolve().parent.parent.parent)

sys.path.append(str(Path(root_path).joinpath('data-processing')))
import GspreadUtils

# CSV 파일 읽기
df = pd.read_csv(f'{root_path}/data-processing/verification/matrix_multiplication.csv')

transferableGroups = transferable_h.all()

# 'migration_success' 열이 'true'인 행 추출
migration_success = df[df['migration_success'] == True]
migration_failed = df[df['migration_success'] == False]

selected_columns = ['source', 'destination']
migration_success = migration_success[selected_columns]
migration_failed = migration_failed[selected_columns]

df = GspreadUtils.read_gspread('groupby isa')

cnt = 0
print('호환맵 상 실패로 판단하나 실제 실험이 성공한 경우')
for index, row in migration_success.iterrows():
    src_index = list(df[df['instance groups'].str.contains(row.source)].index)
    dst_index = list(df[df['instance groups'].str.contains(row.destination)].index)

    # 마이그레이션 실험 대상과 isa set 데이터 수집 대상에서 몇몇 인스턴스가 없음
    if(len(src_index) <= 0 or len(dst_index) <= 0):
        continue

    src_index = src_index[0]
    dst_index = dst_index[0]

    # 같은 그룹에 있지 않은 경우
    if(src_index != dst_index):
        # transferable 그룹이 아닌 경우
        if((dst_index + 2) not in transferableGroups[src_index]):
            print(f'[success] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination}) {transferableGroups[src_index]}')
            cnt += 1
print(f'count : {cnt}')

df2 = pd.read_csv(f'{root_path}/data-processing/verification/AWS migration compatibility - matrix multiplication.csv')

cnt = 0
print('호환맵 상 성공함으로 판단하나 실제 실험이 실패한 경우')
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
        filtered_df = df2[df2['feature groups'].str.contains(row.source)]
        indices1 = filtered_df.index.tolist()

        filtered_df = df2[df2['feature groups'].str.contains(row.destination)]
        indices2 = filtered_df.index.tolist()

        print(f'src : {indices1[0] + 2}, dst : {indices2[0] + 2}')

        print(f'[fail] src : {src_index + 2}({row.source}), dst : {dst_index + 2}({row.destination}) {transferableGroups[src_index]}')
        cnt += 1

        print()

print(f'count : {cnt}')