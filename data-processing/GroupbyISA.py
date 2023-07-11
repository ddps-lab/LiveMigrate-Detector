import pandas as pd

import copy

import GspreadUtils
import ISA_h

df = GspreadUtils.read_gspread('us-west-2 x86 isa set')

# Extract instance types with the same CPU ISA
columns = copy.deepcopy(ISA_h.ISAs)
columns.insert(0, 'instance groups')

groupList = []
flagList = []
grouped = df.groupby(ISA_h.ISAs)
i = 0

df_new = pd.DataFrame(columns=columns)

for features, group in grouped:
    i += 1
    instanceTypes = ', '.join(group['instancetype'].tolist())

    eachFlag = group[ISA_h.ISAs]
    row = eachFlag.iloc[0]
    row = row.to_frame().T
    row.insert(0, 'instance groups', instanceTypes)

    df_new = pd.concat([df_new, row], ignore_index=True)

GspreadUtils.write_gspread('groupby isa', df_new)