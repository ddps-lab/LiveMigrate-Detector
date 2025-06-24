import sys
import importlib
import time

import bcode_parser
import bcode_utils
import func_mapping

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
    print(f"[CREATE_CALL_MAP] Creating call map for module: {module}")

    if module in debug_modules:
        debug_modules[module] += 1
    else:
        debug_modules[module] = 1

    def_map, obj_map, addr_map = {}, {}, {}

    try:
        codes, definitions, main_bcode_block_start_offsets, list_def_bcode_block_start_offsets = bcode_utils.preprocessing_bytecode(
            byte_code)
        print(f"[CREATE_CALL_MAP] Preprocessing completed for {module}")
        print(
            f"[CREATE_CALL_MAP]   Main code blocks: {len(main_bcode_block_start_offsets)}")
        print(f"[CREATE_CALL_MAP]   Definitions: {len(definitions)}")
    except Exception as e:
        print(
            f"[CREATE_CALL_MAP ERROR] Preprocessing failed for {module}: {e}")
        raise

    # 현재 파싱중인 스크립트에 정의된 객체(함수, 클래스, 메서드)
    try:
        obj_sets, user_def_list = bcode_utils.scan_definition(definitions)
        print(
            f"[CREATE_CALL_MAP] Found {len(obj_sets)} user-defined objects in {module}")
    except Exception as e:
        print(
            f"[CREATE_CALL_MAP ERROR] Failed to scan definitions for {module}: {e}")
        raise

    # Process definitions
    failed_definitions = 0
    for i in range(len(definitions)):
        try:
            key, value = next(iter(user_def_list[i].items()))
            def_map[value + '.' + key] = bcode_parser.parse_def(
                definitions[i], addr_map, obj_map, list_def_bcode_block_start_offsets[i], module)
        except Exception as e:
            failed_definitions += 1
            print(
                f"[CREATE_CALL_MAP ERROR] Failed to process definition {i}: {e}")
            continue

    if len(definitions) > 0:
        print(
            f"[CREATE_CALL_MAP] Processed {len(definitions)} definitions ({failed_definitions} failed)")

    try:
        called_map, decorator_map = bcode_parser.parse_main(
            codes, addr_map, obj_sets, obj_map, main_bcode_block_start_offsets, module)
        print(f"[CREATE_CALL_MAP] Parsed main code for {module}")
        print(f"[CREATE_CALL_MAP]   Called objects: {len(called_map)}")
        print(f"[CREATE_CALL_MAP]   Decorators: {len(decorator_map)}")
    except Exception as e:
        print(
            f"[CREATE_CALL_MAP ERROR] Failed to parse main code for {module}: {e}")
        raise

    try:
        bcode_utils.postprocessing_defmap(def_map, addr_map)
        print(f"[CREATE_CALL_MAP] Postprocessing completed for {module}")
    except Exception as e:
        print(
            f"[CREATE_CALL_MAP ERROR] Postprocessing failed for {module}: {e}")

    print(f"[CREATE_CALL_MAP] Call map creation completed for {module}")
    return called_map, def_map, obj_map, decorator_map


