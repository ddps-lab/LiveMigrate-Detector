import pandas as pd

import copy

import GspreadUtils
import ISA

df = GspreadUtils.read_gspread('us-west-2 x86 isa set(23.08.31)')

ISAs = ISA.get_ISAs()
print(ISAs)

# Extract instance types with the same CPU ISA
columns = copy.deepcopy(ISAs)
columns.insert(0, 'instance groups')

groupList = []
flagList = []
grouped = df.groupby(ISAs)
i = 0

df_new = pd.DataFrame(columns=columns)

for features, group in grouped:
    i += 1
    instanceTypes = ', '.join(group['instancetype'].tolist())

    eachFlag = group[ISAs]
    row = eachFlag.iloc[0]
    row = row.to_frame().T
    row.insert(0, 'instance groups', instanceTypes)

    df_new = pd.concat([df_new, row], ignore_index=True)

GspreadUtils.write_gspread('redis(r4.large,func,tsx)', df_new)