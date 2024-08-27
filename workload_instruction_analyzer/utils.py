import pandas as pd

from pathlib import Path

rootdir = str(Path(__file__).resolve().parent)

workload_isa_file = f'{rootdir}/log/isa_set.csv'

def create_csv(workload_data_list, is_tsx_run=None, xtest_enable=None):
    # Convert workload_data_list to DataFrame and save as csv
    workload_df = pd.DataFrame(workload_data_list)
    workload_df = workload_df.drop_duplicates(subset='ISA_SET')

    if is_tsx_run != None and xtest_enable != None:
        if not is_tsx_run:
            workload_df = workload_df[~workload_df['ISA_SET'].str.contains('RTM')]

        workload_df = workload_df[['ISA_SET', 'SHORT']]
        if xtest_enable:
            workload_df.loc[len(workload_df)] = ['XTEST', '']

    workload_df.to_csv(workload_isa_file, index=False)