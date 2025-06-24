import gdb
import subprocess
import re
import ctypes
import os

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


def get_shared_libraries():
    """Get list of shared libraries from GDB"""
    try:
        output = gdb.execute("info sharedlibrary", to_string=True)
        libs = []

        for line in output.split('\n'):
            if '.so' in line and 'python' in line.lower():
                parts = line.split()
                if len(parts) >= 4:
                    libs.append(parts[-1])

        return libs
    except Exception as e:
        print(f"=== ERROR: Failed to get shared libraries: {e} ===")
        return []


def extract_function_names(script_functions):
    """Extract function names from script_functions dict"""
    names = set()

    for key in script_functions.keys():
        if isinstance(key, str):
            # Extract base function name
            name = key.split('.')[-1]  # Get last part after dot
            name = re.sub(r'[<>"]', '', name)  # Remove special chars
            if name and not name.startswith('_'):
                names.add(name)

    return list(names)


def find_library_functions(lib_path, function_names):
    """Find function addresses in a specific library"""
    functions = {}

    try:
        # Use objdump to get function symbols
        result = subprocess.run(['objdump', '-t', lib_path],
                                capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return functions

        for line in result.stdout.split('\n'):
            for func_name in function_names:
                if func_name in line and 'F .text' in line:
                    parts = line.split()
                    if len(parts) >= 1:
                        addr = parts[0]
                        try:
                            addr_int = int(addr, 16)
                            if addr_int > 0:
                                functions[func_name] = f"0x{addr_int:016x}"
                        except ValueError:
                            continue

    except Exception as e:
        pass

    return functions


def check_PyMethodDef(module_dict):
    """Check PyMethodDef structures for C function addresses"""
    print("=== DEBUG: Checking PyMethodDef structures ===")
    C_functions = {}
    processed_count = 0

    try:
        for module_name, module_info in module_dict.items():
            processed_count += 1
            if processed_count % 50 == 0:
                print(
                    f"=== DEBUG: Processed {processed_count}/{len(module_dict)} modules ===")

            try:
                addresses = extract_pymethoddef_addresses(
                    module_name, module_info)
                C_functions.update(addresses)
            except Exception as e:
                continue

    except Exception as e:
        print(f"=== ERROR: PyMethodDef checking failed: {e} ===")

    print(
        f"=== DEBUG: PyMethodDef check completed: {len(C_functions)} functions found ===")
    return C_functions


def extract_pymethoddef_addresses(module_name, module_info):
    """Extract function addresses from PyMethodDef structure"""
    addresses = {}

    try:
        if not isinstance(module_info, dict) or '__called' not in module_info:
            return addresses

        called_functions = module_info['__called']

        for func_name in called_functions:
            try:
                # Try to get function address directly
                cmd = f"p/x &{func_name}"
                result = gdb.execute(cmd, to_string=True)

                if 'No symbol' not in result and '0x' in result:
                    addr_str = result.split('=')[-1].strip()
                    addr = int(addr_str, 16)
                    addresses[func_name] = f"0x{addr:016x}"

            except Exception:
                continue

    except Exception as e:
        pass

    return addresses


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


def map_c_functions(script_functions):
    """Map Python function names to C function addresses"""
    print("=== DEBUG: Starting C function mapping ===")
    c_functions = {}

    # Get shared libraries
    libs = get_shared_libraries()
    print(f"=== DEBUG: Found {len(libs)} shared libraries ===")

    # Extract function names from script_functions
    function_names = extract_function_names(script_functions)
    print(
        f"=== DEBUG: Extracted {len(function_names)} function names to search ===")

    # Search for C functions
    for lib_path in libs:
        if not lib_path or 'python' not in lib_path.lower():
            continue

        try:
            lib_functions = find_library_functions(lib_path, function_names)
            c_functions.update(lib_functions)
        except Exception as e:
            continue

    print(f"=== DEBUG: Found {len(c_functions)} C function mappings ===")
    return c_functions
