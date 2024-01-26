import bcode_instructions

def parse_def(byte_code, addr_map, obj_sets):
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
            bcode_instructions.pop(LOAD)
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
                # call_map[LOAD[-1]] = result
                # 나중에 객체 할당 구조를 파악하도록 해서 userobj.some() 형태의 호출 시 userobj가 userclass의 객체임을 파악할 수 있도록..
                pass
        elif 'CALL_FUNCTION' in line:
            called_objs.add(bcode_instructions.call_function(byte_code, i, LOAD, parents_object))
        elif 'CALL_METHOD' in line:
            called_objs.add(bcode_instructions.call_method(byte_code, i, LOAD, parents_object))

        # next line(source code)
        if line.strip() == '':
            LOAD, parents_object = [], []
    
    return called_objs