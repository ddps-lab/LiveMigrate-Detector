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

def parse_pychaces():
    pymodules = set()

    directory = './__pycache__'
    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    for module in files:
        pymodules.add(module.split('.')[0])

    return pymodules

def preprocessing_bytecode(byte_code):
    '''
    바이트코드를 main과 def 파트로 구분해 각각 반환.
    '''
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
    '''
    함수 이름 중복을 구분하기 위해 상위 객체까지 이름에 포함.
    상위 객체의 주소를 이름으로 치환.
    '''
    obj_addrs = addr_map.keys()
    def_map = DEF_MAP.copy()
    for key, _ in def_map.items():
        if key.split('.')[0] in obj_addrs:
            parent, value = next(iter(addr_map[key.split('.')[0]].items()))
            # 생성자는 클래스 할당 함수에 포함
            if value == '__init__':
                replace = parent
            else:
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
    '''
    사용자 정의 객체를 수집.
    '''
    obj_lists = []
    obj_sets = set()
    for i in range(len(definitions)):
        obj = definitions[i][0].split(' ')[0]
        addr = definitions[i][0].split('at ')[1].split(',')[0].strip()
        obj_sets.add(obj)
        obj_lists.append({obj:addr})

    return obj_sets, obj_lists

def user_def_tracking(called_map, obj_map, def_map, tracked):

    for obj in called_map['__user_def']:
        tracked.add(obj)
        # 클래스 선언 또는 단독 함수 호출
        if obj in def_map.keys():
            tracked.update(def_map[obj])
        else:
            print(obj)
    
    print(tracked)

if __name__ == '__main__':
    LIBRARIES = stdlib_list("3.10")
    called_map = {}
    def_map = {}
    addr_map = {}
    obj_map = {}
    tracked = set()

    with open('example_scripts/main.py', 'r') as f:
    # with open('example_scripts/testpymodule.py', 'r') as f:
        source_code = f.read()

    byte_code = compile(source_code, '<string>', 'exec')
    codes, definitions = preprocessing_bytecode(byte_code)
    # 현재 파싱중인 스크립트에 정의된 객체(함수, 클래스, 메서드)
    obj_sets, user_def_list = parse_definition(definitions)

    for i in range(len(definitions)):
        key, value = next(iter(user_def_list[i].items()))
        def_map[value + '.' + key] = bcode_parser.parse_def(definitions[i], addr_map, obj_sets, obj_map)

    print('------------------------------------------------------------------------------------------------------------')
    postprocessing_defmap(def_map, addr_map)
    print('==== def map ====')
    pprint(def_map)
    print('------------------------------------------------------------------------------------------------------------')
    called_map = bcode_parser.parse_main(codes, addr_map, obj_sets, obj_map)
    print('==== called map ====')
    pprint(called_map)
    print('------------------------------------------------------------------------------------------------------------')
    pprint(obj_map)
    print('------------------------------------------------------------------------------------------------------------')

    # user_def_tracking(called_map, obj_map, def_map, tracked)