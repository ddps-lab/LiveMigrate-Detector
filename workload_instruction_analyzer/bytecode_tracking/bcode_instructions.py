import re

from pprint import pprint

pattern = re.compile(r'\((.*?)\)')

def import_name(byte_code, idx, keys_list):
    line = byte_code[keys_list[idx]]

    if 'IMPORT_NAME' in line:
        module = (pattern.search(line).group(1))
        root_module = (pattern.search(line).group(1)).split('.')[0]
        # 다음 라인을 확인해 import된 모듈이 어떤 이름으로 사용되는지 파악
        next_line = byte_code[keys_list[idx + 1]]
        if 'STORE_NAME' in next_line:
            alias = (pattern.search(next_line).group(1))
            return module, alias
        # from문이 사용된 경우 모듈 자체에 alias 지정 불가.
        else:
            return module, root_module

def import_from(byte_code, idx, keys_list):
    line = byte_code[keys_list[idx]]
        
    func = (pattern.search(line).group(1))
    # 다음 라인을 확인해 import된 모듈이 어떤 이름으로 사용되는지 파악
    next_line = byte_code[keys_list[idx + 1]]
    if 'STORE_NAME' in next_line:
        alias = (pattern.search(next_line).group(1))
        return func, alias

    return func, None

def load_build_class(LOAD):
    LOAD.insert(0, '__build_class__')

def load_attr(content, LOAD):
    value = LOAD.pop(0) + '.' + pattern.search(content).group(1)
    LOAD.insert(0, value)

def load_method(content, LOAD):
    parents_object = LOAD[0]
    LOAD.insert(0, pattern.search(content).group(1))
    return parents_object

def load_etc(content, LOAD):
    LOAD.insert(0, pattern.search(content).group(1))
    
def load(content, LOAD):
    parents_object = None

    # 클래스 정의
    if 'LOAD_BUILD_CLASS' in content:
        LOAD.insert(0, '__build_class__')
    # 스택의 최상단에 있는 객체로부터 속성을 로드하고, 이 속성 값을 스택의 최상단에 푸시
    # self 객체 자체가 스택에서 제거되고 self의 value 속성 값만 스택에 남음
    elif 'LOAD_ATTR' in content:
        value = LOAD.pop(0) + '.' + pattern.search(content).group(1)
        LOAD.insert(0, value)
    # LOAD_METHOD는 스택의 최상단에 있는 객체에서 메서드를 찾음
    elif 'LOAD_METHOD' in content:
        parents_object = LOAD[0]
        LOAD.insert(0, pattern.search(content).group(1))
        return parents_object
    else:
        LOAD.insert(0, pattern.search(content).group(1))

def make_function(byte_code, idx, keys_list, LOAD, addr_map):
    value = 'function object for ' + LOAD.pop(0)
    LOAD.pop(0)
    LOAD.insert(0, value)

    offset = 0
    prev_line = byte_code[keys_list[idx - 1]]
    # 생성되는 함수가 특정 클래스에 종속적인 경우
    if 'LOAD_CONST' in prev_line:
        if '.' in (pattern.search(prev_line).group(1)):
            parents_object = pattern.search(prev_line).group(1).split('.')[0].replace("'", "")
            child_object = pattern.search(prev_line).group(1).split('.')[-1].replace("'", "")
            while True:
                # 클래스에서 정의되는 메서드가 구현될 주소 파악
                if '(<code object' in prev_line:
                    obj_addr = prev_line.split('at ')[1].split(',')[0].strip()
                    addr_map[obj_addr] = {parents_object:child_object}
                    break
                offset -= 1
                if idx + offset == 0:
                    break
                prev_line = byte_code[keys_list[idx + offset]]
    
def build(content, LOAD):
    if 'BUILD_STRING' in content:
        args_count = int(content.split('BUILD_STRING')[1].strip())
        merge_str = ''
        for i in range(args_count):
            merge_str += LOAD.pop(0)
        LOAD.insert(0, merge_str)
    elif 'BUILD_LIST' in content:
        args_count = int(content.split('BUILD_LIST')[1].strip())
        merge_list = ''
        if args_count == 0:
            LOAD.insert(0, '[]')
        else:    
            for _ in range(args_count):
                merge_list += LOAD.pop(0)
            LOAD.insert(0, merge_list)    

def store_attr(byte_code, idx, keys_list):
    line = byte_code[keys_list[idx]]

    # 함수 호출이 아닌 경우를 구분해야함. 함수 호출 없이 객체.변수에 값 할당하는 경우가 있기 때문.
    # Python 바이트코드에서 STORE_ATTR 명령어 다음에 CALL_FUNCTION 명령어가 오는 것은 일반적인 상황이 아님.
    # 따라서 명령어 블록을 조사해 STORE_ATTR 위의 명령들에서 함수 또는 메서드 호출이 있는지 확인함.
    offset = 0
    prev_line = byte_code[keys_list[idx - 1]]
    with_call = False
    while True:
        if 'CALL_FUNCTION' in prev_line or 'CALL_METHOD' in prev_line:
            with_call = True
            break
        offset -= 1
        if idx + offset == 0:
            return None
        prev_line = byte_code[keys_list[idx + offset]]

    if with_call:
        result = (pattern.search(line).group(1))
        return result
    return None

def call_function(content, LOAD, parents_object):
    called_func = None

    if 'CALL_FUNCTION_KW' in content:
        # keyword 까지 스택에 푸시되므로 해당 키워드를 건너뛰고 호출하는 함수가 있는 offset
        func_offset = int(content.split('CALL_FUNCTION_KW')[1].strip()) + 1
    else:
        func_offset = int(content.split('CALL_FUNCTION')[1].strip())
    
    if LOAD[func_offset] == '__build_class__':
        pass
    else:
        # func() 형태의 호출
        if len(parents_object) == 0:
            called_func = LOAD[func_offset]
        # obj.func 형태의 호출
        else:
            called_func = parents_object.pop(0) + '.' + LOAD[func_offset]
    
    call_result = ''
    # 호출되는 함수와 인자들을 pop
    for _ in range(func_offset + 1):
        call_result += LOAD.pop(0)
    LOAD.insert(0, call_result)

    # 객체로부터 호출되는 경우 해당 객체도 pop
    if len(parents_object) != 0:
        LOAD.pop(0)

    return called_func

def call_method(content, LOAD, parents_object):
    method_offset = int(content.split('CALL_METHOD')[1].strip())
    if len(parents_object) == 0:
        called_method = LOAD[method_offset]
    else:
        called_method = parents_object.pop(0) + '.' + LOAD[method_offset]
    
    call_result = ''
    # 호출되는 메서드와 상위 객체, 인자들을 pop
    for _ in range(method_offset + 2):
        call_result += LOAD.pop(0)

    LOAD.insert(0, call_result)

    return called_method

def list_extend(content, LOAD):
    # 스택의 상단부터 취합해 N 번째에 있는 리스트를 확장하지만 확장된 리스트 정보는 필요하지 않으므로 pop만 수행함.
    args_count = int(content.split('LIST_EXTEND')[1].strip())
    for i in range(args_count):
        LOAD.pop(0)

def pop2_push1(LOAD):
    LOAD.pop(0)
    LOAD.pop(0)
    LOAD.insert(0, 'pop2_push1')
    
def setup_finally(LOAD):
    LOAD.insert(0, 'tryblock')

def pop(LOAD):
    LOAD.pop(0)

def dup(LOAD):
    LOAD.insert(0, LOAD[0])