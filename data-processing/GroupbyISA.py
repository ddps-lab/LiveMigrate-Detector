import pandas as pd

import copy

import GspreadUtils
import ISA

def groupby_isa(df, isa = None):
    ISAs = ISA.get_ISAs()

    # Extract instance types with the same CPU ISA
    columns = copy.deepcopy(ISAs)
    columns.insert(0, 'instance groups')

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
    
    return df_new

df = GspreadUtils.read_gspread('us-west-2 x86 isa set(23.08.31)')
group = groupby_isa(df)
GspreadUtils.write_gspread('mat_mul_c(h1.16xlarge)', group)