def module_tracking(pycaches, base_map, C_functions_with_decorators, called_func):
    print(f"[MODULE_TRACKING] Starting with {len(pycaches)} cached modules")

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
    skipped_modules = 0
    error_modules = 0

    for module, path in pycaches.items():
        processed_modules += 1

        if path in no_tracking:
            skipped_modules += 1
            if path == '__ModuleNotFoundError':
                print(f"[MODULE_TRACKING] Module not found: {module}")
            continue

        try:
            byte_code = bcode_utils.read_pyc(path)
        except Exception as e:
            error_modules += 1
            print(
                f"[MODULE_TRACKING ERROR] Failed to read bytecode for {module}: {e}")
            continue

        try:
            called_map, def_map, obj_map, decorator_map = create_call_map(
                byte_code, module)
        except Exception as e:
            error_modules += 1
            print(
                f"[MODULE_TRACKING ERROR] Failed to create call map for {module}: {e}")
            continue

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
                if '.' in decorator_map[func]:
                    c_module = decorator_map[func].split('.')[0]
                    c_func = decorator_map[func].split('.')[1]

                    C_functions_with_decorators.setdefault(c_module, set())
                    C_functions_with_decorators[c_module].add(c_func)

            module_base = module.split('.')[0]
            for key_base in base_map.keys():
                # key가 None이 아닌 경우에만 확인
                if key_base is not None and module_base in key_base:
                    if '__func_alias' in base_map[key_base] and func in base_map[key_base]['__func_alias']:
                        origin_name = base_map[key_base]['__func_alias'][func]

            if origin_name in def_map:
                called_map['__user_def'].add(origin_name)

        # 현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
        user_def_iterations = 0
        while (True):
            user_def_iterations += 1
            new_tracked = user_def_tracking(called_map, obj_map, def_map)
            if bcode_utils.dict_empty_check(new_tracked):
                break
            called_map = bcode_utils.merge_dictionaries(
                called_map, new_tracked)

            if user_def_iterations > 50:  # Safety valve
                print(
                    f"[MODULE_TRACKING WARNING] Too many user_def iterations for {module}, breaking")
                break

        new_called_map = bcode_utils.merge_dictionaries(
            new_called_map, called_map)

    print(f"[MODULE_TRACKING] Completed:")
    print(f"[MODULE_TRACKING]   Processed: {processed_modules}")
    print(f"[MODULE_TRACKING]   Skipped: {skipped_modules}")
    print(f"[MODULE_TRACKING]   Errors: {error_modules}")
    print(f"[MODULE_TRACKING]   Result size: {len(new_called_map)}")

    return new_called_map


