import gdb

from pathlib import Path
import sys
import os

import ctypes

rootdir = str(Path(__file__).resolve().parent)
sys.path.append(rootdir)

import utils

import bytecode_tracking.btracking

glibc_rtm_enable = False
LD_BIND_NOW = False
xtest_enable = False
is_tsx_run = False

# xed wrapper 라이브러리 로드
libxedwrapper = ctypes.CDLL(f'{rootdir}/xedlib/libxedwrapper.so')

class XedResult(ctypes.Structure):
    _fields_ = [("isa_set", ctypes.c_char_p),
                ("disassembly", ctypes.c_char_p)]


# 함수 프로토타입 정의
libxedwrapper.print_isa_set.argtypes = [ctypes.c_char_p]
libxedwrapper.print_isa_set.restype = XedResult

def get_got_sections():
    files = gdb.execute("info files", to_string=True)

    lines = files.split('\n')

    got_addr = []

    for line in lines:
        # The format is 0x0000564c59c75ae0 - 0x0000564c59f24b9e is .text
        if ' is ' not in line:
            continue

        if '.got' == line.split('is ')[1]:
            addresses = line.split()
            got_addr.append(int(addresses[0], 16))
            got_addr.append(int(addresses[2], 16))

    return got_addr

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

# glibc는 항상 TSX를 지원하도록 컴파일되지만 TSX는 애플리케이션을 실행하기 전에(예: 를 실행하여 ) 환경 변수가 glibc.elision.enable1로 설정된 경우에만 사용됨.
# TSX를 사용하도록 환경변수가 설정되지 않았다면 glibc의 내부 함수에서 TSX를 사용하는 __GI___lll_lock_elision, __GI___lll_unlock_elision 를 트래킹에서 제외함.
def glibc_tunables_check():
    global glibc_rtm_enable

    with open(f"/proc/{PID}/environ", 'rb') as file:
        # 파일을 바이너리 모드로 읽고, null 문자를 개행 문자로 대체한 후 디코딩합니다.
        env_data = file.read().replace(b'\0', b'\n').decode('utf-8')

        if 'glibc.elision.enable=1' in env_data:
            glibc_rtm_enable = True

def binding_check(PID):
    global LD_BIND_NOW

    with open(f"/proc/{PID}/environ", 'rb') as file:
        # 파일을 바이너리 모드로 읽고, null 문자를 개행 문자로 대체한 후 디코딩합니다.
        env_data = file.read().replace(b'\0', b'\n').decode('utf-8')

        if 'LD_BIND_NOW=1' in env_data:
            LD_BIND_NOW = True

