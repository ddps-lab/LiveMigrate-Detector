import dis
import io
from contextlib import redirect_stdout
import os

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

def final_call(obj_map, def_map, obj):
    level = obj.count('.') + 1
    # 객체를 참조하는 호출
    if level > 0:
        objs = obj.split('.')
        
        key = objs[0]
        for i in range(level):
            try:
                value = obj_map[key]
                key = value + '.' + objs[i + 1]
            except KeyError:
                break
        
        # 최종 호출 함수가 사용자 정의 함수인 경우
        if key in def_map.keys():
            return def_map[key]
    else:
        return obj

# 너비탐색으로 진행.
def user_def_tracking(called_map, obj_map, def_map):
    '''
    userdef 객체에서 호출되는 함수를 트래킹.
    '''
    # 새로 추적된 함수들을 저장할 곳.
    new_tracked = {'__builtin':set(), '__user_def':set()}
    for key in called_map.keys():
        if key == '__builtin' or key == '__user_def':
            continue
        new_tracked[key] = {'__called':set()}

    for obj in called_map['__user_def']:
        # print(f'\033[31muser_def: {obj}\033[0m')
        chain = final_call(obj_map, def_map, obj)

        for func in chain:
            category = bcode_parser.func_classification(func, called_map, obj_sets, obj_map)
            if category == '__builtin' or category == '__user_def':
                if func not in called_map[category]:
                    new_tracked[category].add(func)
            elif func not in called_map[category]:
                func = func.replace(f'{category}.', '')
                if func not in called_map[category]['__called']:
                    new_tracked[category]['__called'].add(func)
            
    
    pprint(new_tracked)

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

    # print('------------------------------------------------------------------------------------------------------------')
    postprocessing_defmap(def_map, addr_map)
    # print('==== def map ====')
    # pprint(def_map)
    # print('------------------------------------------------------------------------------------------------------------')
    called_map = bcode_parser.parse_main(codes, addr_map, obj_sets, obj_map)
    # print('==== called map ====')
    # pprint(called_map)
    # print('------------------------------------------------------------------------------------------------------------')
    # print('==== obj map ====')
    # pprint(obj_map)
    # print('------------------------------------------------------------------------------------------------------------')

    user_def_tracking(called_map, obj_map, def_map)