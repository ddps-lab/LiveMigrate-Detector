import gdb
import subprocess
import re
from pprint import pprint

from infer_variable_type import infer_global_variable_type

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

def get_PyMethodDef(module, func, func_mapping):
    def sizeof(var):
        result = gdb.execute(f"p sizeof({var}) / sizeof(PyMethodDef)", to_string=True)
        size = result.split('=')[-1].strip()

        return size
    
    def search_mapping(var):
        size = int(sizeof(var))

        start_addr = gdb.execute(f"info addr {var}", to_string=True)
        start_addr = re.search(r'0x[0-9a-fA-F]+', start_addr).group(0)
        start_addr = int(start_addr, 16)
        for _ in range(size - 1):
            
            ml_name_ptr = gdb.execute(f"x/a {hex(start_addr)}", to_string=True).split(':')[1].strip()
            ml_name = gdb.execute(f"x/s {ml_name_ptr}", to_string=True)
            ml_meth = gdb.execute(f"x/a {hex(start_addr + 8)}", to_string=True).split(':')[1].split('<')[0].strip()

            ml_name = re.search(r'\"([^\"]*)\"', ml_name).group(1)

            func_mapping[ml_name] = ml_meth
            start_addr += 32

    shared_libraries = get_sharedlibrary()

    for lib in shared_libraries:
        if module in lib.split('/')[-1]:
            if 'cpython' not in lib.split('/')[-1]:
                func_mapping['ctypes'].update(func)
                continue
        else:
            continue
        
        # 디버깅 심볼이 있는지 체크해야겠네
        if not is_debug_symbols_available(lib):
            print(lib.split('/')[-1])
            infer_global_variable_type(lib)
            continue

        command = (
            "gdb -batch -ex 'info variables' "
            f"{lib}"
            "| grep PyMethodDef"
        )

        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            var = re.search(r'\bPyMethodDef\s+(\w+)\[', line).group(1)
            search_mapping(var)

def check_PyDefMethods(not_pymodules):
    func_mapping = {'ctypes':set()}
    for module, func in not_pymodules.items():
        get_PyMethodDef(module, func, func_mapping)

    print(f'\033[31m==== c funcs ====\033[0m')
    pprint(func_mapping)

if __name__ == '__main__':
    gdb.execute("set pagination off")