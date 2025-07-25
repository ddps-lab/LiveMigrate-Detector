import sys
import importlib
import time

import bcode_parser
import bcode_utils

# get python builtin modules
from stdlib_list import stdlib_list

LIBRARIES = stdlib_list("3.10")


def is_builtin_module(module_name):
    global LIBRARIES

    if '.' in module_name:
        module_name = module_name.split('.')[0]

    if module_name in LIBRARIES:
        return True
    else:
        return False

# 너비탐색으로 진행.


def user_def_tracking(called_map, obj_map, def_map):
    '''
    현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
    '''
    if called_map['__user_def'] == None:
        return

    obj_sets = set(def_map.keys())

    # 새로 추적된 함수들을 저장할 곳.
    new_tracked = {'__builtin': set(), '__user_def': set()}
    for key in called_map.keys():
        if key == '__builtin' or key == '__user_def':
            continue
        new_tracked[key] = {'__called': set()}

    for obj in called_map['__user_def']:
        if obj in def_map:
            chain = def_map[obj]
        else:
            continue

        for func in chain:
            category = bcode_parser.func_classification(
                func, called_map, obj_sets, obj_map)

            if category == '__builtin' or category == '__user_def':
                if func not in called_map[category]:
                    new_tracked[category].add(func)
            elif func not in called_map[category]:
                func = func.replace(f'{category}.', '')
                if func not in called_map[category]['__called']:
                    new_tracked[category]['__called'].add(func)

    return new_tracked


debug_modules = {}


def create_call_map(byte_code, module):
    if module in debug_modules:
        debug_modules[module] += 0
    else:
        debug_modules[module] = 1

    def_map, obj_map, addr_map = {}, {}, {}
    codes, definitions, main_bcode_block_start_offsets, list_def_bcode_block_start_offsets = bcode_utils.preprocessing_bytecode(
        byte_code)

    # 현재 파싱중인 스크립트에 정의된 객체(함수, 클래스, 메서드)
    obj_sets, user_def_list = bcode_utils.scan_definition(definitions)
    for i in range(len(definitions)):
        key, value = next(iter(user_def_list[i].items()))
        def_map[value + '.' + key] = bcode_parser.parse_def(
            definitions[i], addr_map, obj_map, list_def_bcode_block_start_offsets[i], module)

    called_map, decorator_map = bcode_parser.parse_main(
        codes, addr_map, obj_sets, obj_map, main_bcode_block_start_offsets, module)
    bcode_utils.postprocessing_defmap(def_map, addr_map)

    return called_map, def_map, obj_map, decorator_map


def module_tracking(pycaches, base_map, C_functions_with_decorators, called_func):
    # 모듈의 origin name을 확인해 alias를 찾는 함수
    def check_module_alias(module):
        for key, value in base_map.items():
            if '__origin_name' in value and value['__origin_name'] == module:
                return key
            # 패키지가 아닌 내부 모듈로 파악된 경우 ex) numpy.core
            elif '__from' in value and value['__from'] + '.' + value['__origin_name'] == module:
                return key

    new_called_map = {'__builtin': set(), '__user_def': set()}

    no_tracking = {'__builtin', '__not_pymodule',
                   '__virtual_pymodule', '__ModuleNotFoundError'}
    for module, path in pycaches.items():
        if path in no_tracking:
            continue

        byte_code = bcode_utils.read_pyc(path)
        called_map, def_map, obj_map, decorator_map = create_call_map(
            byte_code, module)
        key = module.split('.')[0]
        alias = check_module_alias(module)
        # 현재 모듈에서 트래킹할 함수 - 다른 모듈에서 호출된 현재 모듈의 함수
        called_func.setdefault(key, set())
        # alias가 None이 아닌 경우에만 base_map에서 정보를 가져옴
        if alias is not None and alias in base_map:
            called_func[key].update(base_map[alias]['__called'])

        # 해당 모듈에서 트래킹할 함수의 원본 이름을 확인해 해당 모듈의 사용자 정의 함수라면 __user_def에 추가
        for func in called_func[key]:
            origin_name = func

            if func in decorator_map:
                # FIXME: 데코레이터 사용에서 .이 없을 수도 있을듯?
                if '.' in decorator_map[func]:
                    c_module = decorator_map[func].split('.')[0]
                    c_func = decorator_map[func].split('.')[1]

                    C_functions_with_decorators.setdefault(c_module, set())
                    C_functions_with_decorators[c_module].add(c_func)

            module_base = module.split('.')[0]
            for key in base_map.keys():
                # key가 None이 아닌 경우에만 확인
                if key is not None and module_base in key:
                    if '__func_alias' in base_map[key] and func in base_map[key]['__func_alias']:
                        origin_name = base_map[key]['__func_alias'][func]

            if origin_name in def_map:
                called_map['__user_def'].add(origin_name)

        # 현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
        while (True):
            new_tracked = user_def_tracking(called_map, obj_map, def_map)
            if bcode_utils.dict_empty_check(new_tracked):
                break
            called_map = bcode_utils.merge_dictionaries(
                called_map, new_tracked)
        new_called_map = bcode_utils.merge_dictionaries(
            new_called_map, called_map)

    return new_called_map


