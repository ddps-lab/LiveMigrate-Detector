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

def lazy_loading(byte_code, idx, keys_list, called_objs, cap_stack):
    quotes = re.compile(r"'([^']*)'")
    module = quotes.search(cap_stack[0]).group(1)

    if module not in called_objs.keys():
        next_line = byte_code[keys_list[idx + 1]]
        store = (pattern.search(next_line).group(1)).replace("'", '')
        called_objs[store] = {'__called':set(), '__origin_name':module}    

def parse_shared_instructions(content, LOAD, parents_object):
    if 'LOAD' in content:
        pobject = bcode_instructions.load(content, LOAD)
        if pobject != None:
            parents_object.insert(0, pobject)

    # stack controll
    elif 'POP_TOP' in content:
        bcode_instructions.pop(LOAD)
    elif 'DUP_TOP' in content:
        bcode_instructions.dup(LOAD)

    # try-except
    elif 'SETUP_FINALLY' in content:
        bcode_instructions.setup_finally(LOAD)
    elif 'END_FINALLY' in content:
        bcode_instructions.pop(LOAD)
    elif 'POP_BLOCK' in content:
        bcode_instructions.pop(LOAD)
    elif 'POP_EXCEPT' in content:
        bcode_instructions.pop(LOAD)

    # 스택에 있는 N 개의 값을 합쳐 새로운 문자열을 만듦
    elif 'BUILD' in content:
        bcode_instructions.build(content, LOAD)
    # 스택의 최상단에서 N번째 리스트를 확장
    elif 'LIST_EXTEND' in content:
        bcode_instructions.list_extend(content, LOAD)
    # 두 값을 pop해 비교 후 true or flase를 푸시
    elif 'COMPARE_OP' in content:
        bcode_instructions.pop2_push1(LOAD)
    
    # -=
    elif 'INPLACE_SUBTRACT' in content:
        bcode_instructions.pop2_push1(LOAD)
    # +=
    elif 'INPLACE_ADD' in content:
        bcode_instructions.pop2_push1(LOAD)
    # *=
    elif 'INPLACE_MULTIPLY' in content:
        bcode_instructions.pop2_push1(LOAD)
    # /=
    elif 'INPLACE_TRUE_DIVIDE' in content:
        bcode_instructions.pop2_push1(LOAD)
    # %=    
    elif 'INPLACE_MODULO' in content:
        bcode_instructions.pop2_push1(LOAD)
    # //=
    elif 'INPLACE_FLOOR_DIVIDE' in content:
        bcode_instructions.pop2_push1(LOAD)
    # **=
    elif 'INPLACE_POWER' in content:
        bcode_instructions.pop2_push1(LOAD)


def parse_def(byte_code, addr_map, obj_map):
    keys_list = list(byte_code.keys())
    keys_list = keys_list[2:]
    LOAD = []
    parents_object = []

    called_objs = set()

    for i, (offset, content) in enumerate(byte_code.items()):
        if offset == '__name' or offset == '__addr':
            continue

        if 'IMPORT_NAME' in content:
            # ctypes, libimport만 확인
            pass
        # 스택의 상위 두 항목을 사용하여 함수 객체를 만듦.
        elif 'MAKE_FUNCTION' in content:
            bcode_instructions.make_function(byte_code, i - 2, keys_list, LOAD, addr_map)
        elif 'STORE_ATTR' in content:
            # 객체의 속성에 할당되는 경우 이름 중복을 구분하기 위해 상위 객체정보를 함께 저장
            obj_addr = byte_code['__addr']

            if obj_addr in addr_map:
                parents_obj = list(addr_map[obj_addr].keys())[0]
                result = bcode_instructions.store_attr(byte_code, i - 2, keys_list)
                if result != None:
                    obj_map[parents_obj + '.' + result] = LOAD[-1]                
            else:
                # FIXME:
                # 상위 객체 정보가 없는 경우
                # 객체에 속하지 않는 함수에서 obj.attr에 함수의 결과가 저장되는 경우
                pass
        elif 'CALL_FUNCTION' in content:
            func = bcode_instructions.call_function(content, LOAD, parents_object)
            called_objs.add(func)

            next_content = byte_code[keys_list[i - 1]]
            if 'STORE_NAME' in next_content or 'STORE_FAST' in next_content:
                result = (pattern.search(next_content).group(1))
                obj_map[result] = func
        elif 'CALL_METHOD' in content:
            method = bcode_instructions.call_method(content, LOAD, parents_object)
            called_objs.add(method)
            next_content = byte_code[keys_list[i - 1]]
            if 'STORE_NAME' in next_content or 'STORE_FAST' in next_content:
                result = (pattern.search(next_content).group(1))
                obj_map[result] = method
        else:
            parse_shared_instructions(content, LOAD, parents_object)

    return called_objs

