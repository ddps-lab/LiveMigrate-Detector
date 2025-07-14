import os
import glob
from collections import defaultdict
import pandas as pd
import itertools
from tqdm import tqdm
import multiprocessing

# Global variables for worker processes to avoid passing large data repeatedly
g_workloads = []
g_actuals_map = {}
g_instance_isa_sets = {}
g_workload_isa_sets = {}


def init_worker(workloads, actuals, instance_isas, workload_isas):
    """Initializer for multiprocessing pool to load shared data into each worker."""
    global g_workloads, g_actuals_map, g_instance_isa_sets, g_workload_isa_sets
    g_workloads = workloads
    g_actuals_map = actuals
    g_instance_isa_sets = instance_isas
    g_workload_isa_sets = workload_isas


def evaluate_combination(combo):
    """
    Evaluates a single combination of representative instances.
    This function is executed by worker processes and uses global data.
    """
    reps = sorted(list(combo))
    metrics = defaultdict(int)

    for inst_dst in reps:
        for inst_src in reps:
            if inst_src == inst_dst:
                continue

            src_supported_isa = g_instance_isa_sets.get(inst_src, set())
            dst_supported_isa = g_instance_isa_sets.get(inst_dst, set())

            for workload in g_workloads:
                key = (inst_src, inst_dst, workload)
                if key not in g_actuals_map:
                    continue
                actual_ok = g_actuals_map[key]

                workload_isa = g_workload_isa_sets.get(
                    (inst_src, workload), None)

                predicts_ok = False
                if workload_isa is not None:
                    normalized_isaset = workload_isa.intersection(
                        src_supported_isa)
                    unsupported_features = normalized_isaset - dst_supported_isa
                    predicts_ok = len(unsupported_features) == 0
                else:
                    predicts_ok = False

                if predicts_ok and actual_ok:
                    metrics['TP'] += 1
                elif predicts_ok and not actual_ok:
                    metrics['FP'] += 1
                elif not predicts_ok and not actual_ok:
                    metrics['TN'] += 1
                elif not predicts_ok and actual_ok:
                    metrics['FN'] += 1

    precision, recall = calculate_metrics(metrics)
    return precision, recall, metrics, combo


def read_isaset_from_csv(filepath):
    """
    Reads an ISA set from a CSV file, handling two different formats.
    """
    if not os.path.exists(filepath):
        return set()

    try:
        # Format for 1-collect-info CSVs (native, bytecode)
        if '1-collect-info' in filepath:
            df = pd.read_csv(filepath, header=0)
            if df.empty or 'ISA_SET' not in df.columns:
                return set()
            return set(df['ISA_SET'].astype(str).tolist())

        # Format for 2-compatibility-check isaset.csv
        elif '2-compatibility-check' in filepath and 'isaset.csv' in filepath:
            df = pd.read_csv(filepath, header=None)
            if df.shape[0] < 2:
                return set()

            supported_isa = set()
            feature_names = df.iloc[0].astype(str).tolist()
            feature_values = df.iloc[1].astype(str).tolist()

            for name, value in zip(feature_names, feature_values):
                if value == '1':
                    supported_isa.add(name)
            return supported_isa

        else:  # Fallback for any other format
            df = pd.read_csv(filepath, header=None)
            if df.empty:
                return set()
            return set(df[0].astype(str).tolist())

    except Exception as e:
        print(f"Warning: Could not read or parse ISA set file {filepath}: {e}")
        return set()


