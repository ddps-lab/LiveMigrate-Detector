import gdb
import subprocess
import re

from infer_variable_type import infer_global_variable_type

print("=== DEBUG: func_mapping.py imported ===")

offset_table = {}
data_addr_table = {}


def get_data_addr():
    print("=== DEBUG: Getting data addresses ===")
    try:
        result = gdb.execute('info files', to_string=True)
        print(f"=== DEBUG: GDB info files output length: {len(result)} ===")
    except Exception as e:
        print(f"=== ERROR: Failed to get file info from GDB: {e} ===")
        return {}

    # 정규 표현식으로 .data 섹션의 시작 주소 추출
    pattern = re.compile(r'(0x[0-9a-f]+) - 0x[0-9a-f]+ is \.data in (.+)')
    matches = pattern.findall(result)

    # 시작 주소 추출
    data_addr_table = {lib: int(addr, 16) for addr, lib in matches}
    print(f"=== DEBUG: Found {len(data_addr_table)} data sections ===")
    for lib, addr in data_addr_table.items():
        print(f"=== DEBUG: Data section - {lib}: {hex(addr)} ===")
    return data_addr_table


data_addr_table = get_data_addr()


def get_sharedlibrary():
    print("=== DEBUG: Getting shared libraries ===")
    try:
        result = gdb.execute("info sharedlibrary", to_string=True)
        print(f"=== DEBUG: Shared library info length: {len(result)} ===")
    except Exception as e:
        print(f"=== ERROR: Failed to get shared library info: {e} ===")
        return []

    shared_libraries = []
    library_paths = re.findall(r'/[^\s]+', result)
    for path in library_paths:
        shared_libraries.append(path)

    print(f"=== DEBUG: Found {len(shared_libraries)} shared libraries ===")
    for i, lib in enumerate(shared_libraries[:5]):  # Show first 5
        print(f"=== DEBUG: Shared library {i+1}: {lib} ===")
    if len(shared_libraries) > 5:
        print(
            f"=== DEBUG: ... and {len(shared_libraries) - 5} more libraries ===")

    return shared_libraries


def is_debug_symbols_available(lib):
    print(f"=== DEBUG: Checking debug symbols for {lib} ===")
    command = (
        "readelf -S "
        f"{lib} "
        "| grep .debug"
    )

    try:
        result = subprocess.run(command, shell=True,
                                capture_output=True, text=True)
        has_debug = len(result.stdout) > 0
        print(
            f"=== DEBUG: Debug symbols {'available' if has_debug else 'not available'} for {lib} ===")
        return has_debug
    except Exception as e:
        print(f"=== ERROR: Failed to check debug symbols for {lib}: {e} ===")
        return False


def is_cython(lib):
    print(f"=== DEBUG: Checking if {lib} is Cython ===")
    command = (
        "strings "
        f"{lib} "
        "| grep -w -o __pyx_cython_runtime"
    )

    try:
        result = subprocess.run(command, shell=True,
                                capture_output=True, text=True)
        is_cython_lib = len(result.stdout) > 0
        print(
            f"=== DEBUG: {lib} is {'Cython' if is_cython_lib else 'not Cython'} ===")
        return is_cython_lib
    except Exception as e:
        print(f"=== ERROR: Failed to check if {lib} is Cython: {e} ===")
        return False


def is_c(lib):
    is_c_lib = 'cpython-310-x86_64-linux-gnu' not in lib
    print(
        f"=== DEBUG: {lib} is {'C library' if is_c_lib else 'Python extension'} ===")
    return is_c_lib


