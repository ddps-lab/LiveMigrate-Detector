import re

pattern = re.compile(r'\((.*?)\)')


def import_name(idx, shared_variables):
    byte_code = shared_variables.byte_code
    keys_list = shared_variables.keys_list

    line = byte_code[keys_list[idx]]

    try:
        module = pattern.search(line).group(1)

        # 스택에서 임포트 레벨과 fromlist를 팝
        shared_variables.LOAD.pop(0)
        shared_variables.LOAD.pop(0)
        shared_variables.LOAD.insert(0, module)
    except AttributeError:
        prev_line = byte_code[keys_list[idx - 1]]

        # 상대경로에서 가져오는 모듈 추출
        module = re.findall(r"\'([^\']+)\'", prev_line)
        shared_variables.from_list.clear()
        shared_variables.from_list.extend(module)

        shared_variables.LOAD.pop(0)
        shared_variables.LOAD.pop(0)
        shared_variables.LOAD.insert(0, module)

        return None, None

    # 다음 라인을 확인해 import된 모듈이 어떤 이름으로 사용되는지 파악
    next_line = byte_code[keys_list[idx + 1]]
    if 'STORE_NAME' in next_line:
        alias = (pattern.search(next_line).group(1))

        if '.' in module:
            return module, module

        return module, alias

    prev_line = byte_code[keys_list[idx - 1]]
    if 'LOAD_CONST' in prev_line:
        args = pattern.search(prev_line).group(1)
        if args == 'None':
            i = 1
            while True:
                next_line = byte_code[keys_list[idx + i]]
                if 'STORE_NAME' in next_line:
                    alias = (pattern.search(next_line).group(1))
                    shared_variables.from_pass = module.count('.')
                    return module, alias
                i += 1

    # from문이 사용된 경우 모듈 자체에 alias 지정 불가.
    return module, module


def import_from(idx, shared_variables):
    byte_code = shared_variables.byte_code
    keys_list = shared_variables.keys_list
    line = byte_code[keys_list[idx]]

    func = (pattern.search(line).group(1))
    shared_variables.LOAD.insert(0, func)

    # 다음 라인을 확인해 import된 모듈이 어떤 이름으로 사용되는지 파악
    next_line = byte_code[keys_list[idx + 1]]
    if 'STORE_NAME' in next_line:
        alias = (pattern.search(next_line).group(1))

        if shared_variables.from_list:
            module = func
            return module, alias

        return func, alias

    if shared_variables.from_list:
        return module, None

    return func, None


def raise_varargs(content, shared_variables):
    LOAD = shared_variables.LOAD
    operation_option = int(content.split('RAISE_VARARGS')[1].strip())

    for _ in range(operation_option):
        LOAD.pop(0)


def reraise(shared_variables):
    LOAD = shared_variables.LOAD

    if LOAD and LOAD[0] == 'tryblock':
        LOAD.pop(0)


def load_build_class(shared_variables):
    shared_variables.LOAD.insert(0, '__build_class__')


def load_attr(content, shared_variables):
    value = shared_variables.LOAD.pop(
        0) + '.' + pattern.search(content).group(1)
    shared_variables.LOAD.insert(0, value)


def load_etc(content, shared_variables):
    shared_variables.LOAD.insert(0, pattern.search(content).group(1))


def load(content, shared_variables):
    LOAD = shared_variables.LOAD

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
        value = LOAD.pop(0) + '.' + pattern.search(content).group(1)
        LOAD.insert(0, value)
    elif 'LOAD_ASSERTION_ERROR' in content:
        LOAD.insert(0, 'AssertionError')
    else:
        LOAD.insert(0, pattern.search(content).group(1))


