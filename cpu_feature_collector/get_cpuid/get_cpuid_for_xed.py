import os

def process_file(filename, seen_lines):
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or line == '':
                continue
            parts = line.lstrip().split()
            if "n/a" in parts:
                continue
            line = ' '.join(parts).replace(':', '')
            if line not in seen_lines: # 새로운 라인이 seen_lines에 없으면 yield
                seen_lines.add(line) # 새로운 라인을 seen_lines에 추가
                yield line

def write_cpuid_txt(base_dir, output_file):
    seen_lines = set() # 모든 파일에 대한 중복 체크를 위한 set
    with open(output_file, 'w') as out:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file == 'cpuid.xed.txt':
                    for line in process_file(os.path.join(root, file), seen_lines):
                        out.write(line + '\n')

if __name__ == "__main__":
    # xed 레포지토리의 datafiles 디렉토리 경로
    base_dir = "/home/ubuntu/xed/datafiles"
    output_file = "/home/ubuntu/get_cpuid/cpuid.txt"

    write_cpuid_txt(base_dir, output_file)
    print(f"Finished writing to {output_file}")