def dis_func(addr, tracked_instructions):
    global xtest_enable
    global is_tsx_run

    global logging_functions

    global compile_indirect
    global runtime_indirect
    global call_regi
    
    tsx_enabled_glibc_functions = ['__GI___lll_lock_elision', '__GI___lll_unlock_elision']

    func = {}

    transfer_instructions = set(('call', 'jmp', 'ja', 'jnbe', 'jae', 'jnb', 'jb', 'jnae', 'jbe', 'jna', 'jc', 'je', 'jz', 'jnc', 'jne', 'jnz', 
    'jnp', 'jpo', 'jp', 'jpe', 'jcxz', 'jecxz', 'jg', 'jnle', 'jge', 'jnl', 'jl', 'jnge', 'jle', 'jng', 'jno', 'jns', 'jo', 'js'))

    special_instruction = transfer_instructions.copy()
    special_instruction.add('lea')

    try:
        disas_result = gdb.execute(f"disas /r {addr}", to_string=True)
    except gdb.error as e:
        print(f'error: {addr}')
        return None

    lines = disas_result.split('\n')

    for line in lines:
        if 'Dump of assembler code for function' in line:
            func_name = line.split('function ')[1].split(':')[0]
            logging_functions.append(func_name)

        # tsx를 사용하는 glibc 내부 함수에 대해 처리
        if func_name in tsx_enabled_glibc_functions:
            if glibc_rtm_enable:
                pass
            else:
                return None

        # ex) ["0x0000561161740078 <_start+24>", "48 8d 3d bb 02 00 00	lea    rdi,[rip+0x2bb]        # 0x56116174033a <main>"]
        parts = line.strip().split(":")
        parts = list(filter(None, parts))

        # If there's no instruction part, skip this line
        if len(parts) < 2:
            continue        

        # ex) "48 8d 3d bb 02 00 00	lea    rdi,[rip+0x2bb]        # 0x56116174033a <main>"
        instruction_part = parts[1].strip()
        instruction_hex = instruction_part.split('\t')[0].replace(' ', '')
        instruction = instruction_part.split('\t')[1].split(' ')[0]

        if instruction in special_instruction:
            pass
        elif instruction in tracked_instructions:
            continue
        else:
            tracked_instructions.add(instruction)        

        gdb_comment = instruction_part.split(' ')[-1]

        # exclude cold functions
        if '-' in gdb_comment or '.cold' in gdb_comment:
            continue

        if 'call' in instruction_part and 'QWORD PTR' in line:
            if not '#' in line:
                if '+' in instruction_part:
                    compile_indirect.append(line)
                else:
                    runtime_indirect.append(line)

        # ex) "0x0000561161740078 <_start+24>"
        addresse_part = parts[0].strip()
        # ex) ["0x0000561161740078", "<_start+24>"]
        addresse_part = addresse_part.split(' ')
        # ex) "0x0000561161740078"
        address = addresse_part[0]
        offset = addresse_part[1]

        # instruction not within function
        if len(addresse_part) < 2:
            continue

        # exclude cold functions
        if '-' in offset or '.cold' in offset:
            continue

        is_func_call = None
        if instruction in transfer_instructions:
            # 레지스터 콜 제외..
            if gdb_comment.startswith('<'):
                if '@plt' in gdb_comment:
                    is_func_call = 'plt'
                elif '+' in gdb_comment:
                    pass
                else:
                    is_func_call = 'func'
            elif gdb_comment.startswith('0x'):
                abs_addr = int(gdb_comment, 16)
                if got_addr[0] <= abs_addr <= got_addr[1]:
                    is_func_call = 'got'
            # FIXME
            else:
                call_regi.append(line)
        
        if instruction == 'lea':
            if gdb_comment.startswith('<'):
                if '+' in gdb_comment:
                    pass
                else:
                    is_func_call = 'lea'
                    # 코멘트의 주소를 활용해 주소를 찾는 중복 작업을 제거
                    gdb_comment = instruction_part.split('#')[1].strip()

        if instruction == 'xtest':
            xtest_enable = True
        elif instruction in ['xbegin', 'xend']:
            is_tsx_run = True

        func[instruction_hex] = address, is_func_call, gdb_comment
    return func

def address_calculation(instruction_data, instruction_addr, is_func_call, gdb_comment, tracking_functions):
    global LD_BIND_NOW

    instruction_addr = ctypes.c_int64(int(instruction_addr, 16)).value

    if is_func_call == 'got':
        address = gdb.execute(f'x/g {gdb_comment}', to_string=True).split(':')[-1].strip()
    else:
        # Calculate Call Address
        address = instruction_data["SHORT"].split(' ')
        address = list(filter(None, address))

        if is_func_call != 'lea':
            try:
                # print(is_func_call, hex(instruction_addr), instruction_data["SHORT"], gdb_comment)
                address = int(instruction_data["SHORT"].split(' ')[-1], 16)
                address = address + instruction_addr
                address = hex(address & 0xFFFFFFFFFFFFFFFF)  # 결과를 64비트로 자르기
                address = "0x{:016x}".format(int(address, 16))
            # QWORD PTR [rip+0x2f53] 처럼 call 하는 주소를 계산할 수 없는 경우
            except:
                symbol = gdb_comment.replace('<', '')
                symbol = symbol.replace('>', '')
                address = gdb.execute(f'info address {symbol}', to_string=True).split(' ')[-1].split('.')[0]
        elif is_func_call == 'lea':
            address = gdb_comment.split(' ')[0].strip()
            address = "0x{:016x}".format(int(address, 16))

    # if address is not function start address 
    if is_func_call == 'plt':
        if LD_BIND_NOW:
            plt_addr = gdb.execute(f'disas {address}', to_string=True).split('#')[-1].strip()
            plt_addr = plt_addr.split(' ')[0].strip()
            # address = gdb.execute(f'x/g {plt_addr}', to_string=True).split(':')[-1].strip()
            address = gdb.execute(f'x/g {plt_addr}', to_string=True).split(':')[-1].strip().split(' ')[0]
        else:
            # 트래킹 불가
            if '*ABS*' in gdb_comment:
                return None
            symbol = gdb_comment.split('@')[0].split('<')[1]
            address = gdb.execute(f'info address {symbol}', to_string=True).split(' ')
            # '0x'로 시작하는 항목을 찾습니다.
            address = [part for part in address if part.startswith('0x')]
            address = ''.join(address)

    if address not in tracking_functions:
        return address
    else:
        return None

