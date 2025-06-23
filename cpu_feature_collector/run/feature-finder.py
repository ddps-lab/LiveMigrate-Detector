#!/usr/bin/env python3
"""
Feature Finder Script

Usage: python3 feature-finder.py <group>.json <feature_name>
Example: python3 feature-finder.py groups-no-metal.json AVX512_BF16_128

This script finds groups where the specified CPU feature has value 1.
"""

import json
import csv
import sys
import os
from pathlib import Path


def load_group_file(group_file_path):
    """Load the group JSON file"""
    try:
        with open(group_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Group file '{group_file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{group_file_path}'.")
        sys.exit(1)


def get_feature_value_from_csv(instance_name, feature_name):
    """Get the feature value from the CSV file for a given instance"""
    csv_file_path = f"result/{instance_name}.csv"

    if not os.path.exists(csv_file_path):
        return None

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)

            # Read header (feature names)
            headers = next(reader)

            # Read values
            values = next(reader)

            # Find the feature index
            if feature_name not in headers:
                return None

            feature_index = headers.index(feature_name)
            return int(values[feature_index])

    except (FileNotFoundError, IndexError, ValueError, StopIteration):
        return None


def find_groups_with_feature(group_data, feature_name):
    """Find groups where the specified feature has value 1"""
    matching_groups = []

    for group in group_data.get('groups', []):
        group_id = group.get('group_id')
        instances = group.get('instances', [])

        if not instances:
            continue

        # Take the first instance from the group to check the feature
        sample_instance = instances[0]
        feature_value = get_feature_value_from_csv(
            sample_instance, feature_name)

        if feature_value == 1:
            matching_groups.append({
                'group_id': group_id,
                'instances': instances,
                'count': len(instances),
                'sample_instance': sample_instance
            })

    return matching_groups


def print_results(matching_groups, feature_name, group_file):
    """Print the results in a formatted way"""
    if not matching_groups:
        print(f"No groups found with feature '{feature_name}' = 1")
        return

    print(f"Groups with feature '{feature_name}' = 1 (from {group_file}):")
    print("-" * 60)

    total_instances = 0
    for group in matching_groups:
        total_instances += group['count']
        print(f"Group {group['group_id']}: {group['count']} instances")
        print(f"  Sample instance: {group['sample_instance']}")
        print(f"  Instances: {', '.join(group['instances'])}")
        print()

    print(f"Summary:")
    print(f"  Total matching groups: {len(matching_groups)}")
    print(f"  Total instances with feature: {total_instances}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 feature-finder.py <group>.json <feature_name>")
        print("Example: python3 feature-finder.py groups-no-metal.json AVX512_BF16_128")
        sys.exit(1)

    group_file = sys.argv[1]
    feature_name = sys.argv[2]

    # Load group data
    group_data = load_group_file(group_file)

    # Find groups with the specified feature
    matching_groups = find_groups_with_feature(group_data, feature_name)

    # Print results
    print_results(matching_groups, feature_name, group_file)


if __name__ == "__main__":
    main()
