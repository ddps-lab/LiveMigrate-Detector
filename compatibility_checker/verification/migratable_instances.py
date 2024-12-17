import pandas as pd
from pathlib import Path

import sys
import copy
import boto3

import pickle
import json

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

def criu_compatibility_check(features_lookup, instanceType):
    # CRIU_scope = ['fpu', 'tsc', 'cx8', 'sep', 'cmov', 'clflush', 'mmx', 'fxsr', 'sse', 'sse2', 'syscall', 'mmxext', 'rdtscp', '3dnowext', '3dnow', 'rep_good', 'nopl', 'pni', 'pclmulqdq', 'monitor', 'ssse3', 'cx16', 'sse4_1', 'sse4_2', 'movbe', 'popcnt', 'aes', 'xsave', 'osxsave', 'avx', 'f16c', 'rdrand', 'abm', 'sse4a', 'misalignsse', '3dnowprefetch', 'xop', 'fma4', 'tbm', 'fsgsbase', 'bmi1', 'hle', 'avx2', 'bmi2', 'erms', 'rtm', 'mpx', 'avx512f', 'avx512dq', 'rdseed', 'adx', 'clflushopt', 'avx512pf', 'avx512er', 'avx512cd', 'sha_ni', 'avx512bw', 'avx512vl', 'xsaveopt', 'xsavec', 'xgetbv1', 'avx512vbmi', 'avx512_vbmi2', 'gfni', 'vaes', 'vpclmulqdq', 'avx512_vnni', 'avx512_bitalg', 'tme', 'avx512_vpopcntdq', 'rdpid', 'clzero', 'avx512_4vnniw', 'avx512_4fmaps']
    # cpuinfo에 표시되지 않는 3dnowext, 3dnow, osxsave, xop, fma4, tbm, avx512pf, avx512er, avx512_4vnniw, avx512_4fmaps 제외.
    CRIU_scope = ['fpu', 'tsc', 'cx8', 'sep', 'cmov', 'clflush', 'mmx', 'fxsr', 'sse', 'sse2', 'syscall', 'mmxext', 'rdtscp', 'rep_good', 'nopl', 'pni', 'pclmulqdq', 'monitor', 'ssse3', 'cx16', 'sse4_1', 'sse4_2', 'movbe', 'popcnt', 'aes', 'xsave', 'avx', 'f16c', 'rdrand', 'abm', 'sse4a', 'misalignsse', '3dnowprefetch', 'fsgsbase', 'bmi1', 'hle', 'avx2', 'bmi2', 'erms', 'rtm', 'mpx', 'avx512f', 'avx512dq', 'rdseed', 'adx', 'clflushopt', 'avx512cd', 'sha_ni', 'avx512bw', 'avx512vl', 'xsaveopt', 'xsavec', 'xgetbv1', 'avx512vbmi', 'avx512_vbmi2', 'gfni', 'vaes', 'vpclmulqdq', 'avx512_vnni', 'avx512_bitalg', 'tme', 'avx512_vpopcntdq', 'rdpid', 'clzero']
    
    transferable_instances = []
    reference_row = features_lookup[features_lookup['InstanceType'] == instanceType].iloc[0]

    # 지정된 컬럼들 중 1인 컬럼만 추출
    subset_columns = [col for col in CRIU_scope if reference_row[col] == 1]
    # 다른 모든 행과 비교
    for _, row in features_lookup.iterrows():
        if row['InstanceType'] == instanceType:  # 동일 행 제외
            continue
        if all(row[col] == 1 for col in subset_columns):
            transferable_instances.append(row.InstanceType)

    return transferable_instances


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


def validate(features_lookup, prefix, instanceType):
    response = s3_client.get_object(Bucket=bucket_name, Key=prefix + instanceType + '.csv')
    file_content = response['Body'].read().decode('utf-8')

    features_from_workload = pd.read_csv(StringIO(file_content))
    group = GroupbyISA.groupby_isa(features_lookup, features_from_workload)
    transferableGroups = calTransferableMap(len(group), group)
    compatible = group['instance groups']

    src_index = None
    for i in range(len(compatible)):
        if instanceType in compatible.iloc[i]:
            src_index = i + 2
    
    if(src_index == None):
        print('error')
        exit()

    transferable_instances = []
    for i in range(len(transferableGroups)):
        if transferableGroups[i][0] != src_index:
            continue

        for transferable_index in range(len(transferableGroups[i])):
            group_index = transferableGroups[i][transferable_index]
            transferable = compatible.iloc[group_index - 2].split(', ')
            transferable_instances.append(transferable)
    
    # 리스트 컴프리헨션을 사용하여 중첩된 리스트를 단일 리스트로 변환
    transferable_instances = [item for sublist in transferable_instances for item in sublist]

    return transferable_instances