def tracking(LANGUAGE_TYPE, SCRIPT_PATH):
    executable_instructions = []
    tracking_functions = set()
    list_tracking_functions = []

    tracked_instructions = set()

    if LANGUAGE_TYPE == 'python':
        tracking_functions = bytecode_tracking.btracking.main(SCRIPT_PATH)
        list_tracking_functions = list(tracking_functions)

    # search the starting point of tracking
    # start_addr = gdb.execute(f"p/x (long) main", to_string=True).split(' ')[-1]
    start_addr = gdb.execute(f"p/x (long) _start", to_string=True).split(' ')[-1]
    start_addr = "0x{:016x}".format(int(start_addr, 16))

    tracking_functions.add(start_addr)
    list_tracking_functions.append(start_addr)

    for function_address in list_tracking_functions:
        func = dis_func(function_address, tracked_instructions)

        if func is None:
            continue

        for instruction_hex, instruction_meta in func.items():
            instruction_addr = instruction_meta[0]
            is_func_call = instruction_meta[1]
            gdb_comment = instruction_meta[2]

            instruction_data = {}

            result = libxedwrapper.print_isa_set(instruction_hex.encode())

            instruction_data['ISA_SET'] = result.isa_set.decode('utf-8') if result.isa_set else "Error"
            instruction_data['SHORT'] = result.disassembly.decode('utf-8') if result.disassembly else "Error"

            executable_instructions.append(instruction_data)

            # Calculate the target address in case of a transfer instruction
            if is_func_call:
                dst_addr = address_calculation(instruction_data, instruction_addr, is_func_call, gdb_comment, tracking_functions)

                if dst_addr: 
                    tracking_functions.add(dst_addr)
                    list_tracking_functions.append(dst_addr)
            
    print(f'tracked function count: {len(tracking_functions)}')
    utils.create_csv(executable_instructions, is_tsx_run, xtest_enable)

if __name__ == '__main__':
    logging_functions = []
    gdb.execute(f"set pagination off")
    
    # 쉘 스크립트에서 전달된 workload PID 가져오기
    PID = int(os.getenv('WORKLOAD_PID', '0'))
    LANGUAGE_TYPE = os.getenv('LANGUAGE_TYPE', '0')
    SCRIPT_PATH = os.getenv('SCRIPT_PATH', '0')

    glibc_tunables_check()
    binding_check(PID)
    
    got_addr = get_got_sections()
    sections = get_text_sections()

    compile_indirect = []
    runtime_indirect = []
    call_regi = []

    tracking(LANGUAGE_TYPE, SCRIPT_PATH)

    with open('tracked_functions.txt', 'w') as f:
        f.write('\n'.join(logging_functions))   
    with open('compile_indirect.txt', 'w') as f:
        f.write('\n'.join(compile_indirect))   
    with open('runtime_indirect.txt', 'w') as f:
        f.write('\n'.join(runtime_indirect))   
    with open('call_regi.txt', 'w') as f:
        f.write('\n'.join(call_regi))           