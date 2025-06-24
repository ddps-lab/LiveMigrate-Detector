import psutil
import threading
import bytecode_tracking.btracking
import utils
import gdb

from pathlib import Path
import sys
import os

import ctypes
import time

print("=== DEBUG: Starting gdb_script_exepath_tracking.py ===")
print(f"=== DEBUG: Python version: {sys.version} ===")
print(f"=== DEBUG: Current working directory: {os.getcwd()} ===")

rootdir = str(Path(__file__).resolve().parent)
sys.path.append(rootdir)
print(f"=== DEBUG: Root directory: {rootdir} ===")
print(f"=== DEBUG: Python path: {sys.path} ===")

glibc_rtm_enable = False
LD_BIND_NOW = False
xtest_enable = False
is_tsx_run = False

print("=== DEBUG: Loading XED wrapper library ===")
# xed wrapper 라이브러리 로드
try:
    libxedwrapper = ctypes.CDLL(f'{rootdir}/xedlib/libxedwrapper.so')
    print(
        f"=== DEBUG: XED library loaded successfully from {rootdir}/xedlib/libxedwrapper.so ===")
except Exception as e:
    print(f"=== ERROR: Failed to load XED library: {e} ===")
    sys.exit(1)


class XedResult(ctypes.Structure):
    _fields_ = [("isa_set", ctypes.c_char_p),
                ("disassembly", ctypes.c_char_p)]


# 함수 프로토타입 정의
libxedwrapper.print_isa_set.argtypes = [ctypes.c_char_p]
libxedwrapper.print_isa_set.restype = XedResult
print("=== DEBUG: XED function prototypes defined ===")

tracked_func_count = 0
dis_time = 0
tracking_time = 0
btracking_time = 0
addr_collect_time = 0
module_count = 0

start_memory = 0
max_memory = 0
monitoring = False


def get_got_sections():
    print("=== DEBUG: Getting GOT sections ===")
    try:
        files = gdb.execute("info files", to_string=True)
        print(f"=== DEBUG: GDB info files output length: {len(files)} ===")
    except Exception as e:
        print(f"=== ERROR: Failed to get file info from GDB: {e} ===")
        return []

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
            print(
                f"=== DEBUG: Found GOT section: {addresses[0]} - {addresses[2]} ===")

    print(f"=== DEBUG: Total GOT sections found: {len(got_addr)//2} ===")
    return got_addr


def get_text_sections():
    print("=== DEBUG: Getting text sections ===")
    try:
        files = gdb.execute("info files", to_string=True)
        print(f"=== DEBUG: GDB info files output length: {len(files)} ===")
    except Exception as e:
        print(f"=== ERROR: Failed to get file info from GDB: {e} ===")
        return []

    lines = files.split('\n')
    sections = []

    for line in lines:
        # If line contains ".text" save the section addresses
        # The format is 0x0000564c59c75ae0 - 0x0000564c59f24b9e is .text
        if ".text" in line:
            addresses = line.split()
            sections.append((int(addresses[0], 16), int(
                addresses[2], 16), ' '.join(addresses[4:])))
            print(
                f"=== DEBUG: Found text section: {addresses[0]} - {addresses[2]} in {' '.join(addresses[4:])} ===")

    print(f"=== DEBUG: Total text sections found: {len(sections)} ===")
    return sections


def glibc_tunables_check():
    global glibc_rtm_enable
    print("=== DEBUG: Checking glibc tunables ===")

    try:
        with open(f"/proc/{PID}/environ", 'rb') as file:
            # 파일을 바이너리 모드로 읽고, null 문자를 개행 문자로 대체한 후 디코딩합니다.
            env_data = file.read().replace(b'\0', b'\n').decode('utf-8')

            if 'glibc.elision.enable=1' in env_data:
                glibc_rtm_enable = True
                print("=== DEBUG: glibc RTM enabled ===")
            else:
                print("=== DEBUG: glibc RTM not enabled ===")
    except Exception as e:
        print(f"=== ERROR: Failed to check glibc tunables: {e} ===")


