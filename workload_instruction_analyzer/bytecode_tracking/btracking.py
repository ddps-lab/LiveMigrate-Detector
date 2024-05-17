import sys
import importlib

import bcode_parser
import bcode_utils
import func_mapping

# get python builtin modules
from stdlib_list import stdlib_list

import re

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
def create_call_map(byte_code, module):
    print(f'\033[33m======================================== {module} ========================================\033[0m')
    def_map, obj_map, addr_map = {}, {}, {}
    codes, definitions, main_bcode_block_start_offsets, list_def_bcode_block_start_offsets = bcode_utils.preprocessing_bytecode(byte_code)

    # 현재 파싱중인 스크립트에 정의된 객체(함수, 클래스, 메서드)
    obj_sets, user_def_list = bcode_utils.scan_definition(definitions)
    for i in range(len(definitions)):
        key, value = next(iter(user_def_list[i].items()))
        def_map[value + '.' + key] = bcode_parser.parse_def(definitions[i], addr_map, obj_map, list_def_bcode_block_start_offsets[i], module)

    called_map = bcode_parser.parse_main(codes, addr_map, obj_sets, obj_map, main_bcode_block_start_offsets, module)
    pprint(called_map)
    bcode_utils.postprocessing_defmap(def_map, addr_map)
    # print('================ def map ================')
    # pprint(def_map)
    # print('================ called map ================')
    # pprint(called_map)
    # print('================ obj map ================')
    # pprint(obj_map)
    # print('------------------------------------------------------------------------------------------------------------')

    return called_map, obj_sets, def_map, obj_map

def module_tracking(pycaches, base_map):
    # 모듈의 origin name을 확인해 alias를 찾는 함수
    def check_module_origin_name(module):
        for key, value in base_map.items():
            if '__origin_name' in value and value['__origin_name'] == module:
                return key
            # 패키지가 아닌 내부 모듈로 파악된 경우 ex) numpy.core
            elif '__from' in value and value['__from'] + '.' + value['__origin_name'] == module:
                return key

    new_called_map = {'__builtin':set(), '__user_def':set()}

    for module, path in pycaches.items():
        if path == '__builtin' or path == '__not_pymodule':
            continue

        byte_code = bcode_utils.read_pyc(path)
        called_map, obj_sets, def_map, obj_map = create_call_map(byte_code, module)

        module = check_module_origin_name(module)
        # 현재 모듈에서 트래킹할 함수 - 다른 모듈에서 호출된 현재 모듈의 함수
        called_func = base_map[module]['__called']
        
        print(f'\033[33mcalled func : {called_func}\033[0m')
        print(f'\033[33muser def : {obj_sets}\033[0m')

        # 해당 모듈에서 트래킹할 함수의 원본 이름을 확인해 해당 모듈의 사용자 정의 함수라면 __user_def에 추가
        # FIXME: 해당 모듈A 에서 트래킹할 함수는 모듈 A가 모듈 B로부터 import 한 것이라면?
        for func in called_func:
            origin_name = func
            if '__func_alias' in base_map[module]:
                origin_name = base_map[module]['__func_alias'][func]
            if origin_name in obj_sets:
                called_map['__user_def'].add(origin_name)
        pprint(called_map)

        while(True):
            new_tracked = user_def_tracking(called_map, obj_map, def_map, obj_sets)
            if bcode_utils.dict_empty_check(new_tracked):
                break
            called_map = bcode_utils.merge_dictionaries(called_map, new_tracked)

        new_called_map = bcode_utils.merge_dictionaries(new_called_map, called_map)
        print(f'\033[35m==== new called map ====\033[0m')
        pprint(new_called_map)

    return new_called_map

