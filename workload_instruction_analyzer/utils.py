import pandas as pd

from pathlib import Path

print("=== DEBUG: utils.py imported ===")

rootdir = str(Path(__file__).resolve().parent)
print(f"=== DEBUG: Root directory: {rootdir} ===")

workload_isa_file = f'{rootdir}/log/isa_set.csv'
print(f"=== DEBUG: ISA set file path: {workload_isa_file} ===")


def create_csv(workload_data_list, is_tsx_run=None, xtest_enable=None):
    print(
        f"=== DEBUG: Creating CSV with {len(workload_data_list)} instructions ===")
    print(
        f"=== DEBUG: TSX run: {is_tsx_run}, XTEST enable: {xtest_enable} ===")

    try:
        # Convert workload_data_list to DataFrame and save as csv
        workload_df = pd.DataFrame(workload_data_list)
        print(f"=== DEBUG: Created DataFrame with {len(workload_df)} rows ===")

        # Show first few entries for debugging
        if len(workload_df) > 0:
            print(f"=== DEBUG: Sample entries: ===")
            for i, row in workload_df.head(3).iterrows():
                print(
                    f"=== DEBUG: Row {i}: ISA_SET='{row['ISA_SET']}', SHORT='{row['SHORT'][:50]}...' ===")

        original_size = len(workload_df)
        workload_df = workload_df.drop_duplicates(subset='ISA_SET')
        deduplicated_size = len(workload_df)
        print(
            f"=== DEBUG: Removed {original_size - deduplicated_size} duplicates, {deduplicated_size} unique instructions remain ===")

        if is_tsx_run != None and xtest_enable != None:
            if not is_tsx_run:
                rtm_count = len(
                    workload_df[workload_df['ISA_SET'].str.contains('RTM', na=False)])
                workload_df = workload_df[~workload_df['ISA_SET'].str.contains(
                    'RTM', na=False)]
                print(
                    f"=== DEBUG: Filtered out {rtm_count} RTM instructions (TSX not running) ===")

            workload_df = workload_df[['ISA_SET', 'SHORT']]
            if xtest_enable:
                workload_df.loc[len(workload_df)] = ['XTEST', '']
                print(f"=== DEBUG: Added XTEST instruction ===")

        print(f"=== DEBUG: Final DataFrame has {len(workload_df)} rows ===")

        # Create directory if it doesn't exist
        log_dir = Path(workload_isa_file).parent
        log_dir.mkdir(exist_ok=True)
        print(f"=== DEBUG: Ensured log directory exists: {log_dir} ===")

        workload_df.to_csv(workload_isa_file, index=False)
        print(f"=== DEBUG: CSV file saved to {workload_isa_file} ===")

        # Verify file was created
        if Path(workload_isa_file).exists():
            file_size = Path(workload_isa_file).stat().st_size
            print(
                f"=== DEBUG: CSV file created successfully, size: {file_size} bytes ===")
        else:
            print(f"=== ERROR: CSV file was not created ===")

    except Exception as e:
        print(f"=== ERROR: Failed to create CSV: {e} ===")
        import traceback
        traceback.print_exc()
        raise
