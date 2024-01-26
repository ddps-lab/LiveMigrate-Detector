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

def initialize_variables():
    return [], [], -1, -1

def parse_bytecode(byte_code, definition=False):
    # 괄호 안의 값 추출 패턴
    pattern = re.compile(r'\((.*?)\)')
    
    func_offset = -1
    method_offset = -1
    LOAD = []
    parents_object = []
    module = ''
    object_name = ''

    global addr_map
    call_map = {}

    if definition:
        object_name = byte_code[0].split(' ')[0]

    for i, line in enumerate(byte_code):
        if 'IMPORT_NAME' in line:
            module = (pattern.search(line).group(1))
            root_module = (pattern.search(line).group(1)).split('.')[0]
            # 다음 라인을 확인해 import된 모듈이 어떤 이름으로 사용되는지 파악
            next_line = byte_code[i + 1]
            if 'STORE_NAME' in next_line:
                alias = (pattern.search(next_line).group(1))
                call_map[alias] = {} if module == alias else {'__origin_name':module}
            else:
                call_map[root_module] = {} if module == root_module else {'__origin_name':module}
        if 'IMPORT_FROM' in line:
            func = (pattern.search(line).group(1))
            # 다음 라인을 확인해 import된 모듈이 어떤 이름으로 사용되는지 파악
            next_line = byte_code[i + 1]
            if 'STORE_NAME' in next_line:
                alias = (pattern.search(next_line).group(1))
                call_map[root_module][alias] = None if func == alias else func
        elif 'LOAD' in line:
            # 클래스 정의
            if 'LOAD_BUILD_CLASS' in line:
                LOAD.insert(0, '__build_class__')
            # 스택의 최상단에 있는 객체로부터 속성을 로드하고, 이 속성 값을 스택의 최상단에 푸시
            # self 객체 자체가 스택에서 제거되고 self의 value 속성 값만 스택에 남음
            elif 'LOAD_ATTR' in line:
                value = LOAD.pop(0) + '.' + pattern.search(line).group(1)
                LOAD.insert(0, value)
            # LOAD_METHOD는 스택의 최상단에 있는 객체에서 메서드를 찾음
            elif 'LOAD_METHOD' in line:
                parents_object.insert(0, LOAD[0])
                LOAD.insert(0, pattern.search(line).group(1))
            else:
                LOAD.insert(0, pattern.search(line).group(1))
        elif 'POP_TOP' in line:
            LOAD.pop(0)
        # 스택의 상위 두 항목을 사용하여 함수 객체를 만듦.
        elif 'MAKE_FUNCTION' in line:
            value = 'function object for ' + LOAD.pop(0)
            LOAD.pop(0)
            LOAD.insert(0, value)

            offset = 0
            prev_line = byte_code[i - 1]
            # 생성되는 함수가 특정 클래스에 종속적인 경우
            if 'LOAD_CONST' in prev_line:
                if '.' in (pattern.search(prev_line).group(1)):
                    parents_object = pattern.search(prev_line).group(1).split('.')[0].replace("'", "")
                    child_object = pattern.search(prev_line).group(1).split('.')[-1].replace("'", "")
                    while True:
                        # 클래스에서 정의되는 메서드들의 주소 파악
                        if '(<code object' in prev_line:
                            obj_addr = prev_line.split('at ')[1].split(',')[0].strip()
                            addr_map[obj_addr] = {parents_object:child_object}
                            break
                        offset -= 1
                        if i + offset == 0:
                            break
                        prev_line = byte_code[i + offset]   
        # 스택에 있는 N 개의 값을 합쳐 새로운 문자열을 만듦
        elif 'BUILD_STRING' in line:
            args_count = int(line.split('BUILD_STRING')[1].strip())
            temp = ''
            for i in range(args_count):
                temp += LOAD.pop(0)
            LOAD.insert(0, temp)
        elif 'BUILD_LIST' in line:
            args_count = int(line.split('BUILD_LIST')[1].strip())
            temp = ''
            if args_count == 0:
                LOAD.insert(0, '[]')
            else:    
                for i in range(args_count):
                    temp += LOAD.pop(0)
                LOAD.insert(0, temp)
        # 스택의 최상단에서 N번째 리스트를 확장
        elif 'LIST_EXTEND' in line:
            args_count = int(line.split('LIST_EXTEND')[1].strip())
            for i in range(args_count):
                temp += LOAD.pop(0)
        elif 'STORE_ATTR' in line:
            # 함수 호출이 아닌 경우를 구분해야함. 함수 호출 없이 객체.변수에 값 할당하는 경우가 있기 때문.
            # Python 바이트코드에서 STORE_ATTR 명령어 다음에 CALL_FUNCTION 명령어가 오는 것은 일반적인 상황이 아님.
            # 따라서 명령어 블록을 조사해 STORE_ATTR 위의 명령들에서 함수 또는 메서드 호출이 있는지 확인함.
            offset = 0
            prev_line = byte_code[i - 1]
            object_assign = False
            while True:
                if 'CALL_FUNCTION' in prev_line or 'CALL_METHOD' in prev_line:
                    object_assign = True
                    break
                offset -= 1
                if i + offset == 0:
                    break
                prev_line = byte_code[i + offset]

            if object_assign:
                result = line.split('(')[1].split(')')[0]
                category = func_classification(LOAD[-1], call_map)
                if category not in call_map:
                    call_map[category] = {}
                call_map[category][LOAD[-1]] = result
        elif 'CALL_FUNCTION' in line:
            func_offset = int(line.split('CALL_FUNCTION')[1].strip())
            if LOAD[func_offset] == '__build_class__':
                # FIXME: 클래스 이름 활용 안함.
                # 다음 라인을 읽어 생성된 클래스 이름을 파악.
                if i + 1 < len(byte_code):
                    next_line = byte_code[i + 1]
                    class_name = (pattern.search(next_line).group(1))
                    # print(f'build class: {class_name}')
            else:
                if len(parents_object) == 0:
                    category = func_classification(LOAD[func_offset], call_map)
                    if category not in call_map:
                        call_map[category] = {}

                    call_map[category][LOAD[func_offset]] = None
                    if category == '__user_def':
                        next_line = byte_code[i + 1]
                        if 'STORE_NAME' in next_line:
                            result = (pattern.search(next_line).group(1))
                            call_map[category][LOAD[func_offset]] = result
                    # print(f'func: {LOAD[func_offset]} is in {[category]}')
                else:
                    if parents_object[0] not in call_map:
                        call_map[parents_object[0]] = {}
                    call_map[parents_object[0]][LOAD[func_offset]] = None
                    # print(f'func: {LOAD[func_offset]} is in {parents_object}')

        elif 'CALL_METHOD' in line:
            method_offset = int(line.split('CALL_METHOD')[1].strip())
            if len(parents_object) == 0:
                category = func_classification(LOAD[method_offset], call_map)
                if category not in call_map:
                    call_map[category] = {}

                call_map[category][LOAD[method_offset]] = None                
                if category == '__user_def':
                    next_line = byte_code[i + 1]
                    if 'STORE_NAME' in next_line:
                        result = (pattern.search(next_line).group(1))
                        call_map[category][LOAD[func_offset]] = result                
                # print(f'method: {LOAD[method_offset]} is in {[category]}')
            else:
                if parents_object[0] not in call_map:
                    call_map[parents_object[0]] = {}
                call_map[parents_object[0]][LOAD[method_offset]] = None
                # print(f'method: {LOAD[method_offset]} is in {parents_object}')

        # next line(source code)
        if line.strip() == '':
            LOAD, parents_object, func_offset, method_offset = initialize_variables()
            module = ''
            root_module = ''
    
    return call_map

def func_classification(func, call_map):
    global obj_sets

    if func in obj_sets:
        return '__user_def'

    for outer_key, inner_dict in call_map.items():
        if func in inner_dict:
            return outer_key
    return '__builtin'

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

    with open('example_scripts/main.py', 'r') as f:
        source_code = f.read()

    byte_code = compile(source_code, '<string>', 'exec')
    codes, definitions = preprocessing_bytecode(byte_code)
    obj_sets, user_def_list = parse_definition(definitions)

    for i in range(len(definitions)):
        key, value = next(iter(user_def_list[i].items()))
        DEF_MAP[value + '.' + key] = bcode_parser.parse_def(definitions[i], addr_map, obj_sets)

    modules = parse_bytecode(codes)
    print('------------------------------------------------------')
    postprocessing_defmap(DEF_MAP, addr_map)
    pprint(DEF_MAP)