def search_module_path(called_map, pycaches):
    modules = {
        module_info['__origin_name']: module_info.get('__from', None)
        for _, module_info in called_map.items()
        if '__origin_name' in module_info
    }

    for __origin_name, __from in modules.items():
        try:
            if is_builtin_module(__origin_name):
                pycaches[__origin_name] = '__builtin'
                continue
            loaded_module = importlib.import_module(__origin_name)
            module_path = loaded_module.__cached__
            pycaches[__origin_name] = module_path

        except AttributeError:
            # if is_builtin_module(module):
            #     pycaches[module] = '__builtin'
            # else:
            #     pycaches[module] = '__not_pymodule'
            pycaches[__origin_name] = '__not_pymodule'
        except ModuleNotFoundError:
            try:
                # __from이 None이면 단순 import된 모듈
                # builtin 모듈이 아니면서 ModuleNotFoundError가 발생했다는건 C 모듈
                if __from == None:
                    pycaches[__origin_name] = '__not_pymodule'
                    continue

                module = __from + '.' + __origin_name
                loaded_module = importlib.import_module(module)
                module_path = loaded_module.__cached__
                pycaches[module] = module_path
            except ModuleNotFoundError:
                pycaches[module] = '__not_pymodule'
            except AttributeError:
                if is_builtin_module(module):
                    pycaches[module] = '__builtin'
                else:
                    pycaches[module] = '__not_pymodule'
    
    print(f'\033[31m==== pycaches ====\033[0m')
    pprint(pycaches)

def extract_c_func(modules_info, called_map):
    not_pymodule_keys = []
    not_pymodules = {}

    for key, value in modules_info.items():
        if value == '__not_pymodule':
            not_pymodule_keys.append(key)

    # 경로 등을 제거해 모듈 이름만 파싱
    for module in not_pymodule_keys:
        if '.' in module:
            key = module.split('.')[-1]
        else:
            key = module

        if key == 'so':
            key = module.split('.')[-2]
            key = re.sub(r'[^A-Za-z]', '', key)

        not_pymodules[key] = called_map[key]['__called']
    
    return not_pymodules

if __name__ == '__main__':
    LIBRARIES = stdlib_list("3.10")

    pycaches = {}
    modules_info = {}

    script_path = '/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking/example_scripts'
    if script_path not in sys.path:
        sys.path.append(script_path)

    # script_path += '/branch.py'
    # script_path += '/import_test.py'
    # script_path += '/comprehension.py'
    script_path += '/main.py'
    # script_path = '/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking/test.py'
    with open(script_path, 'r') as f:
        source_code = f.read()

    byte_code = compile(source_code, '<string>', 'exec')

    called_map, obj_sets, def_map, obj_map = create_call_map(byte_code, 'main')
    search_module_path(called_map, pycaches)
    modules_info = pycaches | modules_info

    while(True):
        new_tracked = user_def_tracking(called_map, obj_map, def_map, obj_sets)
        if bcode_utils.dict_empty_check(new_tracked):
            break
        called_map = bcode_utils.merge_dictionaries(called_map, new_tracked)
    print(f'\033[31m==== main tracking ====\033[0m')
    pprint(called_map)
    

    new_called_map = module_tracking(pycaches, called_map)
    # exit()
    while(True):
        next_tracking = bcode_utils.find_unique_keys_values(called_map, new_called_map)
        called_map = bcode_utils.merge_dictionaries(called_map, new_called_map)

        if next_tracking:
            print(f'\033[31m==== next tracking ====\033[0m')
            pprint(next_tracking)
        else:
            break
        
        pycaches = {}
        search_module_path(next_tracking, pycaches)
        modules_info = pycaches | modules_info
        new_called_map = module_tracking(pycaches, new_called_map)

    print(f'\033[31m==== end ====\033[0m')
    pprint(called_map)
    print(f'\033[31m==== modules ====\033[0m')
    pprint(modules_info)

    not_pymodules = extract_c_func(modules_info, called_map)

    print(f'\033[31m==== c modules ====\033[0m')
    pprint(not_pymodules)

    func_mapping.check_PyDefMethods(not_pymodules)