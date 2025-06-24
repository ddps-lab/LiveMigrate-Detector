import sys
import importlib
import time

import bcode_parser
import bcode_utils
import func_mapping

# get python builtin modules
from stdlib_list import stdlib_list

print("=== DEBUG: btracking.py imported ===")

LIBRARIES = stdlib_list("3.10")
print(f"=== DEBUG: Loaded {len(LIBRARIES)} standard library modules ===")


def is_builtin_module(module_name):
    global LIBRARIES

    if '.' in module_name:
        module_name = module_name.split('.')[0]

    is_builtin = module_name in LIBRARIES
    print(
        f"=== DEBUG: Module '{module_name}' is {'builtin' if is_builtin else 'external'} ===")
    return is_builtin

# 너비탐색으로 진행.


def user_def_tracking(called_map, obj_map, def_map):
    '''
    현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
    '''
    print(
        f"=== DEBUG: Starting user_def_tracking, called_map has {len(called_map)} entries ===")

    if called_map['__user_def'] == None:
        print("=== DEBUG: No user-defined functions to track ===")
        return

    obj_sets = set(def_map.keys())
    print(f"=== DEBUG: Found {len(obj_sets)} defined objects ===")

    # 새로 추적된 함수들을 저장할 곳.
    new_tracked = {'__builtin': set(), '__user_def': set()}
    for key in called_map.keys():
        if key == '__builtin' or key == '__user_def':
            continue
        new_tracked[key] = {'__called': set()}

    tracked_count = 0
    for obj in called_map['__user_def']:
        if obj in def_map:
            chain = def_map[obj]
            print(
                f"=== DEBUG: Processing user-defined object '{obj}' with {len(chain)} functions ===")
        else:
            continue

        for func in chain:
            category = bcode_parser.func_classification(
                func, called_map, obj_sets, obj_map)

            if category == '__builtin' or category == '__user_def':
                if func not in called_map[category]:
                    new_tracked[category].add(func)
                    tracked_count += 1
            elif func not in called_map[category]:
                func = func.replace(f'{category}.', '')
                if func not in called_map[category]['__called']:
                    new_tracked[category]['__called'].add(func)
                    tracked_count += 1

    print(
        f"=== DEBUG: user_def_tracking found {tracked_count} new functions to track ===")
    return new_tracked


debug_modules = {}


def create_call_map(byte_code, module):
    print(f"=== DEBUG: Creating call map for module: {module} ===")

    if module in debug_modules:
        debug_modules[module] += 0
    else:
        debug_modules[module] = 1

    def_map, obj_map, addr_map = {}, {}, {}

    try:
        codes, definitions, main_bcode_block_start_offsets, list_def_bcode_block_start_offsets = bcode_utils.preprocessing_bytecode(
            byte_code)
        print(
            f"=== DEBUG: Preprocessed bytecode - {len(codes)} main codes, {len(definitions)} definitions ===")
    except Exception as e:
        print(
            f"=== ERROR: Failed to preprocess bytecode for {module}: {e} ===")
        return {}, {}, {}, {}

    # 현재 파싱중인 스크립트에 정의된 객체(함수, 클래스, 메서드)
    try:
        obj_sets, user_def_list = bcode_utils.scan_definition(definitions)
        print(f"=== DEBUG: Found {len(obj_sets)} user-defined objects ===")

        for i in range(len(definitions)):
            key, value = next(iter(user_def_list[i].items()))
            def_map[value + '.' + key] = bcode_parser.parse_def(
                definitions[i], addr_map, obj_map, list_def_bcode_block_start_offsets[i], module)
            print(
                f"=== DEBUG: Parsed definition {i+1}/{len(definitions)}: {value}.{key} ===")
    except Exception as e:
        print(f"=== ERROR: Failed to scan definitions for {module}: {e} ===")

    try:
        called_map, decorator_map = bcode_parser.parse_main(
            codes, addr_map, obj_sets, obj_map, main_bcode_block_start_offsets, module)
        print(
            f"=== DEBUG: Parsed main code, found {len(called_map)} called modules ===")
    except Exception as e:
        print(f"=== ERROR: Failed to parse main code for {module}: {e} ===")
        called_map, decorator_map = {}, {}

    try:
        bcode_utils.postprocessing_defmap(def_map, addr_map)
        print(f"=== DEBUG: Postprocessed definition map ===")
    except Exception as e:
        print(
            f"=== ERROR: Failed to postprocess definition map for {module}: {e} ===")

    return called_map, def_map, obj_map, decorator_map


