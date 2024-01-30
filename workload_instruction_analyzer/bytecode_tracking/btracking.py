import dis
import io
import re
from contextlib import redirect_stdout
import os
import sys

import bcode_parser

# get python builtin modules
from stdlib_list import stdlib_list
# temp
from pprint import pprint
import json
import numpy

def parse_pychaces():
    pymodules = set()

    directory = './__pycache__'
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    for module in files:
        pymodules.add(module.split('.')[0])

    return pymodules

def preprocessing_bytecode(byte_code):
    # StringIO 객체를 생성
    f = io.StringIO()
    # dis의 출력을 StringIO 객체로 리디렉션
    with redirect_stdout(f):
        dis.dis(byte_code)

    # StringIO 객체에서 값을 얻고, 이를 줄 단위로 분할
    dis_output = f.getvalue()
    codes = dis_output.split('Disassembly of <code object')[0].strip().split('\n')
    objects = dis_output.split('Disassembly of <code object')[1:]
    for i, obj in enumerate(objects):
        objects[i] = obj.strip().split('\n')

    return codes, objects

def is_builtin_module(module_name):
    global LIBRARIES

    if '.' in module_name:
        module_name = module_name.split('.')[0]

    if module_name in LIBRARIES:
        return True
    else:
        return False

def postprocessing_defmap(DEF_MAP, addr_map):
    obj_addrs = addr_map.keys()
    def_map = DEF_MAP.copy()
    for key, _ in def_map.items():
        if key.split('.')[0] in obj_addrs:
            parent, value = next(iter(addr_map[key.split('.')[0]].items()))
            replace = parent + '.' + value
            DEF_MAP[replace] = DEF_MAP.pop(key)
        else:
            DEF_MAP[key.split('.')[1]] = DEF_MAP.pop(key)

def postprocessing_bytecode():
    global CALL_TRACE
    global USER_DEF

    pymodules = parse_pychaces()

    for module in CALL_TRACE.keys():
        if is_builtin_module(module):
            CALL_TRACE[module]['__module_type'] = 'built-in'
        elif module in pymodules:
            CALL_TRACE[module]['__module_type'] = 'pymodule'
        else:
            CALL_TRACE[module]['__module_type'] = 'cmodule'

def parse_definition(definitions):
    obj_lists = []
    obj_sets = set()
    for i in range(len(definitions)):
        obj = definitions[i][0].split(' ')[0]
        addr = definitions[i][0].split('at ')[1].split(',')[0].strip()
        obj_sets.add(obj)
        obj_lists.append({obj:addr})

    return obj_sets, obj_lists
            
if __name__ == '__main__':
    CALL_TRACE = {}
    LIBRARIES = stdlib_list("3.10")
    modules = {}
    USER_DEF = {}
    DEF_MAP = {}
    addr_map = {}
    obj_map = {}

    with open('example_scripts/main.py', 'r') as f:
    # with open('example_scripts/testpymodule.py', 'r') as f:
        source_code = f.read()

    byte_code = compile(source_code, '<string>', 'exec')
    codes, definitions = preprocessing_bytecode(byte_code)
    obj_sets, user_def_list = parse_definition(definitions)

    print(obj_sets)

    for i in range(len(definitions)):
        key, value = next(iter(user_def_list[i].items()))
        DEF_MAP[value + '.' + key] = bcode_parser.parse_def(definitions[i], addr_map, obj_sets, obj_map)

    print('------------------------------------------------------------------------------------------------------------')
    postprocessing_defmap(DEF_MAP, addr_map)
    print('==== def map ====')
    pprint(DEF_MAP)
    print('------------------------------------------------------------------------------------------------------------')
    modules = bcode_parser.parse_main(codes, addr_map, obj_sets, obj_map)
    print('==== called map ====')
    pprint(modules)
    print('------------------------------------------------------------------------------------------------------------')
    pprint(obj_map)
    print('------------------------------------------------------------------------------------------------------------')