def make_function(idx, content, shared_variables):
    def pop(options, LOAD):
        # 시작 팝 횟수: 코드 객체 + 함수 이름 = 2
        pop_count = 2

        # 옵션 별 비트 마스크
        # 기본값(defaults): 0x01, 클로저(closure): 0x02, 어노테이션(annotations): 0x04,
        # 키워드 전용 인자의 기본값: 0x08, 정규 인자명(qualname): 0x10
        # 각 옵션이 설정되어 있으면, pop_count에 1을 더합니다.

        if options & 0x01:  # 기본값
            pop_count += 1
        if options & 0x02:  # 클로저
            pop_count += 1
        if options & 0x04:  # 어노테이션
            pop_count += 1
        if options & 0x08:  # 키워드 전용 인자의 기본값
            pop_count += 1
        if options & 0x10:  # 정규 인자명
            pop_count += 1

        value = 'function object for ' + LOAD.pop(0)
        for _ in range(pop_count - 1):
            LOAD.pop(0)
        LOAD.insert(0, value)

    byte_code = shared_variables.byte_code
    keys_list = shared_variables.keys_list
    LOAD = shared_variables.LOAD
    addr_map = shared_variables.addr_map

    operation_option = int(content.split(
        'MAKE_FUNCTION')[1].strip().split()[0])
    maked_func = LOAD[0].strip("'")
    print(f"[MAKE_FUNCTION DEBUG] Creating function: {maked_func}")
    # Show first 5 items
    print(f"[MAKE_FUNCTION DEBUG] Current LOAD stack: {LOAD[:5]}")

    pop(operation_option, LOAD)

    offset = 0
    prev_line = byte_code[keys_list[idx - 1]]
    # 생성되는 함수가 특정 클래스에 종속적인 경우
    if 'LOAD_CONST' in prev_line:
        if '.' in (pattern.search(prev_line).group(1)):
            parents_object = pattern.search(prev_line).group(
                1).split('.')[0].replace("'", "")
            child_object = pattern.search(prev_line).group(
                1).split('.')[-1].replace("'", "")
            while True:
                # 클래스에서 정의되는 메서드가 구현될 주소 파악
                if '(<code object' in prev_line:
                    obj_addr = prev_line.split('at ')[1].split(',')[0].strip()
                    addr_map[obj_addr] = {parents_object: child_object}
                    break
                offset -= 1
                if idx + offset == 0:
                    break
                prev_line = byte_code[keys_list[idx + offset]]

    if hasattr(shared_variables, 'decorator_map'):
        next_line = byte_code[keys_list[idx + 1]]
        print(f"[MAKE_FUNCTION DEBUG] Next line: {next_line}")

        if 'CALL_FUNCTION' in next_line:
            func_offset = int(next_line.split('CALL_FUNCTION')[1].strip())
            decorator_func = LOAD[func_offset] if func_offset < len(
                LOAD) else "INDEX_OUT_OF_RANGE"

            print(
                f"[MAKE_FUNCTION DEBUG] Found decorator call with offset {func_offset}")
            print(
                f"[MAKE_FUNCTION DEBUG] Decorator function: {decorator_func}")
            print(f"[MAKE_FUNCTION DEBUG] LOAD stack at decorator: {LOAD}")

            shared_variables.decorator_map[maked_func] = decorator_func
            shared_variables.decorators.add(decorator_func)

            # Check if this is a ctypes_function decorator
            if 'ctypes_function' in str(decorator_func):
                print(
                    f"[CTYPES DEBUG] Found ctypes_function decorator for {maked_func}")
                print(f"[CTYPES DEBUG] Full decorator: {decorator_func}")
                print(f"[CTYPES DEBUG] Full LOAD stack: {LOAD}")

                # Try to extract the actual C function name from the decorator arguments
                # Look for string arguments in the stack that might be function names
                for i, item in enumerate(LOAD):
                    if isinstance(item, str) and not item.startswith('(') and not item.startswith('['):
                        print(
                            f"[CTYPES DEBUG] Potential C function name at stack[{i}]: {item}")