def binding_check(PID):
    global LD_BIND_NOW
    print("=== DEBUG: Checking binding ===")

    try:
        with open(f"/proc/{PID}/environ", 'rb') as file:
            # 파일을 바이너리 모드로 읽고, null 문자를 개행 문자로 대체한 후 디코딩합니다.
            env_data = file.read().replace(b'\0', b'\n').decode('utf-8')

            if 'LD_BIND_NOW=1' in env_data:
                LD_BIND_NOW = True
                print("=== DEBUG: LD_BIND_NOW enabled ===")
            else:
                print("=== DEBUG: LD_BIND_NOW not enabled ===")
    except Exception as e:
        print(f"=== ERROR: Failed to check binding: {e} ===")


def dis_func(addr, tracked_instructions):
    global xtest_enable
    global is_tsx_run
    global logging_functions
    global compile_indirect
    global runtime_indirect
    global call_regi

    print(f"=== DEBUG: Disassembling function at address: {addr} ===")

    tsx_enabled_glibc_functions = [
        '__GI___lll_lock_elision', '__GI___lll_unlock_elision']

    func = {}

    transfer_instructions = set(('call', 'jmp', 'ja', 'jnbe', 'jae', 'jnb', 'jb', 'jnae', 'jbe', 'jna', 'jc', 'je', 'jz', 'jnc', 'jne', 'jnz',
                                 'jnp', 'jpo', 'jp', 'jpe', 'jcxz', 'jecxz', 'jg', 'jnle', 'jge', 'jnl', 'jl', 'jnge', 'jle', 'jng', 'jno', 'jns', 'jo', 'js'))

    special_instruction = transfer_instructions.copy()
    special_instruction.add('lea')

    try:
        start_time = time.time()
        disas_result = gdb.execute(f"disas /r {addr}", to_string=True)
        end_time = time.time()
        global dis_time
        dis_time += end_time - start_time
        print(
            f"=== DEBUG: Disassembly completed for {addr}, took {end_time - start_time:.6f}s ===")
    except gdb.error as e:
        print(f"=== ERROR: Failed to disassemble {addr}: {e} ===")
        return None

    lines = disas_result.split('\n')
    instruction_count = 0

    for line in lines:
        if 'Dump of assembler code for function' in line:
            func_name = line.split('function ')[1].split(':')[0]
            logging_functions.append(func_name)
            print(f"=== DEBUG: Processing function: {func_name} ===")

        # tsx를 사용하는 glibc 내부 함수에 대해 처리
        if func_name in tsx_enabled_glibc_functions:
            if glibc_rtm_enable:
                print(
                    f"=== DEBUG: TSX function {func_name} allowed (RTM enabled) ===")
                pass
            else:
                print(
                    f"=== DEBUG: TSX function {func_name} skipped (RTM disabled) ===")
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

        if instruction == 'xtest':
            xtest_enable = True
            print("=== DEBUG: xtest instruction found ===")
        elif instruction in ['xbegin', 'xend']:
            is_tsx_run = True
            print(f"=== DEBUG: TSX instruction found: {instruction} ===")

        func[instruction_hex] = address, is_func_call, gdb_comment
        instruction_count += 1

    print(
        f"=== DEBUG: Processed {instruction_count} instructions for function at {addr} ===")
    return func