def parse_main(byte_code, addr_map, obj_sets, obj_map):
    keys_list = list(byte_code.keys())
    LOAD = []
    parents_object = []
    called_objs = {'__builtin':set(), '__user_def':set()}

    def scan_bcode(LOAD, condition):
        branch_target = 0
        branch_out = 0
        inner_branch_targets = {}
        for i, (offset, content) in enumerate(byte_code.items()):
            if offset == '__name' or offset == '__addr':
                continue

            '''
            외부 분기문 처리 알고리즘
            1. 깊이가 0인 즉, 가장 바깥의 분기는 무조건 True or False로 가정하여 전체 바이트코드를 2회 스캔한다.
            
            내부 분기문 처리 알고리즘
            1. POP_JUMP_IF_FALSE 명령을 만나면 현재의 스택과 분기 타겟 지점을 기록한다.
            2. 조건의 True를 먼저 수행한다. False의 시작 지점은 내부 분기문의 타겟 지점과 동일하다.
            3. 현재 offset이 분기 타겟 지점과 동일하다면 True를 수행하기 이전의 스택 상태로 초기화한다.
            4. 조건의 False를 수행한다.
            * 더 깊은 분기문도 마찬가지로 True부터 수행한다. (깊이 우선 탐색)
            * 내부 분기문을 순회할 때는 JUMP_FORWARD를 무시한다.
            '''

            # 외부 분기문 처리
            if offset < branch_target:
                continue

            if inner_branch_targets and offset in inner_branch_targets:
                LOAD = inner_branch_targets[offset].copy()
                inner_branch_targets.pop(offset, None)
            
            # 바깥 분기가 true일 때 바깥 분기의 false 지점까지 스캔 완료한 경우
            if offset == branch_out:
                inner_branch_targets.pop(offset, None)

            if 'POP_JUMP_IF_FALSE' in content:
                bcode_instructions.pop(LOAD)

                if condition:
                    branch_target = 0
                    if branch_out:
                        inner_branch_targets[int((pattern.search(content).group(1)).split()[1])] = LOAD.copy()

                    branch_out = int((pattern.search(content).group(1)).split()[1])
                else:
                    branch_target = int((pattern.search(content).group(1)).split()[1])

            elif 'JUMP_FORWARD' in content:
                # POP_JUMP_IF_FALSE의 FALSE로 이동 중일 때 branch_target이 변경되는 것을 방지
                # 또는 내부 분기문을 스캔중일 때 바깥으로 나가는 것을 방지
                if offset < branch_target or len(inner_branch_targets) > 1:
                    continue
                branch_target = int((pattern.search(content).group(1)).split()[1])

            if 'IMPORT_NAME' in content:
                module, alias = bcode_instructions.import_name(byte_code, i, keys_list)
                called_objs[alias] = {'__origin_name':module, '__called':set()}
            if 'IMPORT_FROM' in content:
                from_func, from_alias = bcode_instructions.import_from(byte_code, i, keys_list)

                if '__func_alias' not in called_objs[alias]:
                    called_objs[alias]['__func_alias'] = {}
                called_objs[alias]['__func_alias'][from_alias] = from_func

            # 스택의 상위 두 항목을 사용하여 함수 객체를 만듦.
            elif 'MAKE_FUNCTION' in content:
                bcode_instructions.make_function(byte_code, i, keys_list, LOAD, addr_map)
            elif 'STORE_ATTR' in content:
                result = bcode_instructions.store_attr(byte_code, i, keys_list)
                if result != None:
                    obj_map[result] = LOAD[-1]
            elif 'CALL_FUNCTION' in content:
                if 'CALL_FUNCTION_KW' in content:
                    func_offset = int(content.split('CALL_FUNCTION_KW')[1].strip())
                else:
                    func_offset = int(content.split('CALL_FUNCTION')[1].strip())     

                func = bcode_instructions.call_function(content, LOAD, parents_object)
                # __build_class__
                if func == None:
                    continue
                category = func_classification(func, called_objs, obj_sets, obj_map)

                if category == '__builtin' or category == '__user_def':
                    called_objs[category].add(func)
                else:
                    called_objs[category]['__called'].add(LOAD[func_offset])

                next_line = byte_code[keys_list[i + 1]]
                if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                    result = (pattern.search(next_line).group(1))
                    obj_map[result] = func

            elif 'CALL_METHOD' in content:
                cap_stack = LOAD.copy()
                method = bcode_instructions.call_method(content, LOAD, parents_object)
                category = func_classification(method, called_objs, obj_sets, obj_map)

                if method == 'importlib.import_module' or method == 'ctypes.CDLL':
                    lazy_loading(byte_code, i, keys_list, called_objs, cap_stack)

                if category == '__builtin' or category == '__user_def':
                    called_objs[category].add(method)
                else:
                    if category not in called_objs.keys():
                        called_objs[category] = {'__called':set()}
                    called_objs[category]['__called'].add(method.split('.')[-1])

                next_line = byte_code[keys_list[i + 1]]
                if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                    result = (pattern.search(next_line).group(1))
                    obj_map[result] = method
            else:
                parse_shared_instructions(content, LOAD, parents_object)             
    
    # 깊이가 0인 모든 분기를 참으로 판단(분기 불허)
    # FIXME: 2레벨 이상 깊이 테스트 필요
    scan_bcode(LOAD, condition = True)
    # 깊이가 0인 모든 분기를 거짓으로 판단(분기 허용)
    # FIXME: 내부 분기문 처리 못함
    scan_bcode(LOAD, condition = False)

    return called_objs