def search_module_path(called_map, pycaches):
    print(
        f"[SEARCH_MODULE_PATH] Starting search for {len(called_map)} modules")

    # __origin_name 값을 추출하여 리스트로 변환
    origin_names = list({
        module_info['__origin_name']
        for module_info in called_map.values()
        if '__origin_name' in module_info
    })

    print(
        f"[SEARCH_MODULE_PATH] Found {len(origin_names)} unique origin names to process")

    builtin_count = 0
    not_found_count = 0
    error_count = 0
    cached_count = 0

    for __origin_name in origin_names:

        if is_builtin_module(__origin_name):
            pycaches[__origin_name] = '__builtin'
            builtin_count += 1
            continue

        try:
            if __origin_name in sys.modules:
                loaded_module = sys.modules[__origin_name]
            else:
                loaded_module = importlib.import_module(__origin_name)

            module_path = loaded_module.__cached__
            if module_path:
                pycaches[__origin_name] = module_path
                cached_count += 1

        except AttributeError as e:
            # 가상 모듈 구분
            try:
                if not loaded_module.__spec__.origin:
                    pycaches[__origin_name] = '__virtual_pymodule'
                else:
                    pycaches[__origin_name] = '__not_pymodule'
            except Exception as inner_e:
                pycaches[__origin_name] = '__not_pymodule'
                error_count += 1

        # 런타임에 import되지 않는 모듈이 존재하며 해당 모듈은 시스템에 설치되지 않았을 수 있음.
        except ModuleNotFoundError as e:
            # ctypes로 로드되는 모듈의 경우 importlib로 import할 수 없음.
            if __origin_name.endswith('.so'):
                pycaches[__origin_name] = '__not_pymodule'
            else:
                pycaches[__origin_name] = '__ModuleNotFoundError'
                not_found_count += 1
                if not_found_count <= 5:  # Show first few missing modules
                    print(
                        f"[SEARCH_MODULE_PATH] Module not found: {__origin_name}")
        except Exception as e:
            pycaches[__origin_name] = '__ModuleNotFoundError'
            error_count += 1

    print(f"[SEARCH_MODULE_PATH] Completed. Results:")
    print(f"[SEARCH_MODULE_PATH]   Builtin: {builtin_count}")
    print(f"[SEARCH_MODULE_PATH]   Cached: {cached_count}")
    print(f"[SEARCH_MODULE_PATH]   Not found: {not_found_count}")
    print(f"[SEARCH_MODULE_PATH]   Errors: {error_count}")
    print(f"[SEARCH_MODULE_PATH]   Total: {len(pycaches)}")


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
    print(
        f"[ENTRY_TRACKING] Starting entry tracking for script: {SCRIPT_PATH}")

    if SCRIPT_PATH not in sys.path:
        sys.path.append(SCRIPT_PATH)
        print(f"[ENTRY_TRACKING] Added {SCRIPT_PATH} to sys.path")

    try:
        with open(SCRIPT_PATH, 'r') as f:
            source_code = f.read()
        print(
            f"[ENTRY_TRACKING] Successfully read source code ({len(source_code)} characters)")
    except Exception as e:
        print(f"[ENTRY_TRACKING ERROR] Failed to read script: {e}")
        raise

    try:
        byte_code = compile(source_code, '<string>', 'exec')
        print(f"[ENTRY_TRACKING] Successfully compiled source code to bytecode")
    except Exception as e:
        print(f"[ENTRY_TRACKING ERROR] Failed to compile source code: {e}")
        raise

    try:
        called_map, def_map, obj_map, _ = create_call_map(byte_code, 'main')
        print(
            f"[ENTRY_TRACKING] Created call map with {len(called_map)} called objects")
        for key, value in called_map.items():
            if isinstance(value, set):
                print(f"[ENTRY_TRACKING]   {key}: {len(value)} items")
            elif isinstance(value, dict) and '__called' in value:
                print(
                    f"[ENTRY_TRACKING]   {key}: {len(value['__called'])} called items")
    except Exception as e:
        print(f"[ENTRY_TRACKING ERROR] Failed to create call map: {e}")
        raise

    print(f"[ENTRY_TRACKING] Searching module paths...")
    search_module_path(called_map, pycaches)
    modules_info = pycaches | modules_info
    print(f"[ENTRY_TRACKING] Found {len(modules_info)} total modules")

    # 현재 모듈에서 정의된 함수가 호출됐다면 해당 함수가 호출하는 함수를 트래킹.
    user_def_iterations = 0
    while (True):
        user_def_iterations += 1
        new_tracked = user_def_tracking(called_map, obj_map, def_map)
        if bcode_utils.dict_empty_check(new_tracked):
            break
        called_map = bcode_utils.merge_dictionaries(called_map, new_tracked)

        if user_def_iterations > 50:  # Safety valve
            print(f"[ENTRY_TRACKING WARNING] Too many user_def iterations, breaking")
            break

    if user_def_iterations > 1:
        print(
            f"[ENTRY_TRACKING] User-defined tracking took {user_def_iterations} iterations")

    print(f"[ENTRY_TRACKING] Entry tracking completed successfully")
    return called_map, pycaches, modules_info