def address_calculation(instruction_data, instruction_addr, is_func_call, gdb_comment, tracking_functions):
    print(
        f"=== DEBUG: Calculating address for instruction at {instruction_addr} ===")

    def check_address_in_range(address):
        for start, end, _ in sections:
            if start <= int(address, 16) <= end:
                return True
        return False

    global LD_BIND_NOW

    instruction_addr = ctypes.c_int64(int(instruction_addr, 16)).value

    if is_func_call == 'got':
        try:
            address = gdb.execute(f'x/g {gdb_comment}',
                                  to_string=True).split(':')[-1].strip()
            print(f"=== DEBUG: GOT address resolved: {address} ===")
        except Exception as e:
            print(f"=== ERROR: Failed to resolve GOT address: {e} ===")
            return None
    else:
        # Calculate Call Address
        address = instruction_data["SHORT"].split(' ')
        address = list(filter(None, address))

        if is_func_call != 'lea':
            try:
                address = int(instruction_data["SHORT"].split(' ')[-1], 16)
                address = address + instruction_addr
                address = hex(address & 0xFFFFFFFFFFFFFFFF)  # 결과를 64비트로 자르기
                address = "0x{:016x}".format(int(address, 16))
                print(f"=== DEBUG: Calculated call address: {address} ===")
            # QWORD PTR [rip+0x2f53] 처럼 call 하는 주소를 계산할 수 없는 경우
            except Exception as e:
                print(
                    f"=== DEBUG: Cannot calculate address, using symbol: {gdb_comment} ===")
                symbol = gdb_comment.replace('<', '')
                symbol = symbol.replace('>', '')
                try:
                    address = gdb.execute(f'info address {symbol}', to_string=True).split(
                        ' ')[-1].split('.')[0]
                    print(f"=== DEBUG: Symbol address resolved: {address} ===")
                except Exception as e:
                    print(
                        f"=== ERROR: Failed to resolve symbol address: {e} ===")
                    return None
        elif is_func_call == 'lea':
            address = gdb_comment.split(' ')[0].strip()
            address = "0x{:016x}".format(int(address, 16))
            # lea로 할당된 주소가 .text 섹션이 아닌 경우
            if not check_address_in_range(address):
                print(
                    f"=== DEBUG: LEA address {address} not in text section ===")
                return None

    # if address is not function start address
    if is_func_call == 'plt':
        if LD_BIND_NOW:
            try:
                plt_addr = gdb.execute(
                    f'disas {address}', to_string=True).split('#')[-1].strip()
                plt_addr = plt_addr.split(' ')[0].strip()
                address = gdb.execute(
                    f'x/g {plt_addr}', to_string=True).split(':')[-1].strip().split(' ')[0]
                print(
                    f"=== DEBUG: PLT address resolved (LD_BIND_NOW): {address} ===")
            except Exception as e:
                print(f"=== ERROR: Failed to resolve PLT address: {e} ===")
                return None
        else:
            # 트래킹 불가
            if '*ABS*' in gdb_comment:
                print("=== DEBUG: PLT address not trackable (*ABS*) ===")
                return None
            symbol = gdb_comment.split('@')[0].split('<')[1]
            try:
                address = gdb.execute(
                    f'info address {symbol}', to_string=True).split(' ')
                # '0x'로 시작하는 항목을 찾습니다.
                address = [part for part in address if part.startswith('0x')]
                address = ''.join(address)
                print(f"=== DEBUG: PLT symbol address resolved: {address} ===")
            except Exception as e:
                print(f"=== ERROR: Failed to resolve PLT symbol: {e} ===")
                return None

    if address not in tracking_functions:
        print(f"=== DEBUG: New function address to track: {address} ===")
        return address
    else:
        print(f"=== DEBUG: Function address already tracked: {address} ===")
        return None


process = psutil.Process(os.getpid())


def monitor_memory_usage():
    global max_memory, monitoring
    while monitoring:
        current_memory = process.memory_info().rss
        max_memory = max(max_memory, current_memory)
        time.sleep(0.01)  # 10ms 간격으로 체크


def record_memory_start():
    global start_memory, monitoring
    start_memory = process.memory_info().rss
    monitoring = True
    print(
        f"=== DEBUG: Memory monitoring started, initial: {start_memory / 1024 / 1024:.2f} MB ===")
    # 별도의 스레드로 메모리 모니터링 시작
    thread = threading.Thread(target=monitor_memory_usage)
    thread.start()


def record_memory_end():
    global monitoring
    monitoring = False
    memory_diff = max_memory - start_memory
    print(
        f"=== DEBUG: Memory monitoring ended, peak: {max_memory / 1024 / 1024:.2f} MB, diff: {memory_diff / 1024 / 1024:.2f} MB ===")
    return memory_diff / 1024 / 1024


