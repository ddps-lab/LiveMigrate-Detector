import bcode_instructions
import importlib
import sys

from pprint import pprint
import re

pattern = re.compile(r'\((.*?)\)')

def module_classification(__module, __from):
    '''
    Python에서 모듈을 임포트할 때의 우선순위
    1.  현재 디렉토리 (또는 스크립트의 디렉토리):
	    •	Python 스크립트가 실행되는 디렉토리.
	2.	PYTHONPATH 환경 변수:
	    •	환경 변수 PYTHONPATH에 설정된 경로.
	3.	표준 라이브러리 디렉토리:
	    •	Python 설치 경로에 있는 표준 라이브러리 디렉토리. 예를 들어, Unix 시스템에서는 /usr/lib/python3.x와 같은 경로.
	4.	외부 패키지 디렉토리:
	    •	설치된 패키지의 경로로, 일반적으로 site-packages 디렉토리에 위치. 예를 들어, Unix 시스템에서는 /usr/local/lib/python3.x/site-packages와 같은 경로.
    '''


    # 아래 순서로 import를 시도하여 모듈을 구분함.
    # ex) __from : numpy.ma.extras, __module : core
    # 1. numpy.ma.extras.core - numpy.ma.extras가 numpy.ma의 서브 패키지인 경우
    # 2. numpy.ma.core - numpy.ma.extras가 numpy.ma의 모듈인 경우
    # 3. core - 외부 패키지
    module = __from + '.' + __module
    for _ in range(2):
        # 모듈이 이미 로드된 경우를 처리
        if module in sys.modules:
            return module
        
        try:
            importlib.import_module(module)
            return module
        except ModuleNotFoundError:
            pkg = __from.split('.')[:-1]
            if pkg:
                module = '.'.join(__from.split('.')[:-1]) + '.' + __module
        # 특정 OS에 최적화된 모듈을 import 하려는 경우 발생
        except ImportError as e:
            print(f'ImportError when import {module}')
            return e
        except AttributeError as e:
            print(f'AttributeError when import {module}')
            return e
    try:
        importlib.import_module(__module)
        return __module
    except ModuleNotFoundError as e:
        return e

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

def parse_import_instructions(content, called_objs, shared_variables, i):
    if 'IMPORT_NAME' in content:
        module, shared_variables.alias = bcode_instructions.import_name(i, shared_variables)
        
        # 상대경로로 import 하여 IMPORT_FROM을 확인해야 하는 경우.
        if module == None:
            return True
        
        module_path = module_classification(module, shared_variables.current_module)
        if isinstance(module_path, ModuleNotFoundError):
            module_path = module
        elif isinstance(module_path, AttributeError):
            return True
        elif isinstance(module_path, ImportError):
            return True

        called_objs[shared_variables.alias] = {'__origin_name':module_path, '__called':set(), '__from':shared_variables.current_module}
    elif 'IMPORT_FROM' in content:
        # IMPORT_FROM 으로 모듈을 로드하는 경우에 대한 처리
        if shared_variables.from_list:
            shared_variables.from_list.pop(0)
            module, shared_variables.alias = bcode_instructions.import_from(i, shared_variables)
            
            module_path = module_classification(module, shared_variables.current_module)
            if isinstance(module_path, ModuleNotFoundError):
                module_path = module
            elif isinstance(module_path, AttributeError):
                return True
            elif isinstance(module_path, ImportError):
                return True

            called_objs[shared_variables.alias] = {'__origin_name':module_path, '__called':set(), '__from':shared_variables.current_module}
            return True
        
        '''
        72 IMPORT_NAME             13 (collections.abc)
        74 IMPORT_FROM             14 (abc)
        76 STORE_NAME              15 (asdgsadg)
        위와 같이 IMPORT_FROM으로 로드되는 모듈이 단순히 alias 처리를 위함이라면 스택 상태만 처리
        '''
        if shared_variables.from_pass:
            _, _ = bcode_instructions.import_from(i, shared_variables)
            shared_variables.from_pass -= 1
            return True

        # IMPORT_FROM으로 함수 또는 메서드 객체를 로드하는 경우(본래 역할) 처리
        from_func, from_alias = bcode_instructions.import_from(i, shared_variables)
        
        # import할 수 없는 모듈이어서 생략하는 경우 ex) 특정 os 전용 모듈
        if shared_variables.alias not in called_objs:
            return True
        if '__func_alias' not in called_objs[shared_variables.alias]:
            called_objs[shared_variables.alias]['__func_alias'] = {}

        called_objs[shared_variables.alias]['__func_alias'][from_alias] = from_func

        return True
    elif 'IMPORT_STAR' in content:
        bcode_instructions.pop(shared_variables)
        return True

    return False