def main(SCRIPT_PATH):
    print(f"[BTRACKING] Starting bytecode tracking for script: {SCRIPT_PATH}")
    addr_collect_start_time = time.time()

    pycaches = {}
    modules_info = {}
    C_functions_with_decorators = {}
    called_func = {}

    print(f"[BTRACKING] Performing entry tracking...")
    try:
        called_map, pycaches, modules_info = entry_tracking(
            pycaches, modules_info, SCRIPT_PATH)
        print(
            f"[BTRACKING] Entry tracking completed. Found {len(called_map)} called objects")
        print(f"[BTRACKING] Modules found: {list(modules_info.keys())}")
    except Exception as e:
        print(f"[BTRACKING ERROR] Entry tracking failed: {e}")
        return set(), 0, 0

    print(f"[BTRACKING] Starting module tracking...")
    try:
        new_called_map = module_tracking(
            pycaches, called_map, C_functions_with_decorators, called_func)
        print(
            f"[BTRACKING] Module tracking completed. Found {len(new_called_map)} new called objects")
    except Exception as e:
        print(f"[BTRACKING ERROR] Module tracking failed: {e}")
        new_called_map = {'__builtin': set(), '__user_def': set()}

    iteration = 0
    while (True):
        iteration += 1
        print(
            f"[BTRACKING] Iteration {iteration}: Looking for unique keys/values...")

        next_tracking = bcode_utils.find_unique_keys_values(
            called_map, new_called_map)

        if not next_tracking:
            print(
                f"[BTRACKING] No more unique tracking needed, stopping at iteration {iteration}")
            break

        print(
            f"[BTRACKING] Found {len(next_tracking)} items for next tracking")

        # next_tracking[key][__called] 값이 called_map의 __called 값에 포함되는 항목을 next_tracking에서 제거
        keys_to_remove = [
            key for key in next_tracking
            if key in called_map and called_map[key]['__called'].issuperset(next_tracking[key]['__called'])
        ]
        for key in keys_to_remove:
            del next_tracking[key]

        if keys_to_remove:
            print(f"[BTRACKING] Removed {len(keys_to_remove)} duplicate keys")

        pycaches = {}
        print(f"[BTRACKING] Searching module paths for next tracking...")
        search_module_path(next_tracking, pycaches)
        modules_info = pycaches | modules_info

        if next_tracking:
            print(f"[BTRACKING] Merging called maps...")
            called_map = bcode_utils.merge_dictionaries(
                called_map, new_called_map)
            print(f"[BTRACKING] Starting next module tracking iteration...")
            new_called_map = module_tracking(
                pycaches, next_tracking, C_functions_with_decorators, called_func)
        else:
            print(f"[BTRACKING] No more tracking needed")
            break

        if iteration > 10:  # Safety valve
            print(
                f"[BTRACKING WARNING] Too many iterations ({iteration}), breaking")
            break

    print(f"[BTRACKING] Extracting C functions...")
    try:
        not_pymodules = extract_c_func(modules_info, called_map)
        print(f"[BTRACKING] Found {len(not_pymodules)} non-Python modules")
        for module, funcs in not_pymodules.items():
            print(f"[BTRACKING]   {module}: {len(funcs)} functions")
    except Exception as e:
        print(f"[BTRACKING ERROR] Failed to extract C functions: {e}")
        not_pymodules = {}

    print(f"[BTRACKING] Checking PyMethodDef...")
    try:
        C_functions1 = func_mapping.check_PyMethodDef(not_pymodules)
        C_functions2 = func_mapping.check_PyMethodDef(
            C_functions_with_decorators)
        C_functions = C_functions1 | C_functions2
        print(f"[BTRACKING] Found {len(C_functions)} C functions total")
        print(f"[BTRACKING]   From modules: {len(C_functions1)}")
        print(f"[BTRACKING]   From decorators: {len(C_functions2)}")
    except Exception as e:
        print(f"[BTRACKING ERROR] Failed to check PyMethodDef: {e}")
        C_functions = {}

    # C_functions = C_functions1

    set_c_functions = set()

    for _, addr in C_functions.items():
        set_c_functions.add(addr)

    addr_collect_end_time = time.time()
    addr_collect_time = addr_collect_end_time - addr_collect_start_time
    module_count = len(modules_info)

    print(f"[BTRACKING] Completed successfully:")
    print(f"[BTRACKING]   Total C function addresses: {len(set_c_functions)}")
    print(f"[BTRACKING]   Address collection time: {addr_collect_time:.3f}s")
    print(f"[BTRACKING]   Module count: {module_count}")

    return set_c_functions, addr_collect_time, module_count
