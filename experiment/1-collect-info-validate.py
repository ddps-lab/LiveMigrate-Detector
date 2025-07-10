#!/usr/bin/env python3
"""
Validate 1-collect-info experiment results with improved structure
"""

import os
import glob
import re
from pathlib import Path
import sys
from typing import Dict, List, Set, Tuple


class ExperimentValidator:
    def __init__(self, result_dir: str, instance_file: str):
        self.result_dir = result_dir
        self.instance_file = instance_file

        # Expected workloads from the script
        self.expected_workloads = [
            "dask_matmul", "dask_uuid", "falcon_http", "int8dot", "llm",
            "matmul", "pku", "rand", "rsa", "sha", "xgboost"
        ]

        # Expected CRIU files in workload directories
        self.expected_criu_files = [
            "core-*.img", "pages-*.img", "mm-*.img", "files.img",
            "inventory.img", "pstree.img", "stats-dump"
        ]

        # Statistics
        self.stats = {
            'total_expected': 0,
            'total_found': 0,
            'successful_instances': 0,
            'missing_instances': [],
            'failed_instances': [],
            'workload_issues': {},
            'max_pid_stats': {}
        }

    def load_expected_instances(self) -> List[str]:
        """Load expected instances from instance.txt"""
        try:
            with open(self.instance_file, 'r') as f:
                instances = [line.strip() for line in f if line.strip()]
            return instances
        except FileNotFoundError:
            print(f"❌ Instance file not found: {self.instance_file}")
            return []

    def get_actual_instances(self) -> List[str]:
        """Get actual instance directories from result directory"""
        if not os.path.exists(self.result_dir):
            return []

        return [d for d in os.listdir(self.result_dir)
                if os.path.isdir(os.path.join(self.result_dir, d)) and not d.startswith('.')]

    def extract_pid_from_core_file(self, filename: str) -> int:
        """Extract PID from core-*.img filename"""
        match = re.search(r'core-(\d+)\.img', filename)
        return int(match.group(1)) if match else 0

    def validate_global_files(self, instance_path: str) -> List[str]:
        """Validate global files for an instance"""
        issues = []

        # Check user_script.log
        user_script_log = os.path.join(instance_path, "user_script.log")
        if not os.path.exists(user_script_log):
            issues.append("❌ Missing user_script.log")
        elif os.path.getsize(user_script_log) == 0:
            issues.append("⚠️  user_script.log is empty")

        # Check cpuinfo.img
        cpuinfo_img = os.path.join(instance_path, "cpuinfo.img")
        if not os.path.exists(cpuinfo_img):
            issues.append("❌ Missing cpuinfo.img")
        elif os.path.getsize(cpuinfo_img) == 0:
            issues.append("⚠️  cpuinfo.img is empty")

        # Check isaset.csv
        isaset_csv = os.path.join(instance_path, "isaset.csv")
        if not os.path.exists(isaset_csv):
            issues.append("❌ Missing isaset.csv")
        elif os.path.getsize(isaset_csv) == 0:
            issues.append("⚠️  isaset.csv is empty")

        return issues

    def validate_workload_files(self, instance_path: str, workload: str) -> Tuple[List[str], int]:
        """Validate files for a specific workload"""
        issues = []
        max_pid = 0

        # Check workload directory and CRIU files
        workload_dir = os.path.join(instance_path, workload)
        if not os.path.exists(workload_dir):
            issues.append(f"❌ Missing {workload}/ directory")
        else:
            # Check for core-*.img files and find max PID
            core_files = glob.glob(os.path.join(workload_dir, "core-*.img"))
            if not core_files:
                issues.append(f"❌ No core-*.img files in {workload}/")
            else:
                pids = [self.extract_pid_from_core_file(
                    os.path.basename(f)) for f in core_files]
                max_pid = max(pids) if pids else 0

                # Track max PID stats
                if workload not in self.stats['max_pid_stats']:
                    self.stats['max_pid_stats'][workload] = []
                self.stats['max_pid_stats'][workload].append(max_pid)

            # Check for essential CRIU files
            required_files = ["inventory.img", "pstree.img", "stats-dump"]
            for req_file in required_files:
                if not os.path.exists(os.path.join(workload_dir, req_file)):
                    issues.append(f"❌ Missing {workload}/{req_file}")

        # Check .csv files
        for suffix in ["native.csv", "bytecode.csv"]:
            csv_file = os.path.join(instance_path, f"{workload}.{suffix}")
            if not os.path.exists(csv_file):
                issues.append(f"❌ Missing {workload}.{suffix}")
            elif os.path.getsize(csv_file) <= 1:
                issues.append(f"⚠️  {workload}.{suffix} too small (≤1 byte)")

        # Check workload .log file
        log_file = os.path.join(instance_path, f"{workload}.log")
        if not os.path.exists(log_file):
            issues.append(f"❌ Missing {workload}.log")
        elif os.path.getsize(log_file) <= 1:
            issues.append(f"⚠️  {workload}.log too small (≤1 byte)")

        # Check _ept.log files (execution path tracking)
        for suffix in ["native_ept.log", "bytecode_ept.log"]:
            ept_log_file = os.path.join(
                instance_path, f"{workload}_{suffix}")
            if not os.path.exists(ept_log_file):
                issues.append(
                    f"⚠️  Missing {workload}_{suffix} (execution path tracking)")
            elif os.path.getsize(ept_log_file) <= 1:
                issues.append(f"⚠️  {workload}_{suffix} too small (≤1 byte)")

        return issues, max_pid

    def validate_instance(self, instance: str) -> Dict:
        """Validate a single instance"""
        instance_path = os.path.join(self.result_dir, instance)
        result = {
            'instance': instance,
            'issues': [],
            'workload_success': 0,
            'max_pids': {}
        }

        # Validate global files
        global_issues = self.validate_global_files(instance_path)
        result['issues'].extend(global_issues)

        # Validate each workload
        for workload in self.expected_workloads:
            workload_issues, max_pid = self.validate_workload_files(
                instance_path, workload)

            if workload_issues:
                result['issues'].extend(workload_issues)
                if workload not in self.stats['workload_issues']:
                    self.stats['workload_issues'][workload] = 0
                self.stats['workload_issues'][workload] += 1
            else:
                result['workload_success'] += 1

            result['max_pids'][workload] = max_pid

        return result

    def print_instance_comparison(self, expected_instances: List[str], actual_instances: List[str]):
        """Print comparison between expected and actual instances"""
        expected_set = set(expected_instances)
        actual_set = set(actual_instances)

        missing_instances = expected_set - actual_set
        extra_instances = actual_set - expected_set

        print("📊 INSTANCE COMPARISON")
        print("=" * 80)
        print(
            f"📋 Expected instances (from {self.instance_file}): {len(expected_instances)}")
        print(
            f"📂 Found instances (in {self.result_dir}): {len(actual_instances)}")
        print()

        if missing_instances:
            print(f"❌ Missing instances ({len(missing_instances)}):")
            for instance in sorted(missing_instances):
                print(f"  • {instance}")
            print()

        if extra_instances:
            print(f"➕ Extra instances ({len(extra_instances)}):")
            for instance in sorted(extra_instances):
                print(f"  • {instance}")
            print()

        if not missing_instances and not extra_instances:
            print("✅ All expected instances are present!")
            print()

        self.stats['missing_instances'] = list(missing_instances)
        return missing_instances, extra_instances

    def print_validation_summary(self, validation_results: List[Dict]):
        """Print overall validation summary"""
        total_instances = len(validation_results)
        successful_instances = sum(
            1 for r in validation_results if not r['issues'])
        total_issues = sum(len(r['issues']) for r in validation_results)

        print("📈 VALIDATION SUMMARY")
        print("=" * 80)
        print(f"🏗️  Total validated instances: {total_instances}")
        print(
            f"✅ Fully successful instances: {successful_instances} ({successful_instances/total_instances*100:.1f}%)")
        print(f"⚠️  Total issues found: {total_issues}")

        # Workload issues summary
        if self.stats['workload_issues']:
            print(f"\n🔍 Issues by workload:")
            for workload, count in sorted(self.stats['workload_issues'].items()):
                print(f"  • {workload}: {count} instances with issues")

        # Max PID statistics
        if self.stats['max_pid_stats']:
            all_pids = []
            for pids in self.stats['max_pid_stats'].values():
                all_pids.extend(pids)
            if all_pids:
                overall_max_pid = max(all_pids)
                print(
                    f"\n🆔 Maximum PID found across all experiments: {overall_max_pid}")

        # Find instances with most issues
        failed_instances = [(r['instance'], len(r['issues']))
                            for r in validation_results if r['issues']]
        if failed_instances:
            failed_instances.sort(key=lambda x: x[1], reverse=True)
            print(f"\n🚨 Instances with most issues:")
            for instance, count in failed_instances[:5]:  # Top 5
                print(f"  • {instance}: {count} issues")

        self.stats.update({
            'total_found': total_instances,
            'successful_instances': successful_instances,
            'failed_instances': failed_instances
        })

    def run_validation(self) -> int:
        """Run complete validation process"""
        print("🔍 Validating 1-collect-info experiment results...")
        print(f"📂 Result directory: {self.result_dir}")
        print(f"📄 Instance file: {self.instance_file}")
        print(f"🎯 Expected workloads: {', '.join(self.expected_workloads)}")
        print("=" * 80)
        print()

        # Load expected instances and compare with actual
        expected_instances = self.load_expected_instances()
        actual_instances = self.get_actual_instances()

        if not expected_instances:
            return 1

        if not actual_instances:
            print(f"❌ No instance directories found in {self.result_dir}")
            return 1

        self.stats['total_expected'] = len(expected_instances)

        # Compare expected vs actual instances
        missing_instances, extra_instances = self.print_instance_comparison(
            expected_instances, actual_instances)

        # Validate existing instances
        validation_results = []
        for instance in sorted(actual_instances):
            print(f"🔬 Validating instance: {instance}")
            result = self.validate_instance(instance)
            validation_results.append(result)

            if result['issues']:
                print(f"  ⚠️  Found {len(result['issues'])} issues:")
                for issue in result['issues']:
                    print(f"     {issue}")
            else:
                print(f"  🎉 All checks passed!")

            workload_success = result['workload_success']
            print(
                f"  📊 Workload success rate: {workload_success}/{len(self.expected_workloads)} ({workload_success/len(self.expected_workloads)*100:.1f}%)")
            print()

        # Print overall summary
        print("=" * 80)
        self.print_validation_summary(validation_results)
        print("\n" + "=" * 80)

        # Determine exit code
        if missing_instances or self.stats['failed_instances']:
            print(f"⚠️  Validation completed with issues")
            return 1
        else:
            print("🎉 ALL EXPERIMENTS COMPLETED SUCCESSFULLY!")
            return 0


def main():
    result_dir = "result/1-collect-info"
    instance_file = "instance.txt"

    # Check if files exist
    if not os.path.exists(result_dir):
        print(f"❌ Result directory not found: {result_dir}")
        return 1

    if not os.path.exists(instance_file):
        print(f"❌ Instance file not found: {instance_file}")
        return 1

    # Run validation
    validator = ExperimentValidator(result_dir, instance_file)
    return validator.run_validation()


if __name__ == "__main__":
    sys.exit(main())