def calculate_list_memory_size(lst):
    total_size = sys.getsizeof(lst)  # 리스트 객체 자체의 크기
    for item in lst:
        total_size += sys.getsizeof(item)  # 리스트 내부 각 요소의 크기 합산
    return total_size


def tracking(LANGUAGE_TYPE, SCRIPT_PATH):
    print(
        f"=== DEBUG: Starting tracking for {LANGUAGE_TYPE} script: {SCRIPT_PATH} ===")
    start_time = time.time()

    executable_instructions = []
    tracking_functions = set()
    list_tracking_functions = []

    tracked_instructions = set()

    global addr_collect_time
    global btracking_time
    global module_count

    btracking_start_time = 0
    btracking_end_time = 0

    if LANGUAGE_TYPE == 'python':
        print("=== DEBUG: Starting Python bytecode tracking ===")
        record_memory_start()
        btracking_start_time = time.time()
        try:
            tracking_functions, addr_collect_time, module_count = bytecode_tracking.btracking.main(
                SCRIPT_PATH)
            list_tracking_functions = list(tracking_functions)
            btracking_end_time = time.time()
            btracking_time = btracking_end_time - btracking_start_time - addr_collect_time
            print(
                f'=== DEBUG: Btracking completed, functions found: {len(tracking_functions)} ===')
            print(
                f'=== DEBUG: Btracking 추가된 메모리 사용량: {record_memory_end()} MB ===')
        except Exception as e:
            print(f"=== ERROR: Bytecode tracking failed: {e} ===")
            import traceback
            traceback.print_exc()
            return

    record_memory_start()
    # search the starting point of tracking
    try:
        start_addr = gdb.execute(
            f"p/x (long) main", to_string=True).split(' ')[-1]
        # start_addr = gdb.execute(f"p/x (long) _start", to_string=True).split(' ')[-1]
        start_addr = "0x{:016x}".format(int(start_addr, 16))
        print(f"=== DEBUG: Main function address: {start_addr} ===")
    except Exception as e:
        print(f"=== ERROR: Failed to get main function address: {e} ===")
        return

    tracking_functions.add(start_addr)
    list_tracking_functions.append(start_addr)

    processed_functions = 0
    for function_address in list_tracking_functions:
        processed_functions += 1
        if processed_functions % 100 == 0:
            print(
                f"=== DEBUG: Processed {processed_functions}/{len(list_tracking_functions)} functions ===")

        func = dis_func(function_address, tracked_instructions)

        if func is None:
            continue

        for instruction_hex, instruction_meta in func.items():
            instruction_addr = instruction_meta[0]
            is_func_call = instruction_meta[1]
            gdb_comment = instruction_meta[2]

            instruction_data = {}

            try:
                result = libxedwrapper.print_isa_set(instruction_hex.encode())

                instruction_data['ISA_SET'] = result.isa_set.decode(
                    'utf-8') if result.isa_set else "Error"
                instruction_data['SHORT'] = result.disassembly.decode(
                    'utf-8') if result.disassembly else "Error"
            except Exception as e:
                print(
                    f"=== ERROR: XED decoding failed for {instruction_hex}: {e} ===")
                instruction_data['ISA_SET'] = "Error"
                instruction_data['SHORT'] = "Error"

            executable_instructions.append(instruction_data)

            # Calculate the target address in case of a transfer instruction
            if is_func_call:
                dst_addr = address_calculation(
                    instruction_data, instruction_addr, is_func_call, gdb_comment, tracking_functions)

                if dst_addr:
                    tracking_functions.add(dst_addr)
                    list_tracking_functions.append(dst_addr)

    list_size_in_bytes = calculate_list_memory_size(executable_instructions)
    list_size_in_mb = list_size_in_bytes / 1024 / 1024  # MB 단위로 변환
    print(
        f'=== DEBUG: executable_instructions의 메모리 사용량: {list_size_in_mb:.2f} MB ===')
    print(
        f'=== DEBUG: Total instructions collected: {len(executable_instructions)} ===')

    # print(f'tracked function count: {len(tracking_functions)}')
    global tracked_func_count
    tracked_func_count = len(tracking_functions)

    try:
        utils.create_csv(executable_instructions, is_tsx_run, xtest_enable)
        print("=== DEBUG: CSV file created successfully ===")
    except Exception as e:
        print(f"=== ERROR: Failed to create CSV: {e} ===")

    btracking_time = btracking_end_time - btracking_start_time - addr_collect_time
    print(
        f'=== DEBUG: exe path tracking 추가된 메모리 사용량: {record_memory_end()} MB ===')

    end_time = time.time()
    global tracking_time
    global dis_time

    tracking_time = end_time - start_time - \
        dis_time - btracking_time - addr_collect_time


