import os

def process_file(filename):
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or line == '':
                continue
            parts = line.lstrip().split()
            if "n/a" in parts:
                continue
            line = ' '.join(parts).replace(':', '')
            yield line

def write_cpuid_txt(base_dir, output_file):
    with open(output_file, 'w') as out:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file == 'cpuid.xed.txt':
                    for line in process_file(os.path.join(root, file)):
                        out.write(line + '\n')

if __name__ == "__main__":
    # xed 레포지토리의 datafiles 디렉토리 경로
    base_dir = "/home/ubuntu/xed/datafiles"
    output_file = "/home/ubuntu/get_cpuid/cpuid.txt"

    write_cpuid_txt(base_dir, output_file)
    print(f"Finished writing to {output_file}")