def intersection():
    cpuid_lookup = GspreadUtils.read_gspread('us-west-2 x86 isa set(23.08.31)')
    flags_lookup = GspreadUtils.read_CPU_Feature_Visualization()

    set_A = set(cpuid_lookup['instancetype'])
    set_B = set(flags_lookup['InstanceType'])

    # 두 set의 교집합 찾기
    intersection = set_A.intersection(set_B)

    flags_lookup = flags_lookup[flags_lookup['InstanceType'].isin(intersection)]
    cpuid_lookup = cpuid_lookup[cpuid_lookup['instancetype'].isin(intersection)]

    return intersection, flags_lookup, cpuid_lookup

if __name__ == "__main__":
    workloads = ['c_matrix_multiplication', 'redis', 'cpp_xgboost', 'adox_adcx', 'pku', 'rdseed', 'sha', 'pymatmul', 'pyxgboost', 'pyrsa', 'pypku','pyrdseed', 'pysha']
    instanceTypes = ['m5a.large', 'm5a.2xlarge', 'm5a.8xlarge', 'c5a.large', 'c6a.large', 'm4.large', 'h1.2xlarge', 'x1e.xlarge', 'r4.large', 'i3.large', 'c5a.24xlarge', 'c6a.24xlarge', 'c4.8xlarge', 'h1.8xlarge', 'h1.16xlarge', 'x1e.8xlarge', 'm4.16xlarge', 'r4.8xlarge', 'r4.16xlarge', 'c6i.large', 'c5.large', 'm5n.large', 'm5.large', 'c6i.16xlarge', 'c5d.9xlarge', 'm5zn.6xlarge', 'c5.9xlarge']
    # instanceTypes = ["m5a.xlarge", "m5a.2xlarge", "m5a.8xlarge", "c5a.xlarge", "c6a.xlarge", "m4.xlarge", "h1.2xlarge", "x1e.xlarge", "r4.xlarge", "i3.xlarge", "c5a.24xlarge", "c6a.24xlarge", "c4.8xlarge", "h1.8xlarge", "h1.16xlarge", "x1e.8xlarge", "m4.16xlarge", "r4.8xlarge", "r4.16xlarge", "c6i.xlarge", "c5.xlarge", "m5n.xlarge", "c5d.2xlarge", "c6i.16xlarge", "c5d.9xlarge", "m5zn.6xlarge", "c5.9xlarge"]

    print('Select workloads to experiment with')
    print(f'1. {workloads[0]}\n2. {workloads[1]}\n3. {workloads[2]}\n4. {workloads[3]}\n5. {workloads[4]}\n6. {workloads[5]}\n7. {workloads[6]}')
    print(f'8. pymatmul\n9. pyxgboost\n10. pyrsa\n11. pypku\n12. pyrdseed\n13. pysha')
    index = int(input()) - 1
    WORKLOAD = workloads[index]

    intersection, flags_lookup, cpuid_lookup = intersection()

    intersection = sorted(intersection)

    transferableMap = {'CRIU' : {}, 'FuncTracking' : {}, 'FullScanning' : {}, 'BytecodeTracking' : {}}
    for instance in instanceTypes:
        transferable_instances = criu_compatibility_check(flags_lookup, instance)
        transferableMap['CRIU'][instance] = transferable_instances
        print(f'{instance}, criu : {len(transferable_instances)}')

        prefix = f'func_tracking/{WORKLOAD}/'
        transferable_instances = validate(cpuid_lookup, prefix, instance)
        transferableMap['FuncTracking'][instance] = transferable_instances
        print(f'{instance}, FuncTracking : {len(transferable_instances)}')
        
        prefix = f'entire-scanning/{WORKLOAD}/'
        transferable_instances = validate(cpuid_lookup, prefix, instance)
        transferableMap['FullScanning'][instance] = transferable_instances
        print(f'{instance}, FullScanning : {len(transferable_instances)}')

        prefix = f'bytecode_tracking/{WORKLOAD}/'
        transferable_instances = validate(cpuid_lookup, prefix, instance)
        transferableMap['BytecodeTracking'][instance] = transferable_instances
        print(f'{instance}, BytecodeTracking : {len(transferable_instances)}')

    # 딕셔너리를 .pkl 파일로 저장하기
    with open(f'{WORKLOAD}.pkl', 'wb') as pkl_file:
        pickle.dump(transferableMap, pkl_file)

    # # 딕셔너리를 JSON 형식의 텍스트 파일로 저장하기
    # with open('transferableMap.txt', 'w') as txt_file:
    #     json.dump(transferableMap, txt_file, indent=4)