def search_module_path(called_map, pycaches):
    # __origin_name 값을 추출하여 리스트로 변환
    origin_names = list({
        module_info['__origin_name']
        for module_info in called_map.values()
        if '__origin_name' in module_info
    })

    for __origin_name in origin_names:
        if is_builtin_module(__origin_name):
            pycaches[__origin_name] = '__builtin'
            continue

        try:
            if __origin_name in sys.modules:
                loaded_module = sys.modules[__origin_name]
            else:
                loaded_module = importlib.import_module(__origin_name)

            module_path = loaded_module.__cached__
            pycaches[__origin_name] = module_path
        except AttributeError:
            # 가상 모듈 구분
            if not loaded_module.__spec__.origin:
                pycaches[__origin_name] = '__virtual_pymodule'
            else:
                pycaches[__origin_name] = '__not_pymodule'
        # 런타임에 import되지 않는 모듈이 존재하며 해당 모듈은 시스템에 설치되지 않았을 수 있음.
        except ModuleNotFoundError:
            # ctypes로 로드되는 모듈의 경우 importlib로 import할 수 없음.
            if __origin_name.endswith('.so'):
                pycaches[__origin_name] = '__not_pymodule'
            else:
                pycaches[__origin_name] = '__ModuleNotFoundError'


def extract_c_func(modules_info, called_map):
    del called_map['__builtin']
    del called_map['__user_def']
    not_pymodules = {value['__origin_name']: value['__called']
                     for _, value in called_map.items() if value['__called']}

    for module, category in modules_info.items():
        if not category == '__not_pymodule':
            # FIXME: 서로 다른 모듈에 대해 같은 alias를 사용하면 문제가 생김
            # 기존의 called_map이 덮어씌어져서 modules_info에는 특정 모듈에 대한 정보가 있지만 called_map에는 없음
            # 그 때문에 del을 사용하면 에러가 발생하여 임시로 pop으로 처리함.
            not_pymodules.pop(module, None)

    return not_pymodules


def entry_tracking(pycaches, modules_info, SCRIPT_PATH):
    if SCRIPT_PATH not in sys.path:
        sys.path.append(SCRIPT_PATH)

    with open(SCRIPT_PATH, 'r') as f:
        source_code = f.read()

    byte_code = compile(source_code, '<string>', 'exec')

    called_map, def_map, obj_map, _ = create_call_map(byte_code, 'main')
    search_module_path(called_map, pycaches)
    modules_info = pycaches | modules_info

    # 현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
    while (True):
        new_tracked = user_def_tracking(called_map, obj_map, def_map)
        if bcode_utils.dict_empty_check(new_tracked):
            break
        called_map = bcode_utils.merge_dictionaries(called_map, new_tracked)
    return called_map, pycaches, modules_info


def main(SCRIPT_PATH):
    addr_collect_start_time = time.time()

    pycaches = {}
    modules_info = {}
    C_functions_with_decorators = {}
    called_func = {}

    called_map, pycaches, modules_info = entry_tracking(
        pycaches, modules_info, SCRIPT_PATH)

    new_called_map = module_tracking(
        pycaches, called_map, C_functions_with_decorators, called_func)
    while (True):
        next_tracking = bcode_utils.find_unique_keys_values(
            called_map, new_called_map)

        # next_tracking[key][__called] 값이 called_map의 __called 값에 포함되는 항목을 next_tracking에서 제거
        keys_to_remove = [
            key for key in next_tracking
            if key in called_map and called_map[key]['__called'].issuperset(next_tracking[key]['__called'])
        ]
        for key in keys_to_remove:
            del next_tracking[key]

        pycaches = {}
        search_module_path(next_tracking, pycaches)
        modules_info = pycaches | modules_info

        if next_tracking:
            called_map = bcode_utils.merge_dictionaries(
                called_map, new_called_map)
            new_called_map = module_tracking(
                pycaches, next_tracking, C_functions_with_decorators, called_func)
        else:
            break

    not_pymodules = extract_c_func(modules_info, called_map)

    # C_functions1 = func_mapping.check_PyMethodDef(not_pymodules)
    # C_functions2 = func_mapping.check_PyMethodDef(C_functions_with_decorators)
    # C_functions = C_functions1 | C_functions2

    # # C_functions = C_functions1

    # set_c_functions = set()

    # for _, addr in C_functions.items():
    #     set_c_functions.add(addr)

    addr_collect_end_time = time.time()
    addr_collect_time = addr_collect_end_time - addr_collect_start_time
    module_count = len(modules_info)

    return set_c_functions, addr_collect_time, module_count


if __name__ == '__main__':
    # python3 btracking.py /home/ubuntu/workload_instruction_analyzer/compare/beautifulsoup4/bs4_example.py
    if len(sys.argv) != 2:
        print("Usage: python3 btracking.py <script_path>")
        sys.exit(1)

    script_path = sys.argv[1]

    try:
        c_functions, addr_collect_time, module_count = main(script_path)
        print(f"Script analyzed: {script_path}")
        print(f"Analysis time: {addr_collect_time:.2f} seconds")
        print(f"Modules processed: {module_count}")
        print(f"C functions found: {len(c_functions)}")
        print("\nC function addresses:")
        for addr in sorted(c_functions):
            print(f"  {addr}")
    except Exception as e:
        print(f"Error analyzing script: {e}")
        sys.exit(1)