def module_tracking(pycaches, base_map, C_functions_with_decorators, called_func):
    print(
        f"=== DEBUG: Starting module tracking with {len(pycaches)} cached modules ===")

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

    processed_modules = 0
    for module, path in pycaches.items():
        processed_modules += 1
        print(
            f"=== DEBUG: Processing module {processed_modules}/{len(pycaches)}: {module} ===")

        if path in no_tracking:
            print(
                f"=== DEBUG: Skipping module {module} (category: {path}) ===")
            continue

        try:
            byte_code = bcode_utils.read_pyc(path)
            print(f"=== DEBUG: Read bytecode from {path} ===")
        except Exception as e:
            print(f"=== ERROR: Failed to read bytecode from {path}: {e} ===")
            continue

        try:
            called_map, def_map, obj_map, decorator_map = create_call_map(
                byte_code, module)
        except Exception as e:
            print(
                f"=== ERROR: Failed to create call map for {module}: {e} ===")
            continue

        key = module.split('.')[0]
        alias = check_module_alias(module)
        print(
            f"=== DEBUG: Module alias check - key: {key}, alias: {alias} ===")

        # 현재 모듈에서 트래킹할 함수 - 다른 모듈에서 호출된 현재 모듈의 함수
        called_func.setdefault(key, set())
        # alias가 None이 아닌 경우에만 base_map에서 정보를 가져옴
        if alias is not None and alias in base_map:
            called_func[key].update(base_map[alias]['__called'])
            print(
                f"=== DEBUG: Updated called_func for {key} with {len(base_map[alias]['__called'])} functions ===")

        # 해당 모듈에서 트래킹할 함수의 원본 이름을 확인해 해당 모듈의 사용자 정의 함수라면 __user_def에 추가
        decorator_count = 0
        for func in called_func[key]:
            origin_name = func

            if func in decorator_map:
                decorator_count += 1
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

        if decorator_count > 0:
            print(
                f"=== DEBUG: Found {decorator_count} functions with decorators in {module} ===")

        # 현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
        tracking_iterations = 0
        while (True):
            tracking_iterations += 1
            new_tracked = user_def_tracking(called_map, obj_map, def_map)
            if bcode_utils.dict_empty_check(new_tracked):
                break
            called_map = bcode_utils.merge_dictionaries(
                called_map, new_tracked)
            if tracking_iterations > 100:  # Prevent infinite loops
                print(
                    f"=== WARNING: Too many tracking iterations for {module}, breaking ===")
                break

        print(
            f"=== DEBUG: Completed {tracking_iterations} tracking iterations for {module} ===")
        new_called_map = bcode_utils.merge_dictionaries(
            new_called_map, called_map)

    print(
        f"=== DEBUG: Module tracking completed, processed {processed_modules} modules ===")
    return new_called_map


def search_module_path(called_map, pycaches):
    print(
        f"=== DEBUG: Searching module paths for {len(called_map)} called modules ===")

    # __origin_name 값을 추출하여 리스트로 변환
    origin_names = list({
        module_info['__origin_name']
        for module_info in called_map.values()
        if '__origin_name' in module_info
    })

    print(f"=== DEBUG: Found {len(origin_names)} unique origin names ===")

    for __origin_name in origin_names:
        print(f"=== DEBUG: Processing origin name: {__origin_name} ===")

        if is_builtin_module(__origin_name):
            pycaches[__origin_name] = '__builtin'
            continue

        try:
            if __origin_name in sys.modules:
                loaded_module = sys.modules[__origin_name]
                print(
                    f"=== DEBUG: Module {__origin_name} already loaded in sys.modules ===")
            else:
                loaded_module = importlib.import_module(__origin_name)
                print(f"=== DEBUG: Imported module {__origin_name} ===")

            module_path = loaded_module.__cached__
            pycaches[__origin_name] = module_path
            print(
                f"=== DEBUG: Module path for {__origin_name}: {module_path} ===")
        except AttributeError:
            # 가상 모듈 구분
            if not loaded_module.__spec__.origin:
                pycaches[__origin_name] = '__virtual_pymodule'
                print(f"=== DEBUG: {__origin_name} is a virtual module ===")
            else:
                pycaches[__origin_name] = '__not_pymodule'
                print(f"=== DEBUG: {__origin_name} is not a Python module ===")
        # 런타임에 import되지 않는 모듈이 존재하며 해당 모듈은 시스템에 설치되지 않았을 수 있음.
        except ModuleNotFoundError:
            # ctypes로 로드되는 모듈의 경우 importlib로 import할 수 없음.
            if __origin_name.endswith('.so'):
                pycaches[__origin_name] = '__not_pymodule'
                print(f"=== DEBUG: {__origin_name} is a .so module ===")
            else:
                pycaches[__origin_name] = '__ModuleNotFoundError'
                print(f"=== DEBUG: {__origin_name} not found ===")


