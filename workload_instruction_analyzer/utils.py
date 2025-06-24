import pandas as pd
import time
import os

from pathlib import Path

print("=== DEBUG: utils.py imported ===")

rootdir = str(Path(__file__).resolve().parent)
print(f"=== DEBUG: Root directory: {rootdir} ===")

workload_isa_file = f'{rootdir}/log/isa_set.csv'
print(f"=== DEBUG: ISA set file path: {workload_isa_file} ===")


def create_csv(executable_instructions, is_tsx_run, xtest_enable):
    """Create CSV file from instruction data"""
    print("=== DEBUG: Creating CSV file ===")
    start_time = time.time()

    try:
        # Create DataFrame
        df = pd.DataFrame(executable_instructions)

        if df.empty:
            print("=== WARNING: No instructions to write to CSV ===")
            return

        # Remove duplicates
        original_count = len(df)
        df = df.drop_duplicates()
        duplicate_count = original_count - len(df)

        if duplicate_count > 0:
            print(
                f"=== DEBUG: Removed {duplicate_count} duplicate instructions ===")

        # Add metadata columns
        df['TSX_RUN'] = is_tsx_run
        df['XTEST_ENABLE'] = xtest_enable

        # Generate filename
        timestamp = int(time.time())
        filename = f'isa_set_{timestamp}.csv'

        # Write to CSV
        df.to_csv(filename, index=False)

        # Verify file creation
        if os.path.exists(filename):
            file_size = os.path.getsize(filename)
            print(
                f"=== DEBUG: CSV created successfully: {filename} ({file_size} bytes) ===")
        else:
            print("=== ERROR: CSV file was not created ===")

        end_time = time.time()
        print(f"=== DEBUG: CSV creation took {end_time - start_time:.3f}s ===")

    except Exception as e:
        print(f"=== ERROR: Failed to create CSV: {e} ===")
        import traceback
        traceback.print_exc()