def parse_branch_instructions(content, offset, branch_shared_variables, shared_variables, verification):
    # 아래와 같은 경우 조건이 else라면 분기 전 스택을 기준으로 동작함.
    # 즉, 조건이 참인 경우에 변화할 스택 상태로 else를 처리하면 에러가 발생하므로 분기문에 대한 처리가 필요함.
    # print("NumPy CPU features: ", (info if info else 'nothing enabled'))
    '''
    [분기 처리 기본 동작]
    1. POP_JUMP_IF_FALSE 마다 stack을 capture하여 stack_cap에 push.
        * if에 해당.
    2. 현재 offset이 POP_JUMP_IF_FALSE의 target이 되면 직전 capture로 rollback, stack_cap.pop
        * else에 해당.

    if-elif는 아래와 같이 해석할 수 있음. 따라서 elif에 대해 별도로 처리하지 않음.
    if :
    else :
        if :

    동작 예제는 아래와 같음.
    if a > 10:  # push cap1
        test1()
        if a < b:   # push cap2
            test2()
            if a < b:   # push cap3
                test3()
            else: # rollback cap3, pop cap3
                if a == b: # push cap3
                    test4()
                else: # rollback cap3, pop cap3
                    test5()   

                if a != b: # push cap3
                    test6()
                else: # rollback cap3, pop3
                    test7()

            test8()
        else:   # rollback cap2, pop cap2
            test6()
            if a < b:   # push cap2
                test9()
            else:   # rollback cap2, pop2
                test10()
    elif a < 10:    # rollback cap1, pop cap1, push cap1
        test11()
    elif a == 12:   # rollback cap1, pop cap1, push cap1
        test11()
        if a < b:   # push cap2
            test13()
        else:   # rollback cap2, pop cap2
            test14()
    else:   # rollback cap1, pop cap1
        test15()

    if a == 9:  # push cap1
        if a == 100:    # push cap2
            f1()
            if a == 1000:   # push cap3
                f2()
            else:   # rollback cap3, pop cap3
                f3()        
        else:   # rollback cap2, pop cap2
            f4()
        a = 10

    if a == 9:  # push cap1
        if a == 100:    # push cap2
            f5()
            if a == 1000:   # push cap3
                f6()
            else:   # rollback cap3, pop cap3
                f7()        
        else:   # rollback cap2, pop cap2
            f8()
        a = 10
    elif a: # rollback cap1, pop cap1, push cap1
        f9()

    if a >= 10: # push cap1
        f10()
    else:   # rollback cap1, pop cap1
        f11()
        if a == 100:    # push cap1
            f12()
            if a == 100:    # push cap2
                f13()
            else:   # rollback cap2, pop cap2
                f14()
        else:   # rollback cap1, pop cap1
            f15()
    '''
    
    if offset in branch_shared_variables.branch_targets:
        shared_variables.LOAD = branch_shared_variables.stack_cap[-1].copy()
        # print(f'rollback!\toffset:{offset}, verification:{verification}, rollback to {verification[-1]}')

        branch_shared_variables.stack_cap.pop(-1)
        # print(f'pop!\t\toffset:{offset}, verification:{verification}, pop:{verification.pop(-1)}')
        return False

    if 'POP_JUMP_IF_FALSE' in content:
        bcode_instructions.pop(shared_variables)

        branch_shared_variables.stack_cap.append(shared_variables.LOAD.copy())
        branch_shared_variables.branch_targets.add(int((pattern.search(content).group(1)).split()[1]))
        # if len(verification) == 0:
        #     verification.append(1)
        # else:
        #     verification.append(max(verification) + 1)
        # print(f'push!\t\toffset:{offset}, verification:{verification}, push:{max(verification)}')
        # print(offset, shared_variables.LOAD)
        return True
    elif 'JUMP_IF_FALSE_OR_POP' in content:
        branch_shared_variables.stack_cap.append(shared_variables.LOAD.copy())
        branch_shared_variables.branch_targets.add(int((pattern.search(content).group(1)).split()[1]))

        bcode_instructions.pop(shared_variables)

    if 'JUMP_FORWARD' in content:
        branch_shared_variables.jp_offset.add(int((pattern.search(content).group(1)).split()[1]))
        # print(offset, shared_variables.LOAD)
        return True

