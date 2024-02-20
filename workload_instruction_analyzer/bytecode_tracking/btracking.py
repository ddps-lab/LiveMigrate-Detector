import sys
import importlib

import bcode_parser
import bcode_utils

# get python builtin modules
from stdlib_list import stdlib_list

# temp
from pprint import pprint

def is_builtin_module(module_name):
    global LIBRARIES

    if '.' in module_name:
        module_name = module_name.split('.')[0]

    if module_name in LIBRARIES:
        return True
    else:
        return False

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
def user_def_tracking(called_map, obj_map, def_map, obj_sets):
    '''
    userdef 객체에서 호출되는 함수를 트래킹.
    '''
    # 새로 추적된 함수들을 저장할 곳.
    new_tracked = {'__builtin':set(), '__user_def':set()}
    for key in called_map.keys():
        if key == '__builtin' or key == '__user_def':
            continue
        new_tracked[key] = {'__called':set()}

    if called_map['__user_def'] == None:
        return
    
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
    
    print(f'\033[31m==== new tracked - user_def_tracking ====\033[0m')
    pprint(new_tracked)
    return new_tracked

# FIXME: module이름은 출력용이므로 추후 제거
def create_call_map(def_map, addr_map, obj_map, byte_code, module):
    codes, definitions = bcode_utils.preprocessing_bytecode(byte_code)

    # 현재 파싱중인 스크립트에 정의된 객체(함수, 클래스, 메서드)
    obj_sets, user_def_list = bcode_utils.parse_definition(definitions)
    for i in range(len(definitions)):
        key, value = next(iter(user_def_list[i].items()))
        def_map[value + '.' + key] = bcode_parser.parse_def(definitions[i], addr_map, obj_sets, obj_map)

    # print('------------------------------------------------------------------------------------------------------------')
    print(f'\033[33m==== {module} ====\033[0m')
    bcode_utils.postprocessing_defmap(def_map, addr_map)
    # print('==== def map ====')
    # pprint(def_map)
    # print('------------------------------------------------------------------------------------------------------------')
    called_map = bcode_parser.parse_main(codes, addr_map, obj_sets, obj_map)
    # print('==== called map ====')
    pprint(called_map)
    # print('------------------------------------------------------------------------------------------------------------')
    # print('==== obj map ====')
    # pprint(obj_map)
    # print('------------------------------------------------------------------------------------------------------------')

    return called_map, obj_sets

def module_tracking(pycaches):
    def_map = {}
    addr_map = {}
    obj_map = {}

    for module, path in pycaches.items():
        if path == '__builtin' or path == '__not_pymodule':
            continue

        byte_code = bcode_utils.read_pyc(path)
        called_map, obj_sets = create_call_map(def_map, addr_map, obj_map, byte_code, module)
        new_tracked = user_def_tracking(called_map, obj_map, def_map, obj_sets)

        # FIXME: tracked_map에서 호출된 현재 모듈의 함수를 new_tracked에 추가해야함.
        break

def search_module_path(called_map, pycaches):
    modules = [module_info['__origin_name'] for _, module_info in called_map.items() if '__origin_name' in module_info]

    for module in modules:
        try:
            loaded_module = importlib.import_module(module)
            pycaches[module] = loaded_module.__cached__
        except AttributeError:
            if is_builtin_module(module):
                pycaches[module] = '__builtin'
            else:
                pycaches[module] = '__not_pymodule'
        except ModuleNotFoundError:
            # FIXME: C모듈이라 못찾는건지 경로때문에 못찾는건지?
            pycaches[module] = '__not_pymodule'
    
    print(f'\033[31m==== pycaches ====\033[0m')
    pprint(pycaches)

if __name__ == '__main__':
    LIBRARIES = stdlib_list("3.10")

    # called_map = {}
    def_map = {}
    addr_map = {}
    obj_map = {}
    pycaches = {}

    script_path = '/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking/example_scripts'
    if script_path not in sys.path:
        sys.path.append(script_path)

    script_path += '/main.py'
    # script_path += '/testpymodule.py'
    with open(script_path, 'r') as f:
        source_code = f.read()

    byte_code = compile(source_code, '<string>', 'exec')

    called_map, obj_sets = create_call_map(def_map, addr_map, obj_map, byte_code, 'main')

    search_module_path(called_map, pycaches)
    new_tracked = user_def_tracking(called_map, obj_map, def_map, obj_sets)

    module_tracking(pycaches)