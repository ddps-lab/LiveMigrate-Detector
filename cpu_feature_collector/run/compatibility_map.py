#!/usr/bin/env python3
"""
CPU Feature 호환성 맵 생성기

사용법: python3 compatibility_map.py <groups.json>

그룹 간 CPU feature 호환성을 분석하여 트리로 표시합니다.
같은 그룹 내의 인스턴스들은 동일한 CPU feature를 가지므로,
각 그룹의 첫 번째 인스턴스 데이터를 대표값으로 사용합니다.
"""

import json
import csv
import sys
import os
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class CPUFeatureAnalyzer:
    def __init__(self, result_dir: str = "result"):
        self.result_dir = result_dir
        self.groups = {}
        self.group_features = {}

    def load_groups(self, groups_file: str):
        """그룹 정보를 로드합니다."""
        with open(groups_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.groups = {}
        for group in data['groups']:
            group_id = group['group_id']
            instances = group['instances']
            self.groups[group_id] = {
                'instances': instances,
                'count': group['count'],
                'representative': instances[0]  # 첫 번째 인스턴스를 대표로 사용
            }

        print(f"로드된 그룹 수: {len(self.groups)}")
        return data['description']

    def load_cpu_features(self, instance_name: str) -> Dict[str, int]:
        """특정 인스턴스의 CPU feature를 로드합니다."""
        csv_file = os.path.join(self.result_dir, f"{instance_name}.csv")

        if not os.path.exists(csv_file):
            print(f"경고: {csv_file} 파일을 찾을 수 없습니다.")
            return {}

        try:
            with open(csv_file, 'r') as f:
                reader = csv.reader(f)
                headers = next(reader)
                values = next(reader)

                features = {}
                for header, value in zip(headers, values):
                    features[header] = int(value)

                return features
        except Exception as e:
            print(f"오류: {csv_file} 파일 읽기 실패 - {e}")
            return {}

    def analyze_all_groups(self):
        """모든 그룹의 CPU feature를 분석합니다."""
        print("\n각 그룹의 CPU feature 분석 중...")

        for group_id, group_info in self.groups.items():
            representative = group_info['representative']
            features = self.load_cpu_features(representative)

            if features:
                self.group_features[group_id] = {
                    'features': features,
                    'representative': representative,
                    'instance_count': group_info['count'],
                    'instances': group_info['instances']
                }
                print(
                    f"그룹 {group_id}: {representative} ({group_info['count']}개 인스턴스)")
            else:
                print(f"그룹 {group_id}: {representative} - 데이터 없음")

    def is_compatible(self, group1_id: int, group2_id: int) -> bool:
        """두 그룹 간 호환성을 확인합니다. (group1이 group2의 부분집합인지)"""
        if group1_id not in self.group_features or group2_id not in self.group_features:
            return False

        features1 = self.group_features[group1_id]['features']
        features2 = self.group_features[group2_id]['features']

        # group1의 모든 활성화된 feature가 group2에도 있는지 확인
        for feature, value in features1.items():
            if value == 1 and features2.get(feature, 0) == 0:
                return False

        return True

    def find_compatibility_relationships(self) -> Dict[int, List[int]]:
        """그룹 간 호환성 관계를 찾습니다."""
        compatibility = defaultdict(list)

        group_ids = list(self.group_features.keys())

        for i, group1 in enumerate(group_ids):
            for j, group2 in enumerate(group_ids):
                if i != j and self.is_compatible(group1, group2):
                    compatibility[group1].append(group2)

        return compatibility

    def calculate_feature_counts(self) -> Dict[int, int]:
        """각 그룹의 활성화된 feature 수를 계산합니다."""
        feature_counts = {}
        for group_id, group_data in self.group_features.items():
            count = sum(
                1 for value in group_data['features'].values() if value == 1)
            feature_counts[group_id] = count

        return feature_counts

    def build_compatibility_tree(self):
        """호환성 트리를 구축합니다."""
        print("\n호환성 관계 분석 중...")

        compatibility = self.find_compatibility_relationships()
        feature_counts = self.calculate_feature_counts()

        # feature 수에 따라 그룹 정렬 (적은 것부터)
        sorted_groups = sorted(self.group_features.keys(),
                               key=lambda x: feature_counts[x])

        print(f"\n=== CPU Feature 호환성 맵 ===")
        print(f"총 {len(self.group_features)}개 그룹 분석\n")

        # 그룹별 기본 정보 출력
        print("📊 그룹별 정보:")
        for group_id in sorted_groups:
            group_data = self.group_features[group_id]
            feature_count = feature_counts[group_id]
            print(f"  그룹 {group_id:2d}: {group_data['representative']:15} "
                  f"(CPU features: {feature_count:3d}, 인스턴스: {group_data['instance_count']:2d}개)")

        print(f"\n🌳 호환성 트리:")
        print("   ├─ 상위 그룹 (더 많은 CPU feature)")
        print("   └─ 하위 그룹 (더 적은 CPU feature)")
        print("   * 하위 그룹에서 상위 그룹으로 마이그레이션 가능\n")

        # 트리 구조 생성
        self._print_tree_structure(
            sorted_groups, compatibility, feature_counts)

        # 호환성 매트릭스 생성
        self._print_compatibility_matrix(sorted_groups, compatibility)

    def _print_tree_structure(self, sorted_groups: List[int],
                              compatibility: Dict[int, List[int]],
                              feature_counts: Dict[int, int]):
        """트리 구조를 출력합니다."""

        # 부모-자식 관계 구성
        children = defaultdict(list)
        parents = defaultdict(list)

        for group_id in sorted_groups:
            compatible_groups = compatibility[group_id]
            for compatible_group in compatible_groups:
                if feature_counts[group_id] < feature_counts[compatible_group]:
                    children[group_id].append(compatible_group)
                    parents[compatible_group].append(group_id)

        # 루트 노드들 찾기 (부모가 없는 노드)
        roots = [g for g in sorted_groups if not parents[g]]

        # 트리 출력
        printed_groups = set()

        def print_node(group_id: int, prefix: str = "", is_last: bool = True):
            if group_id in printed_groups:
                return

            printed_groups.add(group_id)
            group_data = self.group_features[group_id]
            feature_count = feature_counts[group_id]

            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}그룹 {group_id:2d}: {group_data['representative']:15} "
                  f"[features: {feature_count:3d}, instances: {group_data['instance_count']:2d}]")

            # 자식 노드들 출력
            child_groups = sorted(
                children[group_id], key=lambda x: feature_counts[x])
            for i, child in enumerate(child_groups):
                is_last_child = (i == len(child_groups) - 1)
                next_prefix = prefix + ("    " if is_last else "│   ")
                print_node(child, next_prefix, is_last_child)

        # 루트 노드들부터 출력
        for i, root in enumerate(sorted(roots, key=lambda x: feature_counts[x])):
            is_last_root = (i == len(roots) - 1)
            print_node(root, "", is_last_root)

        # 고립된 노드들 (순환 참조나 복잡한 관계) 출력
        remaining_groups = [
            g for g in sorted_groups if g not in printed_groups]
        if remaining_groups:
            print(f"\n🔄 복잡한 호환성 관계를 가진 그룹들:")
            for group_id in remaining_groups:
                group_data = self.group_features[group_id]
                feature_count = feature_counts[group_id]
                compatible_count = len(compatibility[group_id])
                print(f"   그룹 {group_id:2d}: {group_data['representative']:15} "
                      f"[features: {feature_count:3d}, 호환가능: {compatible_count:2d}개 그룹]")

    def _print_compatibility_matrix(self, sorted_groups: List[int],
                                    compatibility: Dict[int, List[int]]):
        """호환성 매트릭스를 출력합니다."""
        print(f"\n📋 호환성 매트릭스 (행 → 열로 마이그레이션 가능):")
        print(f"   {'':3}", end="")
        for group_id in sorted_groups[:10]:  # 처음 10개 그룹만 표시
            print(f"{group_id:3d}", end="")
        print()

        for i, group1 in enumerate(sorted_groups[:10]):
            print(f"   {group1:2d} ", end="")
            for group2 in sorted_groups[:10]:
                if group1 == group2:
                    print("  -", end="")
                elif group2 in compatibility[group1]:
                    print("  ✓", end="")
                else:
                    print("  ✗", end="")
            print()

    def generate_feature_statistics_csv(self, output_file: str = "feature_statistics.csv"):
        """각 CPU feature를 지원하는 그룹 개수를 통계내어 CSV로 출력합니다."""
        print(f"\n📊 CPU Feature 통계 생성 중...")

        if not self.group_features:
            print("오류: 그룹 feature 데이터가 없습니다.")
            return

        # 모든 feature 목록 수집
        all_features = set()
        for group_data in self.group_features.values():
            all_features.update(group_data['features'].keys())

        all_features = sorted(all_features)

        # 각 feature별로 지원하는 그룹 개수 계산
        feature_counts = {}
        for feature in all_features:
            count = 0
            for group_data in self.group_features.values():
                if group_data['features'].get(feature, 0) == 1:
                    count += 1
            feature_counts[feature] = count

            # CSV 파일 생성 (행렬 변환 - 각 행이 하나의 feature)
        try:
            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)

                # 헤더 작성
                writer.writerow(['Feature', 'Supporting_Groups',
                                'Support_Rate', 'Unsupporting_Groups'])

                # 각 feature별로 데이터 작성
                total_groups = len(self.group_features)
                for feature in all_features:
                    count = feature_counts[feature]
                    support_rate = round((count / total_groups) * 100, 1)
                    unsupported = total_groups - count
                    writer.writerow(
                        [feature, count, support_rate, unsupported])

            print(f"✅ Feature 통계 CSV 파일 생성 완료: {output_file}")
            print(f"   - 총 {len(all_features)}개 feature 정보 저장")
            print(f"   - 엑셀에서 Support_Rate 열로 정렬하여 분석 가능")

        except Exception as e:
            print(f"오류: CSV 파일 생성 실패 - {e}")

    def analyze_feature_distribution(self):
        """Feature 분포를 분석합니다."""
        print(f"\n🔬 Feature 분포 분석:")

        total_groups = len(self.group_features)
        feature_counts = self.calculate_feature_counts()

        # 그룹별 feature 수 분포
        min_features = min(feature_counts.values())
        max_features = max(feature_counts.values())
        avg_features = sum(feature_counts.values()) / len(feature_counts)

        print(f"   최소 feature 수: {min_features}개")
        print(f"   최대 feature 수: {max_features}개")
        print(f"   평균 feature 수: {avg_features:.1f}개")

        # feature 수 구간별 그룹 분포
        ranges = [
            (0, 60, "기본형"),
            (61, 80, "표준형"),
            (81, 110, "고급형"),
            (111, 150, "프리미엄형")
        ]

        print(f"\n📊 그룹별 feature 수 분포:")
        for min_f, max_f, category in ranges:
            count = sum(1 for fc in feature_counts.values()
                        if min_f <= fc <= max_f)
            percentage = (count / total_groups) * 100
            print(
                f"   {category} ({min_f:3d}-{max_f:3d}개): {count:2d}개 그룹 ({percentage:5.1f}%)")


def main():
    if len(sys.argv) != 2:
        print("사용법: python3 compatibility_map.py <groups.json>")
        print("예시: python3 compatibility_map.py groups.json")
        print("      python3 compatibility_map.py groups-no-metal.json")
        sys.exit(1)

    groups_file = sys.argv[1]

    if not os.path.exists(groups_file):
        print(f"오류: {groups_file} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    analyzer = CPUFeatureAnalyzer()

    try:
        # 그룹 정보 로드
        description = analyzer.load_groups(groups_file)
        print(f"분석 대상: {description}")

        # CPU feature 분석
        analyzer.analyze_all_groups()

        # 호환성 트리 구축 및 출력
        analyzer.build_compatibility_tree()

        # Feature 분포 분석
        analyzer.analyze_feature_distribution()

        # Feature 통계 CSV 생성
        csv_filename = f"feature_statistics_{groups_file.replace('.json', '.csv')}"
        analyzer.generate_feature_statistics_csv(csv_filename)

        print(f"\n✅ 호환성 분석이 완료되었습니다!")
        print(f"📁 결과 파일: {groups_file} 기반 분석")
        print(f"📊 통계 파일: {csv_filename}")

    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