def extract_c_func(modules_info, called_map):
    print(
        f"=== DEBUG: Extracting C functions from {len(called_map)} modules ===")

    del called_map['__builtin']
    del called_map['__user_def']
    not_pymodules = {value['__origin_name']: value['__called']
                     for _, value in called_map.items() if value['__called']}

    print(
        f"=== DEBUG: Found {len(not_pymodules)} modules with called functions ===")

    for module, category in modules_info.items():
        if not category == '__not_pymodule':
            # FIXME: 서로 다른 모듈에 대해 같은 alias를 사용하면 문제가 생김
            # 기존의 called_map이 덮어씌어져서 modules_info에는 특정 모듈에 대한 정보가 있지만 called_map에는 없음
            # 그 때문에 del을 사용하면 에러가 발생하여 임시로 pop으로 처리함.
            not_pymodules.pop(module, None)

    print(
        f"=== DEBUG: After filtering, {len(not_pymodules)} non-Python modules remain ===")
    return not_pymodules


def entry_tracking(pycaches, modules_info, SCRIPT_PATH):
    print(f"=== DEBUG: Starting entry tracking for script: {SCRIPT_PATH} ===")

    if SCRIPT_PATH not in sys.path:
        sys.path.append(SCRIPT_PATH)
        print(f"=== DEBUG: Added {SCRIPT_PATH} to sys.path ===")

    try:
        with open(SCRIPT_PATH, 'r') as f:
            source_code = f.read()
        print(
            f"=== DEBUG: Read source code, length: {len(source_code)} characters ===")
    except Exception as e:
        print(f"=== ERROR: Failed to read script {SCRIPT_PATH}: {e} ===")
        return {}, {}, {}

    try:
        byte_code = compile(source_code, '<string>', 'exec')
        print(f"=== DEBUG: Compiled source code to bytecode ===")
    except Exception as e:
        print(f"=== ERROR: Failed to compile script {SCRIPT_PATH}: {e} ===")
        return {}, {}, {}

    try:
        called_map, def_map, obj_map, _ = create_call_map(byte_code, 'main')
        print(f"=== DEBUG: Created call map for entry script ===")
    except Exception as e:
        print(
            f"=== ERROR: Failed to create call map for entry script: {e} ===")
        return {}, {}, {}

    try:
        search_module_path(called_map, pycaches)
        modules_info = pycaches | modules_info
        print(
            f"=== DEBUG: Searched module paths, total modules: {len(modules_info)} ===")
    except Exception as e:
        print(f"=== ERROR: Failed to search module paths: {e} ===")

    # 현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
    tracking_iterations = 0
    while (True):
        tracking_iterations += 1
        new_tracked = user_def_tracking(called_map, obj_map, def_map)
        if bcode_utils.dict_empty_check(new_tracked):
            break
        called_map = bcode_utils.merge_dictionaries(called_map, new_tracked)
        if tracking_iterations > 100:  # Prevent infinite loops
            print(
                f"=== WARNING: Too many tracking iterations in entry tracking, breaking ===")
            break

    print(
        f"=== DEBUG: Entry tracking completed with {tracking_iterations} iterations ===")
    return called_map, pycaches, modules_info