def get_func_addr_from_cython(module, functions, C_functions):
    print(
        f"=== DEBUG: Getting Cython function addresses for module {module}, {len(functions)} functions ===")

    found_functions = 0
    for func in functions:
        mangling = '__pyx_pw'

        path = module.split('/')
        for directory in path:
            mangling = mangling + '_' + str(len(directory)) + directory

        i = 1
        while (True):
            sym = mangling + f'_{i}{func}'

            try:
                result = gdb.execute(f'info addr {sym}', to_string=True)
                match = re.search(r'0x[0-9a-fA-F]+', result)
                if match is not None:
                    addr = match.group()
                    C_functions[sym] = addr
                    found_functions += 1
                    print(
                        f"=== DEBUG: Found Cython function {sym} at {addr} ===")
            except gdb.error:
                break

            i += 1

    print(f"=== DEBUG: Found {found_functions} Cython function addresses ===")


def get_func_addr_from_c(functions, C_functions):
    print(
        f"=== DEBUG: Getting C function addresses for {len(functions)} functions ===")

    found_functions = 0
    for func in functions:
        try:
            result = gdb.execute(f'info addr {func}', to_string=True)
            match = re.search(r'0x[0-9a-fA-F]+', result)
            if match is not None:
                addr = match.group()
                C_functions[func] = addr
                found_functions += 1
                print(f"=== DEBUG: Found C function {func} at {addr} ===")
        except gdb.error:
            # 함수를 찾을 수 없는 경우 건너뜀
            print(f"=== DEBUG: Could not find C function {func} ===")
            continue

    print(f"=== DEBUG: Found {found_functions} C function addresses ===")


def get_PyMethodDef(lib, func_mapping):
    print(f"=== DEBUG: Getting PyMethodDef for library {lib} ===")

    def search_mapping(var, lib):
        print(f"=== DEBUG: Searching mapping for variable {var} in {lib} ===")
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
        try:
            result = subprocess.run(command, shell=True,
                                    capture_output=True, text=True)
            if not result.stdout:
                print(f"=== DEBUG: Variable {var} not found in {lib} ===")
                return

            PyMethodDef_elf_offset = int(result.stdout.split(' ')[0], 16)
            print(
                f"=== DEBUG: Found variable {var} at ELF offset {hex(PyMethodDef_elf_offset)} ===")
        except Exception as e:
            print(
                f"=== ERROR: Failed to find variable {var} in {lib}: {e} ===")
            return

        if lib not in offset_table:
            command = f'readelf -S {lib}'
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True)
                match = re.search(
                    r'\[.*\]\s+\.data\s+PROGBITS\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)', result.stdout)
                if match is not None:
                    offset_table[lib] = int(match.group(1), 16)
                    print(
                        f"=== DEBUG: Data section VMA for {lib}: {hex(offset_table[lib])} ===")
                else:
                    # .data 섹션을 찾을 수 없는 경우 에러 처리
                    print(
                        f"=== ERROR: Could not find .data section in {lib} ===")
                    raise ValueError(f"Could not find .data section in {lib}")
            except Exception as e:
                print(
                    f"=== ERROR: Failed to read ELF sections for {lib}: {e} ===")
                return

        data_ELF_VMA = offset_table[lib]

        PyMethodDef_offset = PyMethodDef_elf_offset - data_ELF_VMA

        if lib not in data_addr_table:
            print(f"=== ERROR: No data address found for {lib} ===")
            return

        start_addr = data_addr_table[lib] + PyMethodDef_offset
        print(
            f"=== DEBUG: Calculated PyMethodDef start address: {hex(start_addr)} ===")

        method_count = 0
        while True:
            try:
                ml_name_ptr = gdb.execute(
                    f"x/a {hex(start_addr)}", to_string=True).split(':')[1].strip()
                ml_name_ptr = ml_name_ptr.split(" ")[0].strip()
                ml_name = gdb.execute(f"x/s {ml_name_ptr}", to_string=True)
                ml_meth = gdb.execute(
                    f"x/a {hex(start_addr + 8)}", to_string=True).split(':')[1].split('<')[0].strip()

                if ml_name_ptr == '0x0' and ml_meth == '0x0':
                    break

                # 정규식 검색 결과가 None인지 확인
                ml_name_match = re.search(r'\"([^\"]*)\"', ml_name)
                if ml_name_match is None:
                    # 패턴이 매치되지 않으면 다음 항목으로 건너뜀
                    start_addr += 32
                    continue

                ml_name = ml_name_match.group(1)

                func_mapping[ml_name] = ml_meth
                method_count += 1
                print(f"=== DEBUG: Found method {ml_name} -> {ml_meth} ===")
                start_addr += 32

            except Exception as e:
                print(
                    f"=== ERROR: Failed to read PyMethodDef at {hex(start_addr)}: {e} ===")
                break

        print(f"=== DEBUG: Found {method_count} methods in {var} ===")

    # 디버깅 심볼이 있는지 확인
    if not is_debug_symbols_available(lib):
        print(
            f"=== DEBUG: No debug symbols, using type inference for {lib} ===")
        try:
            infer_results = infer_global_variable_type(lib)
            print(
                f"=== DEBUG: Type inference found {len(infer_results)} variables ===")
            for var, _ in infer_results.items():
                search_mapping(var, lib)
        except Exception as e:
            print(f"=== ERROR: Type inference failed for {lib}: {e} ===")
        return

    print(f"=== DEBUG: Using debug symbols for {lib} ===")
    command = (
        "gdb -batch -ex 'info variables' "
        f"{lib}"
        "| grep PyMethodDef"
    )

    try:
        result = subprocess.run(command, shell=True,
                                capture_output=True, text=True)
        print(
            f"=== DEBUG: Found PyMethodDef variables: {len(result.stdout.splitlines())} lines ===")

        for line in result.stdout.splitlines():
            # 정규식 검색 결과가 None인지 확인
            var_match = re.search(r'\bPyMethodDef\s+(\w+)\[', line)
            if var_match is None:
                # 패턴이 매치되지 않으면 해당 라인을 건너뜀
                continue

            var = var_match.group(1)
            print(f"=== DEBUG: Processing PyMethodDef variable: {var} ===")
            search_mapping(var, lib)
    except Exception as e:
        print(
            f"=== ERROR: Failed to get PyMethodDef variables for {lib}: {e} ===")