def parse_shared_instructions(content, shared_variables):
    binary_operations = {'BINARY_POWER', 'BINARY_MULTIPLY', 'BINARY_MATRIX_MULTIPLY', 'BINARY_FLOOR_DIVIDE', 
                     'BINARY_TRUE_DIVIDE', 'BINARY_MODULO', 'BINARY_ADD', 'BINARY_SUBTRACT', 'BINARY_SUBSCR', 
                     'BINARY_LSHIFT', 'BINARY_RSHIFT', 'BINARY_AND', 'BINARY_XOR', 'BINARY_OR'}
    
    inplace_operations = {'INPLACE_ADD', 'INPLACE_SUBTRACT', 'INPLACE_MULTIPLY',
                        'INPLACE_DIVIDE', 'INPLACE_FLOOR_DIVIDE', 'INPLACE_TRUE_DIVIDE',
                        'INPLACE_MODULO', 'INPLACE_POWER', 'INPLACE_LSHIFT',
                        'INPLACE_RSHIFT', 'INPLACE_AND', 'INPLACE_XOR', 'INPLACE_OR'}

    instruction = content.split()[0]
    if 'LOAD' in instruction:
        bcode_instructions.load(content, shared_variables)
    elif 'STORE_NAME' in instruction or 'STORE_FAST' in instruction:
        bcode_instructions.pop(shared_variables)
    # 객체의 특정 인덱스나 키에 값을 할당 ex) sys.modules['importlib._bootstrap'] = _bootstrap
    elif 'STORE_SUBSCR' in instruction:
        [bcode_instructions.pop(shared_variables) for _ in range(3)]

    # stack controll
    elif 'POP_TOP' in instruction:
        bcode_instructions.pop(shared_variables)
    elif 'DUP_TOP' in instruction:
        try:
            bcode_instructions.dup(shared_variables)
        # except 문에서는 아래와 같이 DUP_TOP을 통해 스택 최상단의 예외 객체를 복사.
        # 예외 객체는 런타임에 스택에 삽입되므로 정적 분석에서는 스택이 비어있는 상태.
        # 따라서 비어있는 스택을 참조하려 하기 때문에 IndexError 가 발생함
        # 371 except ValueError:
        # 371     >>   58 DUP_TOP
        #              60 LOAD_GLOBAL              4 (ValueError)
        #              62 JUMP_IF_NOT_EXC_MATCH    38 (to 76)
        #              64 POP_TOP
        #              66 POP_TOP
        #              68 POP_TOP
        except IndexError:
            pass
    elif 'RETURN_VALUE' in instruction:
        try:
            bcode_instructions.pop(shared_variables)
        except IndexError:
            return

    # 예외를 발생시키는 명령어
    elif 'RAISE_VARARGS' in instruction:
        bcode_instructions.raise_varargs(content, shared_variables)
    elif 'RERAISE' in instruction:
        bcode_instructions.reraise(shared_variables)

    # 스택에 있는 N 개의 값을 합쳐 새로운 문자열을 만듦
    elif 'BUILD' in instruction:
        bcode_instructions.build(content, shared_variables)
    # 스택의 최상단에서 N번째 리스트를 확장
    elif 'LIST_EXTEND' in instruction:
        bcode_instructions.list_extend(content, shared_variables)
    # 두 값을 pop해 비교 후 true or flase를 푸시
    elif 'COMPARE_OP' in instruction or 'IS_OP' in instruction:
        bcode_instructions.pop2_push1(shared_variables)

    elif instruction in inplace_operations:
        bcode_instructions.pop2_push1(shared_variables)
    elif 'STORE_SUBSCR' in instruction:
        [bcode_instructions.pop(shared_variables) for _ in range(3)]
    elif 'DELETE_SUBSCR' in instruction:
        [bcode_instructions.pop(shared_variables) for _ in range(2)]
        
    elif instruction in binary_operations:
        bcode_instructions.pop2_push1(shared_variables)

