import time
import pandas as pd

xed_pkl = '/home/ubuntu/migration_test/ins_disas/log/unique_instructions.pkl'
workload_isa_file = '/home/ubuntu/migration_test/ins_disas/log/isa_set.csv'

def create_csv(workload_data_list, is_tsx_run=None, xtest_enable=None):
    temp_time = time.time()
    # Convert workload_data_list to DataFrame and save as csv
    workload_df = pd.DataFrame(workload_data_list)
    workload_df = workload_df.drop_duplicates(subset='ISA_SET')

    if is_tsx_run != None and xtest_enable != None:
        if not is_tsx_run:
            workload_df = workload_df[workload_df['ISA_SET'] != '   RTM']

        workload_df = workload_df[['ISA_SET', 'SHORT']]
        if xtest_enable:
            workload_df.loc[len(workload_df)] = ['XTEST', '']

    workload_df.to_csv(workload_isa_file, index=False)

    end_time = time.time()
    total_time = end_time - temp_time
    print("create csv: {:.3f} s".format(total_time))