import os
import filecmp
import sys

# Change working directory to the script's directory to make it runnable from anywhere
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Base directories
dir1 = 'result/0-cpuinfo'
dir2 = 'result/0-cpuinfo-all'

# Check if base directories exist
if not os.path.isdir(dir1):
    print(f"Error: Base directory '{dir1}' not found.")
    sys.exit(1)
if not os.path.isdir(dir2):
    print(f"Error: Base directory '{dir2}' not found.")
    sys.exit(1)

# Get subdirectories from dir1 (instance types)
instance_types = sorted([d for d in os.listdir(dir1) if os.path.isdir(os.path.join(dir1, d))])

mismatches = 0
total_compared = 0

print(f"Comparing isaset.csv from '{dir1}' against '{dir2}'...")

for instance in instance_types:
    total_compared += 1
    file1 = os.path.join(dir1, instance, 'isaset.csv')
    file2 = os.path.join(dir2, instance, 'isaset.csv')

    if not os.path.exists(file1):
        # This is unlikely given the loop structure, but a good check.
        # It means the instance folder exists but isaset.csv is missing.
        print(f"[{instance:15s}] WARNING: Source file missing at {file1}")
        continue

    if not os.path.exists(file2):
        print(f"[{instance:15s}] MISMATCH: File is MISSING in '{dir2}'")
        mismatches += 1
        continue

    # Compare the files if both exist
    if not filecmp.cmp(file1, file2, shallow=False):
        print(f"[{instance:15s}] MISMATCH: Files are DIFFERENT")
        mismatches += 1
    else:
        # Files are identical, do nothing to keep the output clean.
        pass

print("-" * 40)
if mismatches == 0:
    print(f"Success: All {total_compared} instances in '{dir1}' have a matching and identical isaset.csv in '{dir2}'.")
else:
    print(f"Failure: Found {mismatches} mismatches or missing files out of {total_compared} instances.")