def parse_def(byte_code, addr_map, obj_map, def_bcode_block_start_offsets, module):
    called_objs = set()
    comprehensions = ["function object for '<listcomp>'", "function object for '<dictcomp>'", "function object for '<setcomp>'", "function object for '<genexpr>'"]

    class BRANCH_SHARED_VARIABLES:
        def __init__(self):
            self.stack_cap = []
            self.jp_offset = set()
            self.branch_targets = set()

    class SHARED_VARIABLES:
        def __init__(self):
            self.byte_code = byte_code
            self.keys_list = list(byte_code.keys())[2:]
            self.LOAD = []
            self.addr_map = addr_map
            self.def_bcode_block_start_offsets = def_bcode_block_start_offsets

            self.current_module = module

            self.pass_offset = 0

            self.from_list = [] # IMPORT_FROM 으로 import 되는 모듈
            self.from_pass = 0 # alias를 위해 로드되는 모듈이 있으면 IMPORT_FROM 을 생략(스택 변화만 적용)
            self.alias = 0 # module alias -> IMPORT_FROM이 로드하는 객체가 어느 모듈에 속하는지 파악하기 위해 사용

    # FIXME: 검증용 스택, 추후 제거
    verification = []

    shared_variables = SHARED_VARIABLES()
    branch_shared_variables = BRANCH_SHARED_VARIABLES()

    for i, (offset, content) in enumerate(byte_code.items()):
        if offset == '__name' or offset == '__addr':
            continue

        if parse_branch_instructions(content, offset, branch_shared_variables, shared_variables, verification):
            continue

        # 해석하지 않을 바이트코드 명령 (사용자 코드가 아닌 내부 처리 코드)
        if offset < shared_variables.pass_offset:
            continue
        
        # FIXME: 파라미터로 전달하는 called_objs는 set이 아니고 dict여야함.
        # 해결하지 않으면 함수 내에서 모듈을 import 하는 것을 처리할 수 없음
        # if parse_import_instructions(content, called_objs, shared_variables, i):
            # continue

        if 'IMPORT_NAME' in content:
            # ctypes, libimport만 확인
            pass
        # 스택의 상위 두 항목을 사용하여 함수 객체를 만듦.
        elif 'MAKE_FUNCTION' in content:
            bcode_instructions.make_function(i - 2, content, shared_variables)
        elif 'STORE_ATTR' in content:
            # 객체의 속성에 할당되는 경우 이름 중복을 구분하기 위해 상위 객체정보를 함께 저장
            obj_addr = byte_code['__addr']

            if obj_addr in addr_map:
                parents_obj = list(addr_map[obj_addr].keys())[0]
                result = bcode_instructions.store_attr(i - 2, shared_variables)
                if result != None:
                    obj_map[parents_obj + '.' + result] = shared_variables.LOAD[-1].replace('(', '').replace(')', '')
            bcode_instructions.pop(shared_variables)
            bcode_instructions.pop(shared_variables)
        elif 'CALL_FUNCTION' in content:
            if 'CALL_FUNCTION_KW' in content:
                # keyword 까지 스택에 푸시되므로 해당 키워드를 건너뛰고 호출하는 함수가 있는 offset
                func_offset = int(content.split('CALL_FUNCTION_KW')[1].strip()) + 1
            elif 'CALL_FUNCTION_EX' in content:
                # args 까지 스택에 푸시되므로 해당 키워드를 건너뛰고 호출하는 함수가 있는 offset
                func_offset = int(content.split('CALL_FUNCTION_EX')[1].strip()) + 1
            else:
                func_offset = int(content.split('CALL_FUNCTION')[1].strip())

            # FIXME: 아래와 같은 경우 스택에는 np.ediff1d로 저장됨 때문에 np.np.ediff1d가 func 결과로 나오는 경우가 있음.
            # LOAD_METHOD의 경우 스택에 [ediff1d, np]로 저장됨. 일관성을 만들어주는게 좋을듯
            # 240 LOAD_GLOBAL              0 (np)
            # 242 LOAD_ATTR               15 (ediff1d)
            # 244 LOAD_FAST                4 (unique_pcts)
            # 246 LOAD_FAST                5 (to_begin)
            # 248 LOAD_FAST                6 (to_end)
            # 250 LOAD_CONST              11 (('to_begin', 'to_end'))
            # 252 CALL_FUNCTION_KW         3
            func = bcode_instructions.call_function(func_offset, shared_variables)
            # comprehensions 함수를 호출하는 경우(실제 함수가 아님)
            if func in comprehensions:
                bcode_instructions.call_function_stack(func_offset, shared_variables)
                continue

            called_objs.add(func)

            next_content = byte_code[shared_variables.keys_list[i - 2]]

            if 'STORE_NAME' in next_content or 'STORE_FAST' in next_content:
                result = (pattern.search(next_content).group(1))
                obj_map[result] = func
            
            bcode_instructions.call_function_stack(func_offset, shared_variables)
        elif 'CALL_METHOD' in content:
            method = bcode_instructions.call_method(content, shared_variables)
            called_objs.add(method)
            next_content = byte_code[shared_variables.keys_list[i - 2]]
            if 'STORE_NAME' in next_content or 'STORE_FAST' in next_content:
                result = (pattern.search(next_content).group(1))
                obj_map[result] = method
        else:
            parse_shared_instructions(content, shared_variables)
        # print(offset, shared_variables.LOAD)
    return called_objs

