import bcode_instructions
from pprint import pprint

import re

pattern = re.compile(r'\((.*?)\)')

def func_classification(func, called_objs, obj_sets, obj_map):
    '''
    함수 또는 메서드를 를 아래 세 가지 범주로 분류함.
      1. 파싱중인 스크립트에서 정의된 객체
      2. 외부 모듈의 객체
      3. 파이썬 내장 객체
    '''

    if '.' in func:
        root_obj = func.split('.')[0]

        # 외부 모듈로부터 호출되는 함수 또는 메서드
        if root_obj in called_objs.keys():
            return root_obj

        # 할당된 객체로부터 호출되는 메서드
        elif root_obj in obj_map.keys():
            # 최상위 객체가 사용자 정의 함수 또는 클래스 등에서 할당된 경우
            if obj_map[root_obj] in obj_sets:
                return '__user_def'

    # 파싱중인 스크립트에 정의된 함수 호출
    elif func in obj_sets:
        return '__user_def'
    
    # alias로 사용되는 외부 모듈의 함수 또는 메서드
    for outer_key, inner_dict in called_objs.items():
        if '__func_alias' not in inner_dict:
            continue
        if func in inner_dict['__func_alias']:
            return outer_key

    return '__builtin'

def lazy_loading(byte_code, idx, called_objs, cap_stack):
    quotes = re.compile(r"'([^']*)'")
    module = quotes.search(cap_stack[0]).group(1)

    if module not in called_objs.keys():
        next_line = byte_code[idx + 1]
        store = (pattern.search(next_line).group(1)).replace("'", '')
        called_objs[store] = {'__called':set(), '__origin_name':module}    

def parse_def(byte_code, addr_map, obj_sets, obj_map):
    LOAD = []
    parents_object = []

    called_objs = set()

    for i, line in enumerate(byte_code):
        if 'IMPORT_NAME' in line:
            # ctypes, libimport만 확인
            pass
        elif 'LOAD' in line:
            pobject = bcode_instructions.load(byte_code, i, LOAD)
            if pobject != None:
                parents_object.insert(0, pobject)
        elif 'POP_TOP' in line:
            bcode_instructions.pop(LOAD, line)
        # 스택의 상위 두 항목을 사용하여 함수 객체를 만듦.
        elif 'MAKE_FUNCTION' in line:
            bcode_instructions.make_function(byte_code, i, LOAD, addr_map)
        # 스택에 있는 N 개의 값을 합쳐 새로운 문자열을 만듦
        elif 'BUILD' in line:
            bcode_instructions.build(byte_code, i, LOAD)
        # 스택의 최상단에서 N번째 리스트를 확장
        elif 'LIST_EXTEND' in line:
            bcode_instructions.list_extend(byte_code, i, LOAD)
        elif 'STORE_ATTR' in line:
            # 객체의 속성에 할당되는 경우 이름 중복을 구분하기 위해 상위 객체정보를 함께 저장
            obj_addr = byte_code[0].split('at ')[1].split(',')[0].strip()
            parents_obj = list(addr_map[obj_addr].keys())[0]

            result = bcode_instructions.store_attr(byte_code, i, LOAD)
            if result != None:
                obj_map[parents_obj + '.' + result] = LOAD[-1]
        elif 'CALL_FUNCTION' in line:
            func = bcode_instructions.call_function(byte_code, i, LOAD, parents_object)
            called_objs.add(func)
            next_line = byte_code[i + 1]
            if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                result = (pattern.search(next_line).group(1))
                obj_map[result] = func
        elif 'CALL_METHOD' in line:
            method = bcode_instructions.call_method(byte_code, i, LOAD, parents_object)
            called_objs.add(method)
            next_line = byte_code[i + 1]
            if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                result = (pattern.search(next_line).group(1))
                obj_map[result] = method

        # next line(source code)
        if line.strip() == '':
            parents_object = []
    
    return called_objs

def parse_main(byte_code, addr_map, obj_sets, obj_map):
    LOAD = []
    parents_object = []

    called_objs = {'__builtin':set(), '__user_def':set()}

    for i, line in enumerate(byte_code):
        if 'IMPORT_NAME' in line:
            module, alias = bcode_instructions.import_name(byte_code, i)
            called_objs[alias] = {'__origin_name':module, '__called':set()}

        if 'IMPORT_FROM' in line:
            from_func, from_alias = bcode_instructions.import_from(byte_code, i)

            if '__func_alias' not in called_objs[alias]:
                called_objs[alias]['__func_alias'] = {}
            called_objs[alias]['__func_alias'][from_alias] = from_func

        elif 'LOAD' in line:
            pobject = bcode_instructions.load(byte_code, i, LOAD)
            if pobject != None:
                parents_object.insert(0, pobject)

        elif 'POP_TOP' in line:
            bcode_instructions.pop(LOAD, line)

        # 스택의 상위 두 항목을 사용하여 함수 객체를 만듦.
        elif 'MAKE_FUNCTION' in line:
            bcode_instructions.make_function(byte_code, i, LOAD, addr_map)

        # 스택에 있는 N 개의 값을 합쳐 새로운 문자열을 만듦
        elif 'BUILD' in line:
            bcode_instructions.build(byte_code, i, LOAD)

        # 스택의 최상단에서 N번째 리스트를 확장
        elif 'LIST_EXTEND' in line:
            bcode_instructions.list_extend(byte_code, i, LOAD)

        elif 'STORE_ATTR' in line:
            result = bcode_instructions.store_attr(byte_code, i, LOAD)
            if result != None:
                # obj_map[LOAD[-1]] = result
                obj_map[result] = LOAD[-1]
                
        elif 'CALL_FUNCTION' in line:
            if 'CALL_FUNCTION_KW' in line:
                func_offset = int(line.split('CALL_FUNCTION_KW')[1].strip())
            else:
                func_offset = int(line.split('CALL_FUNCTION')[1].strip())     

            func = bcode_instructions.call_function(byte_code, i, LOAD, parents_object)
            
            # __build_class__
            if func == None:
                continue
            category = func_classification(func, called_objs, obj_sets, obj_map)

            if category == '__builtin' or category == '__user_def':
                called_objs[category].add(func)
            else:
                called_objs[category]['__called'].add(LOAD[func_offset])

            next_line = byte_code[i + 1]
            if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                result = (pattern.search(next_line).group(1))
                obj_map[result] = func

        elif 'CALL_METHOD' in line:
            method_offset = int(line.split('CALL_METHOD')[1].strip())
            cap_stack = LOAD.copy()
            method = bcode_instructions.call_method(byte_code, i, LOAD, parents_object)
            category = func_classification(method, called_objs, obj_sets, obj_map)

            if method == 'importlib.import_module' or method == 'ctypes.CDLL':
                lazy_loading(byte_code, i, called_objs, cap_stack)

            if category == '__builtin' or category == '__user_def':
                called_objs[category].add(method)
            else:
                if category not in called_objs.keys():
                    called_objs[category] = {'__called':set()}
                called_objs[category]['__called'].add(method.split('.')[-1])

            next_line = byte_code[i + 1]
            if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                result = (pattern.search(next_line).group(1))
                obj_map[result] = method
            
        # next line(source code)
        if line.strip() == '':
            LOAD, parents_object = [], []
    
    return called_objs