def measure_initial_memory_usage():
    process = psutil.Process(os.getpid())
    mem_usage = process.memory_info().rss / 1024 / 1024  # MB 단위로 변환
    return mem_usage


if __name__ == '__main__':
    print(
        f"=== DEBUG: 프로세스 시작 시점의 메모리 사용량: {measure_initial_memory_usage()} MB ===")
    start_time = float(os.getenv('START_TIME', '0'))
    print(f"=== DEBUG: Script start time: {start_time} ===")

    gdb_time = time.time()
    load_time = gdb_time - start_time
    print(f"=== DEBUG: GDB load time: {load_time:.6f} sec ===")

    logging_functions = []
    try:
        gdb.execute(f"set pagination off")
        print("=== DEBUG: GDB pagination disabled ===")
    except Exception as e:
        print(f"=== ERROR: Failed to disable pagination: {e} ===")

    # 쉘 스크립트에서 전달된 workload PID 가져오기
    PID = int(os.getenv('WORKLOAD_PID', '0'))
    LANGUAGE_TYPE = os.getenv('LANGUAGE_TYPE', '0')
    SCRIPT_PATH = os.getenv('SCRIPT_PATH', '0')

    print(f"=== DEBUG: Retrieved environment variables ===")
    print(f"=== DEBUG: PID: {PID} ===")
    print(f"=== DEBUG: LANGUAGE_TYPE: {LANGUAGE_TYPE} ===")
    print(f"=== DEBUG: SCRIPT_PATH: {SCRIPT_PATH} ===")

    if PID == 0:
        print("=== ERROR: Invalid PID ===")
        exit(1)

    glibc_tunables_check()
    binding_check(PID)

    got_addr = get_got_sections()
    sections = get_text_sections()

    if not got_addr:
        print("=== WARNING: No GOT sections found ===")
    if not sections:
        print("=== WARNING: No text sections found ===")

    compile_indirect = []
    runtime_indirect = []
    call_regi = []

    print("=== DEBUG: Starting main tracking process ===")
    tracking(LANGUAGE_TYPE, SCRIPT_PATH)

    end_time = time.time()
    total_time = end_time - start_time

    print(f'=== DEBUG: tracked function count: {tracked_func_count} ===')
    print(f"=== DEBUG: GDB load time: {load_time:.6f} sec ===")
    print(f"=== DEBUG: btracking time: {btracking_time:.6f} sec ===")
    print(f"=== DEBUG: addr collect time: {addr_collect_time:.6f} sec ===")
    print(f"=== DEBUG: disassemble time: {dis_time:.6f} sec ===")
    print(f"=== DEBUG: exe path tracking time: {tracking_time:.6f} sec ===")
    print(f'=== DEBUG: additionally tracked: {tracked_func_count - 1663} ===')
    print(f"=== DEBUG: total time: {total_time:.6f} sec ===")
    print(f"=== DEBUG: Number of modules searched: {module_count} ===")

    print("=== DEBUG: gdb_script_exepath_tracking.py completed successfully ===")
    exit()

    # with open('tracked_functions.txt', 'w') as f:
    #     f.write('\n'.join(logging_functions))
    # with open('compile_indirect.txt', 'w') as f:
    #     f.write('\n'.join(compile_indirect))
    # with open('runtime_indirect.txt', 'w') as f:
    #     f.write('\n'.join(runtime_indirect))
    # with open('call_regi.txt', 'w') as f:
    #     f.write('\n'.join(call_regi))
