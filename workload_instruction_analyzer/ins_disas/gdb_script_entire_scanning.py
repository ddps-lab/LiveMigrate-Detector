import capstone
import gdb

import time
from pathlib import Path
import sys
import os

from tqdm import tqdm

import ctypes

sys.path.append(str(Path(__file__).resolve().parent))

import utils

# xed wrapper 라이브러리 로드
libxedwrapper = ctypes.CDLL('/home/ubuntu/migration_test/ins_disas/xedlib/libxedwrapper.so')

class XedResult(ctypes.Structure):
    _fields_ = [("isa_set", ctypes.c_char_p),
                ("disassembly", ctypes.c_char_p)]


# 함수 프로토타입 정의
libxedwrapper.print_isa_set.argtypes = [ctypes.c_char_p]
libxedwrapper.print_isa_set.restype = XedResult

disassembler = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
disas_file = '/home/ubuntu/migration_test/ins_disas/log/disas.txt'

def get_text_sections():
    files = gdb.execute("info files", to_string=True)

    lines = files.split('\n')

    sections = []

    for line in lines:
        # If line contains ".text" save the section addresses
        # The format is 0x0000564c59c75ae0 - 0x0000564c59f24b9e is .text
        if ".text" in line:
            addresses = line.split()
            sections.append((int(addresses[0], 16), int(addresses[2], 16), ' '.join(addresses[4:])))

    return sections


def disas(start_addr, end_addr, seen, buffered_output, name):
    current_addr = start_addr
    progress = tqdm(total=end_addr-start_addr, desc=f'{name}', unit="B")

    while current_addr <= end_addr:
        try:
            memory_bytes = gdb.selected_inferior().read_memory(current_addr, 15)
        except gdb.MemoryError:
            current_addr += 1
            continue

        instructions = list(disassembler.disasm(bytes(memory_bytes), current_addr))
        if len(instructions) == 0:
            current_addr += 1
            continue

        instruction = instructions[0]
        instruction_hex = ''.join(f'{byte:02x}' for byte in instruction.bytes)
        if instruction_hex not in seen:
            buffered_output.append(f"{hex(instruction.address)}: {instruction.mnemonic} {instruction_hex}\n")
            seen.add(instruction_hex)
            
        current_addr = instruction.address + instruction.size
        progress.update(instruction.size)

    progress.close()

def remove_ins_duplicate():
    # 파일 읽기
    with open(disas_file, 'r') as file:
        lines = file.readlines()

    # 중복된 명령어 제거
    unique_commands = []
    seen_commands = set()

    for line in lines:
        line = line.strip()
        command = line.split(': ')[-1].split(' ')[0]  # 라인에서 명령어 부분 추출
        if command not in seen_commands:
            unique_commands.append(line)
            seen_commands.add(command)

    # 결과 파일로 저장 또는 출력
    with open(disas_file, 'w') as output_file:
        for line in unique_commands:
            output_file.write(line + '\n')

def preprocessing():
    workload_data_list = []
    with open(disas_file, 'r') as f:
        lines = f.readlines()
        for line in tqdm(lines, desc='Processing lines', file=sys.stdout):
            parts = line.split(' ')

            binary_value = parts[-1].strip()
            instruction_data = {}

            result = libxedwrapper.print_isa_set(binary_value.encode())

            instruction_data['ISA_SET'] = result.isa_set.decode('utf-8') if result.isa_set else "Error"
            instruction_data['SHORT'] = result.disassembly.decode('utf-8') if result.disassembly else "Error"

            workload_data_list.append(instruction_data)

    utils.create_csv(workload_data_list)

if __name__ == '__main__':
    # 스크립트 시작 시간 기록
    script_start_time = time.time()

    gdb.execute(f"set pagination off")

    # 쉘 스크립트에서 전달된 GDB 시작 시간 가져오기
    gdb_start_time = float(os.getenv('GDB_START_TIME', '0'))
    # GDB 실행에 걸린 시간 계산
    gdb_load_time = script_start_time - gdb_start_time
    print("GDB uptime : {:.3} s".format(gdb_load_time))

    temp_time = time.time()
    sections = get_text_sections()
    end_time = time.time()
    total_time = end_time - temp_time
    print("get text sections: {:.3f} s".format(total_time))
    
    temp_time = time.time()
    seen = set()
    buffered_output = []
    for start_addr, end_addr, name in sections:
        disas(start_addr, end_addr, seen, buffered_output, name)
    
    with open(disas_file, 'w') as f:
        f.write(''.join(buffered_output))
    end_time = time.time()
    total_time = end_time - temp_time
    remove_ins_duplicate()
    print("entire disassemble: {:.3f} s".format(total_time))
    
    temp_time = time.time()
    preprocessing()
    end_time = time.time()
    total_time = end_time - temp_time
    print("instruction interpretation: {:.3f} s".format(total_time))

    end_time = time.time()
    total_time = end_time - gdb_start_time
    print("total: {:.3f} s".format(total_time))

    exit()