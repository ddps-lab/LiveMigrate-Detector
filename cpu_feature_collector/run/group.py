#!/usr/bin/env python3
import os
import csv
import json
from collections import defaultdict


def sort_instance_name(instance_name):
    """인스턴스 이름을 올바른 순서로 정렬하기 위한 키 함수"""
    # instance_type.instance_size 형태를 분리
    if '.' in instance_name:
        instance_type, instance_size = instance_name.split('.', 1)
        # 사이즈는 길이 순으로, 같은 길이면 알파벳 순으로
        return (instance_type, len(instance_size), instance_size)
    else:
        # .이 없는 경우는 그냥 원본 이름으로
        return (instance_name, 0, "")


def read_csv_content(file_path):
    """CSV 파일의 내용을 읽어서 데이터 행만 반환합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        if len(rows) >= 2:
            # 헤더는 무시하고 데이터 행만 반환
            return tuple(rows[1])  # tuple로 변환하여 hashable하게 만듦
        return None


def create_groups_from_content_groups(content_groups, output_filename, description):
    """내용 그룹에서 JSON 파일을 생성합니다."""
    # 그룹을 리스트 형태로 변환
    groups = []
    for i, (content, instances) in enumerate(content_groups.items()):
        group = {
            "group_id": i + 1,
            # 개선된 정렬 방식 사용
            "instances": sorted(instances, key=sort_instance_name),
            "count": len(instances)
        }
        groups.append(group)

    # 그룹을 인스턴스 개수 순으로 정렬 (많은 것부터)
    groups.sort(key=lambda x: x["count"], reverse=True)

    # 그룹 ID 재할당
    for i, group in enumerate(groups):
        group["group_id"] = i + 1

    # 결과를 JSON 파일로 저장
    output_data = {
        "description": description,
        "total_groups": len(groups),
        "total_instances": sum(group["count"] for group in groups),
        "groups": groups
    }

    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # 결과 출력
    print(f"\n=== {description} ===")
    print(f"총 그룹 수: {len(groups)}")
    print(f"총 인스턴스 수: {sum(group['count'] for group in groups)}")
    print(f"\n각 그룹별 인스턴스 개수:")

    for group in groups:
        print(f"그룹 {group['group_id']}: {group['count']}개 인스턴스")
        print(f"  인스턴스: {', '.join(group['instances'][:5])}")  # 처음 5개만 출력
        if len(group['instances']) > 5:
            print(f"  ... 외 {len(group['instances']) - 5}개")
        print()

    print(f"결과가 {output_filename} 파일에 저장되었습니다.")


def group_csv_files():
    """result 디렉토리의 모든 CSV 파일을 읽어서 내용별로 그룹화합니다."""
    result_dir = "result"

    if not os.path.exists(result_dir):
        print(f"Error: {result_dir} directory not found")
        return

    # 내용별로 파일들을 그룹화 (전체)
    content_groups_all = defaultdict(list)
    # 내용별로 파일들을 그룹화 (metal 제외)
    content_groups_no_metal = defaultdict(list)

    # 모든 CSV 파일 처리
    csv_files = [f for f in os.listdir(result_dir) if f.endswith('.csv')]

    print(f"Processing {len(csv_files)} CSV files...")

    metal_instances = []
    non_metal_instances = []

    for filename in csv_files:
        file_path = os.path.join(result_dir, filename)
        content = read_csv_content(file_path)

        if content is not None:
            # 파일명에서 .csv 확장자 제거
            instance_name = filename[:-4]

            # 전체 그룹에 추가
            content_groups_all[content].append(instance_name)

            # .metal이 포함되지 않은 경우에만 no-metal 그룹에 추가
            if ".metal" not in instance_name:
                content_groups_no_metal[content].append(instance_name)
                non_metal_instances.append(instance_name)
            else:
                metal_instances.append(instance_name)

            print(f"Processed: {instance_name}")
        else:
            print(f"Warning: Could not read content from {filename}")

    print(f"\nTotal instances: {len(csv_files)}")
    print(f"Metal instances: {len(metal_instances)}")
    print(f"Non-metal instances: {len(non_metal_instances)}")
    print(f"Metal instances: {', '.join(sorted(metal_instances))}")

    # 전체 결과 저장
    create_groups_from_content_groups(
        content_groups_all,
        "groups.json",
        "모든 인스턴스 그룹화 결과"
    )

    # metal 제외 결과 저장
    create_groups_from_content_groups(
        content_groups_no_metal,
        "groups-no-metal.json",
        "Metal 인스턴스 제외 그룹화 결과"
    )


if __name__ == "__main__":
    group_csv_files()
