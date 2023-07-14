import pandas as pd
from pathlib import Path
import sys

root_path = str(Path(__file__).resolve().parent.parent.parent)

sys.path.append(str(Path(root_path).joinpath('data-processing')))

import GspreadUtils

df1 = pd.read_csv(f'{root_path}/data-processing/tsx-adjust/CPU Feature Visualization - all features.csv')
df1 = df1[df1['CloudProvider'] == 'AWS']
df2 = GspreadUtils.read_gspread('us-west-2 x86 isa set')

df2.set_index('instancetype', inplace=True)

"""
kernel에서 TSX 관련 CPU features를 disable 하므로 cpuid를 통해 rtm을 조회하여도 0의 값만 확인됨.
따라서 rtm에 한해서 cpuid를 통해 조회하지 않고 kernel에서 설정한 cpu flag를 대입함.
"""
for idx1, row1 in df1.iterrows():
    instance_type = row1['InstanceType']

    if instance_type in df2.index:
        df2.loc[instance_type, 'rtm'] = row1['rtm']


df2_only_instance_types = df2.index.difference(df1['InstanceType'])
print(df2_only_instance_types)

df2.reset_index(inplace=True)

# GspreadUtils.write_gspread('us-west-2 x86 isa set', df2)