def main(SCRIPT_PATH):
    print(f"=== DEBUG: Starting btracking main for script: {SCRIPT_PATH} ===")
    addr_collect_start_time = time.time()

    pycaches = {}
    modules_info = {}
    C_functions_with_decorators = {}
    called_func = {}

    try:
        called_map, pycaches, modules_info = entry_tracking(
            pycaches, modules_info, SCRIPT_PATH)
        print(f"=== DEBUG: Entry tracking completed ===")
    except Exception as e:
        print(f"=== ERROR: Entry tracking failed: {e} ===")
        import traceback
        traceback.print_exc()
        return set(), 0, 0

    try:
        new_called_map = module_tracking(
            pycaches, called_map, C_functions_with_decorators, called_func)
        print(f"=== DEBUG: Initial module tracking completed ===")
    except Exception as e:
        print(f"=== ERROR: Module tracking failed: {e} ===")
        import traceback
        traceback.print_exc()
        return set(), 0, 0

    tracking_rounds = 0
    while (True):
        tracking_rounds += 1
        print(f"=== DEBUG: Starting tracking round {tracking_rounds} ===")

        next_tracking = bcode_utils.find_unique_keys_values(
            called_map, new_called_map)

        if not next_tracking:
            print(
                f"=== DEBUG: No new modules to track, stopping after {tracking_rounds} rounds ===")
            break

        # next_tracking[key][__called] 값이 called_map의 __called 값에 포함되는 항목을 next_tracking에서 제거
        keys_to_remove = [
            key for key in next_tracking
            if key in called_map and called_map[key]['__called'].issuperset(next_tracking[key]['__called'])
        ]
        for key in keys_to_remove:
            del next_tracking[key]

        print(
            f"=== DEBUG: Round {tracking_rounds}: Found {len(next_tracking)} new modules to track ===")

        pycaches = {}
        try:
            search_module_path(next_tracking, pycaches)
            modules_info = pycaches | modules_info
            print(
                f"=== DEBUG: Updated module info, total modules: {len(modules_info)} ===")
        except Exception as e:
            print(
                f"=== ERROR: Failed to search module paths in round {tracking_rounds}: {e} ===")

        if next_tracking:
            called_map = bcode_utils.merge_dictionaries(
                called_map, new_called_map)
            try:
                new_called_map = module_tracking(
                    pycaches, next_tracking, C_functions_with_decorators, called_func)
                print(
                    f"=== DEBUG: Round {tracking_rounds} module tracking completed ===")
            except Exception as e:
                print(
                    f"=== ERROR: Module tracking failed in round {tracking_rounds}: {e} ===")
                break
        else:
            break

        if tracking_rounds > 10:  # Prevent infinite loops
            print(
                f"=== WARNING: Too many tracking rounds, stopping at {tracking_rounds} ===")
            break

    try:
        not_pymodules = extract_c_func(modules_info, called_map)
        print(
            f"=== DEBUG: Extracted {len(not_pymodules)} non-Python modules ===")
    except Exception as e:
        print(f"=== ERROR: Failed to extract C functions: {e} ===")
        not_pymodules = {}

    try:
        C_functions1 = func_mapping.check_PyMethodDef(not_pymodules)
        print(
            f"=== DEBUG: Found {len(C_functions1)} C functions from PyMethodDef ===")
    except Exception as e:
        print(
            f"=== ERROR: Failed to check PyMethodDef for not_pymodules: {e} ===")
        C_functions1 = {}

    try:
        C_functions2 = func_mapping.check_PyMethodDef(
            C_functions_with_decorators)
        print(
            f"=== DEBUG: Found {len(C_functions2)} C functions from decorators ===")
    except Exception as e:
        print(
            f"=== ERROR: Failed to check PyMethodDef for decorators: {e} ===")
        C_functions2 = {}

    C_functions = C_functions1 | C_functions2

    # C_functions = C_functions1

    set_c_functions = set()

    for _, addr in C_functions.items():
        set_c_functions.add(addr)

    addr_collect_end_time = time.time()
    addr_collect_time = addr_collect_end_time - addr_collect_start_time
    module_count = len(modules_info)

    print(f"=== DEBUG: btracking main completed ===")
    print(f"=== DEBUG: Total C functions found: {len(set_c_functions)} ===")
    print(f"=== DEBUG: Total modules processed: {module_count} ===")
    print(
        f"=== DEBUG: Address collection time: {addr_collect_time:.6f} sec ===")

    return set_c_functions, addr_collect_time, module_count