def parse_main(byte_code, addr_map, obj_sets, obj_map, main_bcode_block_start_offsets, module):
    called_objs = {'__builtin':set(), '__user_def':set()}
    comprehensions = ["function object for '<listcomp>'", "function object for '<dictcomp>'", "function object for '<setcomp>'", "function object for '<genexpr>'"]

    class BRANCH_SHARED_VARIABLES:
        def __init__(self):
            self.stack_cap = []
            self.jp_offset = set()
            self.branch_targets = set()

    class SHARED_VARIABLES:
        def __init__(self):
            self.byte_code = byte_code
            self.keys_list = list(byte_code.keys())
            self.LOAD = []
            self.addr_map = addr_map
            self.main_bcode_block_start_offsets = main_bcode_block_start_offsets

            self.current_module = module

            self.pass_offset = 0

            self.from_list = [] # IMPORT_FROM 으로 import 되는 모듈
            self.from_pass = 0 # alias를 위해 로드되는 모듈이 있으면 IMPORT_FROM 을 생략(스택 변화만 적용)
            self.alias = 0 # module alias -> IMPORT_FROM이 로드하는 객체가 어느 모듈에 속하는지 파악하기 위해 사용

            self.decorator_map = dict()
            self.decorators = set()

    # FIXME: 검증용 스택, 추후 제거
    verification = []

    shared_variables = SHARED_VARIABLES()
    branch_shared_variables = BRANCH_SHARED_VARIABLES()

    for i, (offset, content) in enumerate(byte_code.items()):
        if offset == '__name' or offset == '__addr':
            continue

        if offset < shared_variables.pass_offset:
            continue

        if parse_branch_instructions(content, offset, branch_shared_variables, shared_variables, verification):
            continue
        
        if parse_import_instructions(content, called_objs, shared_variables, i):
            continue

        # 스택의 상위 두 항목을 사용하여 함수 객체를 만듦.
        elif 'MAKE_FUNCTION' in content:
            bcode_instructions.make_function(i, content, shared_variables)
        elif 'STORE_ATTR' in content:
            result = bcode_instructions.store_attr(i, shared_variables)
            if result != None:
                obj_map[result] = shared_variables.LOAD[-1]

            bcode_instructions.pop(shared_variables)
            bcode_instructions.pop(shared_variables)                
        elif 'CALL_FUNCTION' in content:
            if 'CALL_FUNCTION_KW' in content:
                # keyword 까지 스택에 푸시되므로 해당 키워드를 건너뛰고 호출하는 함수가 있는 offset
                func_offset = int(content.split('CALL_FUNCTION_KW')[1].strip()) + 1
            elif 'CALL_FUNCTION_EX' in content:
                # args 까지 스택에 푸시되므로 해당 키워드를 건너뛰고 호출하는 함수가 있는 offset
                func_offset = int(content.split('CALL_FUNCTION_EX')[1].strip()) + 1
            else:
                func_offset = int(content.split('CALL_FUNCTION')[1].strip())

            func = bcode_instructions.call_function(func_offset, shared_variables)

            if func in shared_variables.decorators:
                continue
            
            # comprehensions 함수를 호출하는 경우(실제 함수가 아님)
            if func in comprehensions:
                bcode_instructions.call_function_stack(func_offset, shared_variables)
                continue

            # __build_class__
            if func == None:
                bcode_instructions.call_function_stack(func_offset, shared_variables)
                continue

            category = func_classification(func, called_objs, obj_sets, obj_map)
            # 함수 또는 메서드의 호출 반환이 객체인 경우 정보를 저장
            next_line = byte_code[shared_variables.keys_list[i + 1]]
            if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                result = (pattern.search(next_line).group(1))
                if category not in func and not category.startswith('__'):
                    func = category + '.' + func
                obj_map[result] = func

            if func.split('.')[0] in obj_map:
                external_module, obj_func = '', ''

                assign = obj_map[func.split('.')[0]].split('.')
                for i in range(len(assign), 0, -1):
                    if '.'.join(assign[:i]) in called_objs.keys():
                        external_module = '.'.join(assign[:i])
                        obj_func = '.'.join(assign[i:])
                
                if external_module and obj_func:
                    called_objs[external_module]['__called'].add(obj_func + '.' + '.'.join(func.split('.')[1:]))
                    continue

            if category == '__builtin' or category == '__user_def':
                called_objs[category].add(func)
            else:
                called_func = shared_variables.LOAD[func_offset]
                # module.func 형태의 호출의 경우 func만 추출해 저장 ex) xgb.XGBClassifier -> XGBClassifier
                if '.' in called_func and called_func.split('.')[0] in called_objs:
                    called_func = ''.join(called_func.split('.')[1:])

                called_objs[category]['__called'].add(called_func)

            bcode_instructions.call_function_stack(func_offset, shared_variables)
        elif 'CALL_METHOD' in content:
            cap_stack = shared_variables.LOAD.copy()
            method = bcode_instructions.call_method(content, shared_variables)

            if method == 'importlib.import_module' or method == 'ctypes.CDLL':
                lazy_loading(byte_code, i, shared_variables.keys_list, called_objs, cap_stack)

            # 함수 또는 메서드의 호출 반환이 객체인 경우 정보를 저장
            next_line = byte_code[shared_variables.keys_list[i + 1]]
            if 'STORE_NAME' in next_line or 'STORE_FAST' in next_line:
                result = (pattern.search(next_line).group(1))
                obj_map[result] = method

            # 외부 모듈의 객체에서 호출하는 메서드
            # 'scaler': 'sklearn.preprocessing.StandardScaler',
            # scaler.fit_transform
            if method.split('.')[0] in obj_map:
                external_module, obj_method = '', ''

                assign = obj_map[method.split('.')[0]].split('.')
                for i in range(len(assign), 0, -1):
                    if '.'.join(assign[:i]) in called_objs.keys():
                        external_module = '.'.join(assign[:i])
                        obj_method = '.'.join(assign[i:])
                
                if external_module and obj_method:
                    called_objs[external_module]['__called'].add(obj_method + '.' + '.'.join(method.split('.')[1:]))
                    continue

            category = func_classification(method, called_objs, obj_sets, obj_map)

            if category == '__builtin' or category == '__user_def':
                called_objs[category].add(method)
            else:
                if category not in called_objs.keys():
                    called_objs[category] = {'__called':set()}
                called_objs[category]['__called'].add(method.split('.')[-1])
        else:
            parse_shared_instructions(content, shared_variables)
        # print(offset, shared_variables.LOAD)
    # pprint(shared_variables.decorator_map)
    # input()
    return called_objs, shared_variables.decorator_map