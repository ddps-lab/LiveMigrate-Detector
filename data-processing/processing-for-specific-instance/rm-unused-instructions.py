import pandas as pd
import copy

from pathlib import Path
import sys

root_path = str(Path(__file__).resolve().parent.parent.parent)

sys.path.append(str(Path(root_path).joinpath('data-processing')))
import GspreadUtils
import ISA_h

ISAs = ISA_h.ISAs_for_matmul

df = GspreadUtils.read_gspread('us-west-2 x86 isa set')

INSTANCE_TYPE = 'c5a.large'

row = df[df['instancetype'] == INSTANCE_TYPE]

columns_with_value_1 = row.loc[:, row.eq(1).all()].columns


columns_with_value_1 = set(columns_with_value_1)
ISAs = set(ISAs)

usable_instruction_sets = list(columns_with_value_1 & ISAs)

print(usable_instruction_sets)

############################################################

df = GspreadUtils.read_gspread('us-west-2 x86 isa set')

# Extract instance types with the same CPU ISA
columns = copy.deepcopy(usable_instruction_sets)
columns.insert(0, 'instance groups')

groupList = []
flagList = []
grouped = df.groupby(usable_instruction_sets)
i = 0

df_new = pd.DataFrame(columns=columns)

for features, group in grouped:
    i += 1
    instanceTypes = ', '.join(group['instancetype'].tolist())

    eachFlag = group[usable_instruction_sets]
    row = eachFlag.iloc[0]
    row = row.to_frame().T
    row.insert(0, 'instance groups', instanceTypes)

    df_new = pd.concat([df_new, row], ignore_index=True)

GspreadUtils.write_gspread(f'mat_mul_for_{INSTANCE_TYPE}', df_new)