def check_PyMethodDef(not_pymodules):
    print(
        f"=== DEBUG: Checking PyMethodDef for {len(not_pymodules)} modules ===")

    try:
        shared_libraries = get_sharedlibrary()
    except Exception as e:
        print(f"=== ERROR: Failed to get shared libraries: {e} ===")
        return {}

    func_mapping = dict()
    C_functions = {}

    processed_modules = 0
    for module, functions in not_pymodules.items():
        processed_modules += 1
        print(
            f"=== DEBUG: Processing module {processed_modules}/{len(not_pymodules)}: {module} with {len(functions)} functions ===")

        if '.' in module:
            module = module.replace('.', '/')
        if '/so' in module:
            module = module.replace('/so', '.so')

        found_library = False
        for lib in shared_libraries:
            if module in lib:
                found_library = True
                print(f"=== DEBUG: Found matching library: {lib} ===")

                try:
                    if is_cython(lib):
                        print(f"=== DEBUG: Processing as Cython library ===")
                        get_func_addr_from_cython(
                            module, functions, C_functions)
                    elif is_c(lib):
                        print(f"=== DEBUG: Processing as C library ===")
                        get_func_addr_from_c(functions, C_functions)
                    else:
                        print(f"=== DEBUG: Processing as Python extension ===")
                        get_PyMethodDef(lib, func_mapping)

                        for func in functions:
                            if func in func_mapping:
                                C_functions[func] = func_mapping[func]
                                print(
                                    f"=== DEBUG: Mapped function {func} -> {func_mapping[func]} ===")
                except Exception as e:
                    print(
                        f"=== ERROR: Failed to process library {lib}: {e} ===")
                break

        if not found_library:
            print(
                f"=== DEBUG: No matching library found for module {module} ===")

    print(
        f"=== DEBUG: check_PyMethodDef completed, found {len(C_functions)} C function addresses ===")
    return C_functions
