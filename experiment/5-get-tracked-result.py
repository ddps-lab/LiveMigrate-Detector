import os
import re
import pandas as pd

BTRACKING_DIR = '/Users/cg10036/LiveMigrate-Detector/experiment/result/3-get-tracked-module-btracking/'
PYCG_DIR = '/Users/cg10036/LiveMigrate-Detector/experiment/result/4-get-tracked-module-pycg/'


def parse_log_file(file_path):
    """
    Parses a log file and returns a set of unique module paths.
    A module is identified as a python file within 'dist-packages' or 'site-packages'.
    For pycg, it also considers the main script files not in those packages.
    """
    if not os.path.exists(file_path):
        return set(), set()

    package_modules = set()
    other_files = set()

    path_regex = re.compile(r'openat\(AT_FDCWD, "([^"]+\.(?:py|pyc))"')

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            match = path_regex.search(line)
            if not match:
                continue

            path = match.group(1)

            # Normalize path
            module_path = None
            is_package_module = False

            site_pkg_str = 'site-packages/'
            dist_pkg_str = 'dist-packages/'

            if site_pkg_str in path:
                start_index = path.find(site_pkg_str) + len(site_pkg_str)
                module_path = path[start_index:]
                is_package_module = True
            elif dist_pkg_str in path:
                start_index = path.find(dist_pkg_str) + len(dist_pkg_str)
                module_path = path[start_index:]
                is_package_module = True
            else:
                module_path = path

            # Clean up path details
            if module_path:
                module_path = re.sub(r'/__pycache__', '', module_path)
                module_path = re.sub(r'\.cpython-[0-9]+', '', module_path)
                if module_path.endswith('.pyc'):
                    module_path = module_path.replace('.pyc', '.py')

                if is_package_module:
                    package_modules.add(module_path)
                else:
                    other_files.add(module_path)

    return package_modules, other_files


def main():
    """
    Main function to compare btracking and pycg results.
    """
    workloads = sorted([
        f.replace('.txt', '') for f in os.listdir(BTRACKING_DIR)
        if f.endswith('.txt')
    ])

    results = []

    for workload in workloads:
        btracking_file = os.path.join(BTRACKING_DIR, f"{workload}.txt")
        pycg_file = os.path.join(PYCG_DIR, f"{workload}.txt")

        btracking_pkg_modules, _ = parse_log_file(btracking_file)
        pycg_pkg_modules, pycg_other_files = parse_log_file(pycg_file)

        print(f"--- Workload: {workload} ---")

        print(f"\n[btracking] - {len(btracking_pkg_modules) + 1} modules:")
        btracking_list = ["(main script)"] + \
            sorted(list(btracking_pkg_modules))
        print(", ".join(btracking_list))

        all_pycg_modules = sorted(
            list(pycg_pkg_modules.union(pycg_other_files)))
        pycg_count = len(all_pycg_modules)
        pycg_table_value = pycg_count

        if pycg_count == 0:
            print(f"\n[pycg] - Error")
            pycg_table_value = "Error"
        else:
            print(f"\n[pycg] - {pycg_count} modules:")
            print(", ".join(all_pycg_modules))

        print("-" * (len(workload) + 20))

        btracking_count = len(btracking_pkg_modules) + 1

        results.append({
            'Workload': workload,
            'btracking': btracking_count,
            'pycg': pycg_table_value,
        })

    df = pd.DataFrame(results)

    print("\n\nComparison of tracked modules (Plain Text):")
    print(df.to_string(index=False))

    print("\n\nComparison of tracked modules (Markdown):")
    print(df.to_markdown(index=False))


if __name__ == "__main__":
    main()
