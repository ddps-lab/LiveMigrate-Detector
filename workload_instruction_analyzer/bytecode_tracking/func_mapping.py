import gdb
import subprocess
import re

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

    result = subprocess.run(command, shell=True,
                            capture_output=True, text=True)
    if len(result.stdout) == 0:
        return False

    return True


def is_cython(lib):
    command = (
        "strings "
        f"{lib} "
        "| grep -w -o __pyx_cython_runtime"
    )

    result = subprocess.run(command, shell=True,
                            capture_output=True, text=True)
    if len(result.stdout) == 0:
        return False

    return True


def is_c(lib):
    if 'cpython-310-x86_64-linux-gnu' not in lib:
        return True
    return False


def get_func_addr_from_cython(module, functions, C_functions):
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
            except gdb.error:
                break

            i += 1


def get_func_addr_from_c(functions, C_functions):
    for func in functions:
        try:
            result = gdb.execute(f'info addr {func}', to_string=True)
            match = re.search(r'0x[0-9a-fA-F]+', result)
            if match is not None:
                addr = match.group()
                C_functions[func] = addr
        except gdb.error:
            # 함수를 찾을 수 없는 경우 건너뜀
            continue


def get_PyMethodDef(lib, func_mapping):
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
        result = subprocess.run(command, shell=True,
                                capture_output=True, text=True)
        PyMethodDef_elf_offset = int(result.stdout.split(' ')[0], 16)

        if lib not in offset_table:
            command = f'readelf -S {lib}'
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True)
            match = re.search(
                r'\[.*\]\s+\.data\s+PROGBITS\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)', result.stdout)
            if match is not None:
                offset_table[lib] = int(match.group(1), 16)
            else:
                # .data 섹션을 찾을 수 없는 경우 에러 처리
                raise ValueError(f"Could not find .data section in {lib}")
        data_ELF_VMA = offset_table[lib]

        PyMethodDef_offset = PyMethodDef_elf_offset - data_ELF_VMA

        start_addr = data_addr_table[lib] + PyMethodDef_offset
        while True:
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
            start_addr += 32

    # 디버깅 심볼이 있는지 확인
    if not is_debug_symbols_available(lib):
        infer_results = infer_global_variable_type(lib)
        for var, _ in infer_results.items():
            search_mapping(var, lib)
        return

    command = (
        "gdb -batch -ex 'info variables' "
        f"{lib}"
        "| grep PyMethodDef"
    )

    result = subprocess.run(command, shell=True,
                            capture_output=True, text=True)
    for line in result.stdout.splitlines():
        # 정규식 검색 결과가 None인지 확인
        var_match = re.search(r'\bPyMethodDef\s+(\w+)\[', line)
        if var_match is None:
            # 패턴이 매치되지 않으면 해당 라인을 건너뜀
            continue

        var = var_match.group(1)
        search_mapping(var, lib)


def check_PyMethodDef(not_pymodules):
    print(
        f"[FUNC_MAPPING] Starting PyMethodDef check for {len(not_pymodules)} modules")

    try:
        shared_libraries = get_sharedlibrary()
        print(f"[FUNC_MAPPING] Found {len(shared_libraries)} shared libraries")
    except Exception as e:
        print(f"[FUNC_MAPPING ERROR] Failed to get shared libraries: {e}")
        return {}

    func_mapping = dict()
    C_functions = {}

    processed_modules = 0
    found_libraries = 0

    for module, functions in not_pymodules.items():
        processed_modules += 1
        print(
            f"[FUNC_MAPPING] Processing module {module} with {len(functions)} functions")

        if '.' in module:
            module = module.replace('.', '/')
        if '/so' in module:
            module = module.replace('/so', '.so')

        module_found = False
        for lib in shared_libraries:
            if module in lib:
                module_found = True
                found_libraries += 1
                print(
                    f"[FUNC_MAPPING] Found library for module {module}: {lib}")

                try:
                    if is_cython(lib):
                        print(
                            f"[FUNC_MAPPING] Processing as Cython library: {lib}")
                        get_func_addr_from_cython(
                            module, functions, C_functions)
                    elif is_c(lib):
                        print(f"[FUNC_MAPPING] Processing as C library: {lib}")
                        get_func_addr_from_c(functions, C_functions)
                    else:
                        print(
                            f"[FUNC_MAPPING] Processing as Python extension with PyMethodDef: {lib}")
                        get_PyMethodDef(lib, func_mapping)

                        for func in functions:
                            if func in func_mapping:
                                C_functions[func] = func_mapping[func]
                                print(
                                    f"[FUNC_MAPPING] Mapped function {func} to address {func_mapping[func]}")
                            else:
                                print(
                                    f"[FUNC_MAPPING] Function {func} not found in PyMethodDef")
                except Exception as e:
                    print(
                        f"[FUNC_MAPPING ERROR] Failed to process library {lib}: {e}")
            else:
                continue

        if not module_found:
            print(f"[FUNC_MAPPING] No library found for module {module}")

    print(f"[FUNC_MAPPING] Completed:")
    print(f"[FUNC_MAPPING]   Processed modules: {processed_modules}")
    print(f"[FUNC_MAPPING]   Found libraries: {found_libraries}")
    print(f"[FUNC_MAPPING]   Total C functions mapped: {len(C_functions)}")

    return C_functions
