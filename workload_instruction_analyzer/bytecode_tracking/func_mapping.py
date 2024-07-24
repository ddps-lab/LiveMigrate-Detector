import gdb
import subprocess
import re
from pprint import pprint

from infer_variable_type import infer_global_variable_type

offset_table = {}
data_addr_table = {}
def get_data_addr():
    result = gdb.execute('info files', to_string=True)

    # 정규 표현식으로 .data 섹션의 시작 주소 추출
    pattern = re.compile(r'(0x[0-9a-f]+) - 0x[0-9a-f]+ is \.data in (.+)')
    matches = pattern.findall(result)

    # 시작 주소 추출
    data_addr_table = {lib: int(addr, 16) for addr, lib in matches}
    return data_addr_table
data_addr_table = get_data_addr()

def get_sharedlibrary():
    result = gdb.execute("info sharedlibrary", to_string=True)

    shared_libraries = []
    library_paths = re.findall(r'/[^\s]+', result)
    for path in library_paths:
        shared_libraries.append(path)
    
    return shared_libraries

def is_debug_symbols_available(lib):
    command = (
        "readelf -S "
        f"{lib} "
        "| grep .debug"
    )

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if len(result.stdout) == 0:
        return False

    return True

def get_PyMethodDef(module, functions, func_mapping):
    def search_mapping(var, lib):
        '''
        특정 PyMethodDef의 정확한 주소를 계산

        1. .data 섹션의 VMA와 mod_methods의 오프셋 간의 차이 계산:
            - .data 섹션의 VMA: 0x00006140
            - mod_methods의 오프셋: 0x000061c0
            - .data로부터 mod_methods가 존재하는 오프셋: 0x000061c0 - 0x00006140 = 0x80
        2. .data 섹션의 메모리 시작 주소와 이 차이를 더하여 실제 메모리 주소를 계산:
            - .data 섹션의 메모리 시작 주소: 0x000076fc4777f140
            - 오프셋: 0x80
            - 실제 메모리 주소: 0x00007c61c7af7140 + 0x80 = 0x000076fc47780220
        '''
        command = f'objdump -t {lib} | grep {var}'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        PyMethodDef_elf_offset = int(result.stdout.split(' ')[0], 16)
        # print(f'PyMethodDef_elf_offset: {hex(PyMethodDef_elf_offset)}')

        if lib not in offset_table:
            command = f'readelf -S {lib}'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            # match = re.search(r'\.data\s+PROGBITS\s+\S+\s+(\S+)', result.stdout)
            match = re.search(r'\[.*\]\s+\.data\s+PROGBITS\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)', result.stdout)
            offset_table[lib] = int(match.group(1), 16)
        data_ELF_VMA = offset_table[lib]
        # print(f'.data_ELF_VMA: {hex(data_ELF_VMA)}')

        PyMethodDef_offset = PyMethodDef_elf_offset - data_ELF_VMA
        # print(f'PyMethodDef_offset: {hex(PyMethodDef_offset)}')

        start_addr = data_addr_table[lib] + PyMethodDef_offset
        # print(f'data_addr: {hex(data_addr_table[lib])}')
        # print(f'start_addr: {hex(start_addr)}')
        while True:
            ml_name_ptr = gdb.execute(f"x/a {hex(start_addr)}", to_string=True).split(':')[1].strip()
            ml_name = gdb.execute(f"x/s {ml_name_ptr}", to_string=True)
            ml_meth = gdb.execute(f"x/a {hex(start_addr + 8)}", to_string=True).split(':')[1].split('<')[0].strip()

            if ml_name_ptr == '0x0' and ml_meth == '0x0':
                break
            
            ml_name = re.search(r'\"([^\"]*)\"', ml_name).group(1)

            func_mapping[ml_name] = ml_meth
            start_addr += 32

    shared_libraries = get_sharedlibrary()

    if '.' in module:
        module = module.replace('.', '/')
    for lib in shared_libraries:
        if module in lib:
            pass
        # if module in lib.split('/')[-1]:
            # if 'cpython' not in lib.split('/')[-1]:
            #     for func in functions:
            #         start_addr = gdb.execute(f"info addr {func}", to_string=True)
            #         start_addr = int(re.search(r'0x[0-9a-fA-F]+', start_addr).group(0), 16)

            #         func_mapping[func] = hex(start_addr)
            #     continue
        else:
            continue
        
        # 디버깅 심볼이 있는지 확인
        if not is_debug_symbols_available(lib):
            infer_results = infer_global_variable_type(lib)
            for var, _ in infer_results.items():
                search_mapping(var, lib)
            continue

        command = (
            "gdb -batch -ex 'info variables' "
            f"{lib}"
            "| grep PyMethodDef"
        )

        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            var = re.search(r'\bPyMethodDef\s+(\w+)\[', line).group(1)
            search_mapping(var, lib)

def check_PyMethodDef(not_pymodules):
    func_mapping = {'ctypes':set()}
    C_functions = {}
    for module, functions in not_pymodules.items():
        get_PyMethodDef(module, functions, func_mapping)
        for func in functions:
            if func in func_mapping:
                C_functions[func] = func_mapping[func]

    return C_functions