def get_valid_instances(base_dir):
    """Filters instances based on self-checks."""
    print("--- Step 1: Filtering Abnormal Instances ---")
    if not os.path.isdir(base_dir):
        print(f"Error: Base directory not found at '{base_dir}'")
        return []

    all_instances = sorted([d for d in os.listdir(
        base_dir) if os.path.isdir(os.path.join(base_dir, d))])

    valid_instances = set()
    for instance in all_instances:
        check_log_path = os.path.join(
            base_dir, instance, f"{instance}_check.log")
        if os.path.exists(check_log_path):
            with open(check_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                if "Error" not in f.read():
                    valid_instances.add(instance)
                else:
                    print(f"  - Filtering out {instance} (failed self-check).")
        else:
            print(f"  - Filtering out {instance} (missing self-check log).")

    final_valid_instances = sorted(list(valid_instances))
    print(
        f"\nFound {len(final_valid_instances)} valid instances for analysis.")
    return final_valid_instances


def group_instances(valid_instances, base_dir):
    """Groups instances based on mutual migration compatibility."""
    print("\n--- Step 2: Grouping Instances ---")
    adj = defaultdict(list)
    for i in range(len(valid_instances)):
        for j in range(i + 1, len(valid_instances)):
            inst1, inst2 = valid_instances[i], valid_instances[j]
            check1_path = os.path.join(base_dir, inst2, f"{inst1}_check.log")
            check2_path = os.path.join(base_dir, inst1, f"{inst2}_check.log")

            try:
                with open(check1_path, 'r', encoding='utf-8', errors='ignore') as f:
                    compat_1_to_2 = "Error" not in f.read()
                with open(check2_path, 'r', encoding='utf-8', errors='ignore') as f:
                    compat_2_to_1 = "Error" not in f.read()

                if compat_1_to_2 and compat_2_to_1:
                    adj[inst1].append(inst2)
                    adj[inst2].append(inst1)
            except FileNotFoundError:
                continue

    groups, visited = [], set()
    for instance in valid_instances:
        if instance not in visited:
            group, q = [], [instance]
            visited.add(instance)
            head = 0
            while head < len(q):
                u = q[head]
                head += 1
                group.append(u)
                for v in adj[u]:
                    if v not in visited:
                        visited.add(v)
                        q.append(v)
            groups.append(sorted(group))

    print("Instance Groups:")
    for i, group in enumerate(groups):
        print(f"  Group {i+1}: {group}")

    return groups


def get_workloads(base_dir_1, reps):
    """Discovers unique workloads from csv files, excluding 'isaset'."""
    workloads = set()
    for rep in reps:
        path_pattern = os.path.join(base_dir_1, rep, "*.csv")
        csv_files = glob.glob(path_pattern)
        for f in csv_files:
            filename = os.path.basename(f)
            # Extracts 'workload' from 'workload.native.csv' or 'workload.bytecode.csv'
            workload = filename.split('.')[0]
            workloads.add(workload)

    sorted_workloads = sorted(list(workloads))
    if 'isaset' in sorted_workloads:
        sorted_workloads.remove('isaset')
        print("\nNote: 'isaset' has been excluded from the workload analysis.")

    print(
        f"\nFound {len(sorted_workloads)} unique workloads: {sorted_workloads}")
    return sorted_workloads


def calculate_metrics(results):
    tp, fp, tn, fn = results['TP'], results['FP'], results['TN'], results['FN']
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    return precision, recall


def find_best_reps_for_bept(groups, all_workloads, base_dir_1, base_dir_2):
    """
    Finds the best set of representative instances by testing all combinations
    to maximize BEPT Recall while keeping Precision at 1.0.
    """
    print("\n--- Step 2.5: Optimizing Representative Set for BEPT (Precision=1, Max Recall) ---")

    # 1. Pre-calculate all possible actuals and ISA sets to avoid re-reading files.
    all_instances = sorted(
        list(set(inst for group in groups for inst in group)))
    # Workloads are now passed as an argument.
    if not all_workloads:
        print("Warning: No workloads found for any instance, cannot optimize. Falling back to default.")
        return [g[0] for g in groups if g]

    actuals_map = {}
    for inst_dst in all_instances:
        for inst_src in all_instances:
            if inst_src == inst_dst:
                continue
            for workload in all_workloads:
                restore_log = os.path.join(
                    base_dir_2, inst_dst, f"{inst_src}_{workload}_restore.log")
                if os.path.exists(restore_log):
                    actual_ok = "Success" in open(
                        restore_log, 'r', errors='ignore').read()
                    actuals_map[(inst_src, inst_dst, workload)] = actual_ok

    instance_isa_sets = {inst: read_isaset_from_csv(
        os.path.join(base_dir_2, inst, "isaset.csv")) for inst in all_instances}

    workload_isa_sets = {}
    for inst in all_instances:
        for workload in all_workloads:
            workload_isa_path = os.path.join(
                base_dir_1, inst, f"{workload}.bytecode.csv")
            if os.path.exists(workload_isa_path):
                workload_isa_sets[(inst, workload)
                                  ] = read_isaset_from_csv(workload_isa_path)

    # 2. Iterate through combinations using multiprocessing
    all_combinations = list(itertools.product(*groups))
    print(
        f"Testing {len(all_combinations)} representative combinations using multiprocessing...")

    best_combination = None
    max_recall = -1.0
    best_combo_metrics = {}

    init_args = (all_workloads, actuals_map,
                 instance_isa_sets, workload_isa_sets)
    with multiprocessing.Pool(initializer=init_worker, initargs=init_args) as pool:
        results_iterator = pool.imap_unordered(
            evaluate_combination, all_combinations)

        # Process results with tqdm for a progress bar
        results = list(tqdm(results_iterator, total=len(
            all_combinations), desc="Optimizing Representatives"))

    for precision, recall, metrics, combo in results:
        if precision == 1.0 and recall > max_recall:
            max_recall = recall
            best_combination = sorted(list(combo))
            best_combo_metrics = metrics

    if best_combination:
        print(
            f"\nFound best representative set with Precision=1.0 and Recall={max_recall:.4f}")
        print(f"  - Representatives: {best_combination}")
        print(
            f"  - Metrics: TP={best_combo_metrics['TP']}, FP={best_combo_metrics['FP']}, TN={best_combo_metrics['TN']}, FN={best_combo_metrics['FN']}")
        return best_combination
    else:
        print("\nCould not find a combination with Precision=1.0. Falling back to default.")
        default_reps = [g[0] for g in groups if g]
        print(f"  - Default Representatives: {default_reps}")
        return default_reps


def print_results(title, metrics_by_workload, overall_metrics):
    print(f"\n--- Results: {title} ---")
    print("\n--- Per-Workload Metrics ---")
    for workload, metrics in sorted(metrics_by_workload.items()):
        precision, recall = calculate_metrics(metrics)
        print(f"Workload: {workload}")
        print(
            f"  - Precision: {precision:.4f}, Recall: {recall:.4f}, TP: {metrics['TP']}, FP: {metrics['FP']}, TN: {metrics['TN']}, FN: {metrics['FN']}")

    print("\n--- Overall Metrics ---")
    precision, recall = calculate_metrics(overall_metrics)
    print(
        f"TP: {overall_metrics['TP']}, FP: {overall_metrics['FP']}, TN: {overall_metrics['TN']}, FN: {overall_metrics['FN']}")
    print(f"Overall Precision: {precision:.4f}, Overall Recall: {recall:.4f}")
    print("----------------------------------\n")


def analyze_criu_performance(reps, workloads, base_dir_2, actuals_map, preds_map):
    print("\n--- Step 3.1: Calculating CRIU Precision & Recall ---")
    metrics = {w: defaultdict(int) for w in workloads}
    overall = defaultdict(int)

    for inst_dst in reps:
        for inst_src in reps:
            if inst_src == inst_dst:
                continue
            check_log = os.path.join(
                base_dir_2, inst_dst, f"{inst_src}_check.log")
            criu_predicts_ok = "Error" not in open(
                check_log, 'r', errors='ignore').read() if os.path.exists(check_log) else False

            for workload in workloads:
                key = (inst_src, inst_dst, workload)
                restore_log = os.path.join(
                    base_dir_2, inst_dst, f"{inst_src}_{workload}_restore.log")
                if not os.path.exists(restore_log):
                    continue  # Skip if no actual result

                actual_ok = "Success" in open(restore_log, 'r', errors='ignore').read(
                ) if os.path.exists(restore_log) else False
                actuals_map[key] = actual_ok
                preds_map[key] = criu_predicts_ok

                if criu_predicts_ok and actual_ok:
                    metrics[workload]['TP'] += 1
                elif criu_predicts_ok and not actual_ok:
                    metrics[workload]['FP'] += 1
                elif not criu_predicts_ok and not actual_ok:
                    metrics[workload]['TN'] += 1
                elif not criu_predicts_ok and actual_ok:
                    metrics[workload]['FN'] += 1

    for w in workloads:
        [overall.update({k: overall[k] + metrics[w][k]}) for k in metrics[w]]
    return metrics, overall


def analyze_isa_method(reps, workloads, base_dir_1, base_dir_2, method_name, file_suffix, actuals_map, preds_map):
    """Generic analyzer for ISA-based methods (EPT, BEPT)."""
    print(f"\n--- Step 3.2: Calculating {method_name} Precision & Recall ---")
    metrics = {w: defaultdict(int) for w in workloads}
    overall = defaultdict(int)
    instance_isa_sets = {inst: read_isaset_from_csv(
        os.path.join(base_dir_2, inst, "isaset.csv")) for inst in reps}

    for inst_dst in reps:
        for inst_src in reps:
            if inst_src == inst_dst:
                continue
            src_supported_isa = instance_isa_sets.get(inst_src, set())
            dst_supported_isa = instance_isa_sets.get(inst_dst, set())

            for workload in workloads:
                key = (inst_src, inst_dst, workload)
                # Skip if we don't have an actual result for this combination
                if key not in actuals_map:
                    continue
                actual_ok = actuals_map[key]

                workload_isa_path = os.path.join(
                    base_dir_1, inst_src, f"{workload}{file_suffix}")
                if not os.path.exists(workload_isa_path):
                    preds_map[key] = (
                        False, {'workload_data_missing'})  # Predict fail
                    if not actual_ok:
                        metrics[workload]['TN'] += 1
                    else:
                        metrics[workload]['FN'] += 1
                    continue

                workload_isa = read_isaset_from_csv(workload_isa_path)
                normalized_isaset = workload_isa.intersection(
                    src_supported_isa)
                unsupported_features = normalized_isaset - dst_supported_isa
                predicts_ok = len(unsupported_features) == 0
                preds_map[key] = (predicts_ok, unsupported_features)

                if predicts_ok and actual_ok:
                    metrics[workload]['TP'] += 1
                elif predicts_ok and not actual_ok:
                    metrics[workload]['FP'] += 1
                elif not predicts_ok and not actual_ok:
                    metrics[workload]['TN'] += 1
                elif not predicts_ok and actual_ok:
                    metrics[workload]['FN'] += 1

    for w in workloads:
        [overall.update({k: overall[k] + metrics[w][k]}) for k in metrics[w]]
    return metrics, overall


def write_detailed_log(log_path, wrong_bept_log_path, reps, workloads, actuals, criu_preds, ept_preds, bept_preds):
    print(f"\n--- Writing detailed analysis log to {log_path} ---")
    print(f"--- Writing BEPT mismatch log to {wrong_bept_log_path} ---")

    with open(log_path, 'w') as f_all, open(wrong_bept_log_path, 'w') as f_wrong_bept:
        for inst_src in sorted(reps):
            for inst_dst in sorted(reps):
                if inst_src == inst_dst:
                    continue

                header = f"\n{'='*40}\nMigration Path: {inst_src} -> {inst_dst}\n{'='*40}\n"
                path_content_blocks = []
                wrong_bept_blocks = []

                # Get all workloads that have an actual result for this pair
                sorted_workloads_for_pair = sorted(
                    [w for w in workloads if (inst_src, inst_dst, w) in actuals])

                if not sorted_workloads_for_pair:
                    f_all.write(header)
                    f_all.write(
                        "No restore logs found for this migration path.\n")
                    continue

                for workload in sorted_workloads_for_pair:
                    key = (inst_src, inst_dst, workload)
                    actual_ok = actuals.get(key, False)
                    result_str = "YES" if actual_ok else "NO"

                    # CRIU
                    criu_pred_ok = criu_preds.get(key, False)
                    criu_pred_str = "YES" if criu_pred_ok else "NO"

                    # EPT
                    ept_pred_ok, ept_features = ept_preds.get(
                        key, (False, {'no_prediction_data'}))
                    ept_pred_str = "YES" if ept_pred_ok else f"NO, missing: {sorted(list(ept_features))}"

                    # BEPT
                    bept_pred_ok, bept_features = bept_preds.get(
                        key, (False, {'no_prediction_data'}))
                    bept_pred_str = "YES" if bept_pred_ok else f"NO, missing: {sorted(list(bept_features))}"

                    block = (
                        f"\nWorkload: {workload}\n"
                        f"- CRIU:   {criu_pred_str}\n"
                        f"- EPT:    {ept_pred_str}\n"
                        f"- BEPT:   {bept_pred_str}\n"
                        f"- RESULT: {result_str}\n"
                    )
                    path_content_blocks.append(block)

                    if bept_pred_ok != actual_ok:
                        wrong_bept_blocks.append(block)

                if path_content_blocks:
                    f_all.write(header)
                    f_all.write("".join(path_content_blocks))

                if wrong_bept_blocks:
                    f_wrong_bept.write(header)
                    f_wrong_bept.write("".join(wrong_bept_blocks))


def analyze_experiments():
    # Define workloads to exclude from the analysis
    excluded_workloads = ["dask_matmul"]

    script_dir = os.path.dirname(os.path.realpath(__file__))
    base_dir_1 = os.path.join(script_dir, 'result/1-collect-info')
    base_dir_2 = os.path.join(script_dir, 'result/2-compatibility-check')

    valid_instances = get_valid_instances(base_dir_2)
    if not valid_instances:
        return

    instance_groups = group_instances(valid_instances, base_dir_2)
    if not instance_groups:
        return

    # Get all workloads first from all possible instances
    all_possible_instances = sorted(
        list(set(inst for group in instance_groups for inst in group)))
    workloads = get_workloads(base_dir_1, all_possible_instances)

    # Filter out excluded workloads BEFORE optimization
    if excluded_workloads:
        print(f"\n--- Excluding Workloads: {excluded_workloads} ---")
        original_count = len(workloads)
        workloads = [w for w in workloads if w not in excluded_workloads]
        print(f"Workloads remaining: {original_count} -> {len(workloads)}")

    if not workloads:
        print("No workloads left to analyze after exclusion.")
        return

    # Find the best representative set based on BEPT performance using the FILTERED workloads
    rep_instances = find_best_reps_for_bept(
        instance_groups, workloads, base_dir_1, base_dir_2)
    print(
        f"\n--- Using optimized representative set for final analysis: {rep_instances} ---")

    # --- Data Structures for Logging ---
    actual_outcomes = {}
    criu_predictions = {}
    ept_predictions = {}
    bept_predictions = {}

    # --- Run Analyses ---
    criu_metrics, criu_overall = analyze_criu_performance(
        rep_instances, workloads, base_dir_2, actual_outcomes, criu_predictions)
    ept_metrics, ept_overall = analyze_isa_method(
        rep_instances, workloads, base_dir_1, base_dir_2, "EPT", ".native.csv", actual_outcomes, ept_predictions)
    bept_metrics, bept_overall = analyze_isa_method(
        rep_instances, workloads, base_dir_1, base_dir_2, "BEPT (Proposed)", ".bytecode.csv", actual_outcomes, bept_predictions)

    # --- Write Log ---
    log_file_path = os.path.join(script_dir, 'result', 'analysis_log.txt')
    wrong_bept_log_path = os.path.join(
        script_dir, 'result', 'analysis_log_wrong_bept.txt')
    write_detailed_log(log_file_path, wrong_bept_log_path, rep_instances, workloads,
                       actual_outcomes, criu_predictions, ept_predictions, bept_predictions)

    # --- Print Results ---
    print_results("CRIU", criu_metrics, criu_overall)
    print_results("EPT", ept_metrics, ept_overall)
    print_results("BEPT (Proposed Method)", bept_metrics, bept_overall)


if __name__ == '__main__':
    analyze_experiments()
