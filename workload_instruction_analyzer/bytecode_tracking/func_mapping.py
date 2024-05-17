import gdb
import subprocess
import re
from pprint import pprint

def get_sharedlibrary():
    result = gdb.execute("info sharedlibrary", to_string=True)

    shared_libraries = []
    library_paths = re.findall(r'/[^\s]+', result)
    for path in library_paths:
        shared_libraries.append(path)
        # shared_libraries.append(path.split('/')[-1])
    
    return shared_libraries

def get_variable(module):
    def sizeof(var):
        result = gdb.execute(f"p sizeof({var}) / sizeof(PyMethodDef)", to_string=True)
        size = result.split('=')[-1].strip()

        return size
    
    def search_mapping(var):
        size = int(sizeof(var))
        func_mapping = {}

        start_addr = gdb.execute(f"info addr {var}", to_string=True)
        start_addr = re.search(r'0x[0-9a-fA-F]+', start_addr).group(0)
        start_addr = int(start_addr, 16)
        for _ in range(size - 1):
            
            ml_name_ptr = gdb.execute(f"x/a {hex(start_addr)}", to_string=True).split(':')[1].strip()
            ml_name = gdb.execute(f"x/s {ml_name_ptr}", to_string=True)
            ml_meth = gdb.execute(f"x/a {hex(start_addr + 8)}", to_string=True).split(':')[1].split('<')[0].strip()

            ml_name = re.search(r'\"([^\"]*)\"', ml_name).group(1)
            # print(ml_name)
            # print(ml_meth)

            func_mapping[ml_name] = ml_meth
            start_addr += 32

        return func_mapping

    shared_libraries = get_sharedlibrary()

    for lib in shared_libraries:
        if module in lib.split('/')[-1]:
            path = lib
            
    command = (
        "gdb -batch -ex 'info variables' "
        f"{path}"
        "| grep PyMethodDef"
    )
    print(path)

    # func_mapping = search_mapping('PyCPointerType_methods')
    # func_mapping = search_mapping('csv_methods')
    # pprint(func_mapping)
    # exit()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    pprint(result.stdout)
    for line in result.stdout.splitlines():
        var = re.search(r'\bPyMethodDef\s+(\w+)\[', line).group(1)
        func_mapping = search_mapping(var)
        pprint(func_mapping)

def check_PyDefMethods(not_pymodules):
    for module, func in not_pymodules.items():
        print(module)
        get_variable(module)

if __name__ == '__main__':
    gdb.execute("set pagination off")