import dis
import marshal
import io
from contextlib import redirect_stdout

def read_pyc(path):
    with open(path, 'rb') as f:
        # Python 3.7 이상에서 .pyc 파일의 헤더는 16바이트입니다
        f.read(16)
        # marshal 모듈을 사용하여 코드 객체를 로드합니다
        code_obj = marshal.load(f)
    
    return code_obj

def preprocessing_bytecode(byte_code):
    '''
    바이트코드를 main과 def 파트로 구분해 각각 반환.
    '''
    # StringIO 객체를 생성
    f = io.StringIO()
    # dis의 출력을 StringIO 객체로 리디렉션
    with redirect_stdout(f):
        dis.dis(byte_code)

    # StringIO 객체에서 값을 얻고, 이를 줄 단위로 분할
    dis_output = f.getvalue()
    codes = dis_output.split('Disassembly of <code object')[0].strip().split('\n')
    objects = dis_output.split('Disassembly of <code object')[1:]
    for i, obj in enumerate(objects):
        objects[i] = obj.strip().split('\n')

    return codes, objects

def postprocessing_defmap(DEF_MAP, addr_map):
    '''
    함수 이름 중복을 구분하기 위해 상위 객체까지 이름에 포함.
    상위 객체의 주소를 이름으로 치환.
    '''
    obj_addrs = addr_map.keys()
    def_map = DEF_MAP.copy()
    for key, _ in def_map.items():
        if key.split('.')[0] in obj_addrs:
            parent, value = next(iter(addr_map[key.split('.')[0]].items()))
            # 생성자는 클래스 할당 함수에 포함
            if value == '__init__':
                replace = parent
            else:
                replace = parent + '.' + value
            DEF_MAP[replace] = DEF_MAP.pop(key)
        else:
            DEF_MAP[key.split('.')[1]] = DEF_MAP.pop(key)

def parse_definition(definitions):
    '''
    사용자 정의 객체를 수집.
    '''
    obj_lists = []
    obj_sets = set()
    for i in range(len(definitions)):
        obj = definitions[i][0].split(' ')[0]
        addr = definitions[i][0].split('at ')[1].split(',')[0].strip()
        obj_sets.add(obj)
        obj_lists.append({obj:addr})

    return obj_sets, obj_lists