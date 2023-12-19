import gdb
import capstone

import subprocess
import sys

import csv
import glob

def GetPath():
    for filename in glob.glob('/home/ubuntu/migration_test/*_to_*.csv'):
        path = filename
        return path

def get_instances():
    with open('/home/ubuntu/migration_test/performance.log', 'r') as file:
        src = file.readline().strip()  # 첫 번째 줄 읽기
        dst = file.readline().strip()  # 두 번째 줄 읽기

        src = src.split(':')
        dst = dst.split(':')

        src = src[1].strip()
        dst = dst[1].strip()
    
    return src, dst

def get_instruction_pointer():
    global err_message

    command = 'sudo dmesg | grep \'invalid opcode\' | awk -F\'ip:\' \'{print $2}\' | awk \'{print $1}\''
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if len(result.stdout) == 0:
        err_message = 'invalid opcode error is not in dmesg.'
        return 0

    hex_string = result.stdout.strip()
    # 16진수로 변환
    instruction_pointer = int(hex_string, 16)

    return instruction_pointer

def get_instruction_binary(instruction_pointer):
    global err_message

    # x86-64용 디스어셈블러 생성
    disassembler = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

    # 최대 명령어 길이인 15 바이트 읽기
    try:
        memory_bytes = gdb.selected_inferior().read_memory(instruction_pointer, 15)
    except gdb.MemoryError as e:
        err_message = "Failed to read memory:" + str(e)
        return 0

    # 바이트를 디스어셈블
    instructions = list(disassembler.disasm(bytes(memory_bytes), instruction_pointer))

    # 첫 번째 명령어 가져오기
    first_instruction = instructions[0]

    instruction_byte = first_instruction.bytes
    instruction_binary = ''.join(f'{byte:02x}' for byte in instruction_byte)

    return instruction_binary

def get_instruction_info(instruction_binary):
    xed_path = "/home/ubuntu/.guix-profile/bin/xed"
    command = f"{xed_path} -64 -d {instruction_binary}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    return result

def create_csv(path, result, args):
    src, dst, instruction_pointer, instruction_binary = args
    result_dict = {}

    if isinstance(result, subprocess.CompletedProcess):
        # 줄별로 나누기
        lines = result.stdout.strip().split("\n")

        # 각 줄을 파싱하여 딕셔너리에 저장
        for line in lines:
            if ": " in line:
                key, value = line.split(": ", 1)
                result_dict[key] = value

    # CSV 파일로 저장
    with open(path, 'w', newline='') as file:
        writer = csv.writer(file)
        
        # 헤더 작성
        writer.writerow(['SOURCE', 'DESTINATION', 'INSTRUCTION_POINTER', 'INSTRUCTION_BINARY', 'ICLASS', 'CATEGORY', 'EXTENSION', 'IFORM', 'ISA_SET', 'ATTRIBUTES', 'SHORT', 'ERROR'])
        
        # 값 작성
        writer.writerow([
            src,
            dst,
            f"0x{instruction_pointer:x}",
            instruction_binary,
            result_dict.get("ICLASS", "N/A"),
            result_dict.get("CATEGORY", "N/A"),
            result_dict.get("EXTENSION", "N/A"),
            result_dict.get("IFORM", "N/A"),
            result_dict.get("ISA_SET", "N/A"),
            result_dict.get("ATTRIBUTES", "N/A"),
            result_dict.get("SHORT", "N/A"),
            err_message
        ])

if __name__ == '__main__':
    path = GetPath()
    path = path[:-4]
    path = path + '-debug.csv'

    err_message = 'N/A'
    instruction_binary = 0
    result = ''
    
    src, dst = get_instances()
    instruction_pointer = get_instruction_pointer()

    if instruction_pointer != 0:
        instruction_binary = get_instruction_binary(instruction_pointer)

    if instruction_binary != 0:
        result = get_instruction_info(instruction_binary)

    args = [src, dst, instruction_pointer, instruction_binary]

    create_csv(path, result, args)

    # GDB 종료
    gdb.execute("quit\ny")
