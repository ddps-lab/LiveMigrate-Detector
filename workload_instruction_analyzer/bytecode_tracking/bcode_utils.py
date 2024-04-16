import dis
import marshal
import io
from contextlib import redirect_stdout

from pprint import pprint

def read_pyc(path):
    with open(path, 'rb') as f:
        # Python 3.7 이상에서 .pyc 파일의 헤더는 16바이트입니다
        f.read(16)
        # marshal 모듈을 사용하여 코드 객체를 로드합니다
        code_obj = marshal.load(f)
    
    return code_obj

def preprocessing_bytecode(byte_code):
    # 라인 번호를 추출하기 위한 함수
    def parse_bytecode_line(bytecode_line):
        parts = bytecode_line.strip().split()
        line_number = 0

        if not parts:
            return None, None, line_number

        # code line number 제외
        if parts[1].isdigit():
            line_number = parts[0]
            offset = parts[1]
            content = parts[2:]
        elif parts[1] == '>>':
            line_number = parts[0]
            offset = parts[2]
            content = parts[3:]
        else:
            offset = parts[0]
            content = parts[1:]

        return int(offset), ' '.join(content), line_number
    
    '''
    바이트코드를 main과 def 파트로 구분해 각각 반환.
    '''
    dis_bytecode = {}
    dis_objects = []

    cleanup = set() # 바이트코드 상에 추가되는 클린업 코드(유저가 작성하지 않음)

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

    for line in codes:
        offset, content, line_number = parse_bytecode_line(line)
        if not isinstance(offset, int):
            continue

        # 유저가 작성하지 않은 코드를 트래킹에서 제외
        # With, Try 등의 클린업 코드
        if 'SETUP_WITH' in content:
            cleanup.add(line_number)
            line_number += 1
        
        if line_number in cleanup:
            continue

        dis_bytecode[offset] = content
    
    for obj in objects:
        dis_object = {}
        first_line = obj[0].split()

        dis_object['__name'] = first_line[0]
        dis_object['__addr'] = first_line[2].replace(',', '')
        obj.pop(0)
        for line in obj:
            offset, content, line_number = parse_bytecode_line(line)
            if not isinstance(offset, int):
                continue

            if 'SETUP_WITH' in content:
                cleanup.add(line_number)
                line_number += 1
            
            if line_number in cleanup:
                continue

            dis_object[offset] = content

        dis_objects.append(dis_object)

    return dis_bytecode, dis_objects

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

def scan_definition(definitions):
    '''
    사용자 정의 객체를 수집.
    '''
    obj_lists = []
    obj_sets = set()
    
    for obj in definitions:
        __name = obj['__name']
        __addr = obj['__addr']

        obj_sets.add(__name)
        obj_lists.append({__name:__addr})

    return obj_sets, obj_lists

def merge_dictionaries(dictA, dictB):
    for key, value in dictB.items():
        if isinstance(value, set):
            # dictB.key의 값이 비어있는 세트가 아닌 경우에만 업데이트
            if value:
                if key in dictA and isinstance(dictA[key], set):
                    dictA[key].update(value)
                else:
                    dictA[key] = value.copy()
        elif isinstance(value, dict):
            # dictB.key의 값이 딕셔너리인 경우, __called 키의 세트를 업데이트
            if '__called' in value and value['__called']:
                if key in dictA and '__called' in dictA[key] and isinstance(dictA[key]['__called'], set):
                    dictA[key]['__called'].update(value['__called'])
                else:
                    # dictA[key]가 존재하지 않거나 __called 키가 없는 경우 새로운 딕셔너리와 세트를 생성
                    if key not in dictA:
                        dictA[key] = {}
                    dictA[key]['__called'] = value['__called'].copy()

    return dictA

def dict_empty_check(input_dict):
    for key, value in input_dict.items():
        if isinstance(value, dict) and '__called' in value:
            # __called 키의 값이 세트이고 비어 있지 않으면 False 반환
            if not value['__called'].issubset(set()):
                return False
        elif isinstance(value, set) and value:
            # 값이 비어 있지 않은 세트인 경우 False 반환
            return False
    # 모든 검사를 통과했다면, 모든 세트가 비어 있음
    return True