def build(content, shared_variables):
    LOAD = shared_variables.LOAD

    if 'BUILD_STRING' in content:
        args_count = int(content.split('BUILD_STRING')[1].strip())
        merge_str = ''
        for _ in range(args_count):
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
            LOAD.insert(0, '[' + merge_list + ']')
    elif 'BUILD_MAP' in content:
        args_count = int(content.split('BUILD_MAP')[1].strip())
        merge_list = ''
        if args_count == 0:
            LOAD.insert(0, '\{\}')
        else:
            for _ in range(args_count * 2):
                merge_list += LOAD.pop(0)
            LOAD.insert(0, '{' + merge_list + '}')
    elif 'BUILD_TUPLE' in content:
        args_count = int(content.split('BUILD_TUPLE')[1].strip())
        merge_list = ''
        if args_count == 0:
            LOAD.insert(0, '()')
        else:
            for _ in range(args_count):
                merge_list += LOAD.pop(0)
            LOAD.insert(0, '(' + merge_list + ')')
    elif 'BUILD_CONST_KEY_MAP' in content:
        args_count = int(content.split('BUILD_CONST_KEY_MAP')[1].strip())
        merge_list = ''
        if args_count == 0:
            LOAD.insert(0, '()')
        else:
            # 키 튜플을 포함해 pop
            for _ in range(args_count + 1):
                merge_list += LOAD.pop(0)
            LOAD.insert(0, 'KEY_MAP')


def store_attr(idx, shared_variables):
    byte_code = shared_variables.byte_code
    keys_list = shared_variables.keys_list

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


def call_function(func_offset, shared_variables):
    LOAD = shared_variables.LOAD
    called_func = None

    try:
        if LOAD[func_offset] == '__build_class__':
            pass
        else:
            called_func = LOAD[func_offset]

            # Special handling for ctypes_function decorator calls
            if 'ctypes_function' in str(called_func):
                print(
                    f"[CALL_FUNCTION DEBUG] Processing ctypes_function call: {called_func}")
                print(
                    f"[CALL_FUNCTION DEBUG] Full LOAD stack: {LOAD[:func_offset+3]}")

                # Try to extract the actual function name from arguments
                # ctypes_function typically takes (name, argtypes, restype) as arguments
                # The function name should be in the stack as a string argument
                for i in range(min(func_offset, len(LOAD))):
                    item = LOAD[i]
                    if isinstance(item, str) and not item.startswith('(') and not item.startswith('[') and not item.startswith('function'):
                        # This might be the C function name
                        if len(item) > 2 and item.replace('_', '').replace('-', '').isalnum():
                            print(
                                f"[CALL_FUNCTION DEBUG] Potential C function name found: {item}")
                            # Create a better representation for the ctypes function
                            called_func = f"ctypes_function({item})"
                            break
    except:
        return '__bug__'

    return called_func


def call_function_stack(func_offset, shared_variables):
    # FIXME: 함수 결과를 np.ediff1d(('to_begin', 'to_end'to_endto_beginunique_pcts) 이렇게 모호하게 하지 말고 result of np.ediff1d 처럼 저장하는게 좋을듯
    LOAD = shared_variables.LOAD

    call_result = ''

    # 호출되는 함수와 인자들을 pop
    call_result += LOAD.pop(func_offset)
    call_result += '('
    for _ in range(func_offset):
        call_result += LOAD.pop(0)
    call_result += ')'
    LOAD.insert(0, call_result)


def call_method(content, shared_variables):
    LOAD = shared_variables.LOAD

    method_offset = int(content.split('CALL_METHOD')[1].strip())
    called_method = LOAD[method_offset]

    call_result = ''
    # 호출되는 메서드와 상위 객체, 인자들을 pop
    for _ in range(method_offset + 1):
        try:
            call_result += LOAD.pop(0)
        except:
            raise

    LOAD.insert(0, call_result)

    return called_method


def list_extend(content, shared_variables):
    # 스택의 상단부터 취합해 N 번째에 있는 리스트를 확장하지만 확장된 리스트 정보는 필요하지 않으므로 pop만 수행함.
    args_count = int(content.split('LIST_EXTEND')[1].strip())
    for i in range(args_count):
        shared_variables.LOAD.pop(0)


def pop2_push1(shared_variables):
    shared_variables.LOAD.pop(0)
    shared_variables.LOAD.pop(0)
    shared_variables.LOAD.insert(0, 'pop2_push1')


def setup_finally(shared_variables):
    shared_variables.LOAD.insert(0, 'tryblock')


def pop(shared_variables):
    try:
        shared_variables.LOAD.pop(0)
    except IndexError:
        return


def dup(shared_variables):
    shared_variables.LOAD.insert(0, shared_variables.LOAD[0])
