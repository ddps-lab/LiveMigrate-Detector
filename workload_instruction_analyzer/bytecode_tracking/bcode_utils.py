import dis
import marshal
import io
from contextlib import redirect_stdout

print("=== DEBUG: bcode_utils.py imported ===")


def read_pyc(path):
    print(f"=== DEBUG: Reading pyc file: {path} ===")
    try:
        with open(path, 'rb') as f:
            # Python 3.7 이상에서 .pyc 파일의 헤더는 16바이트입니다
            header = f.read(16)
            print(f"=== DEBUG: Read {len(header)} bytes header ===")
            # marshal 모듈을 사용하여 코드 객체를 로드합니다
            code_obj = marshal.load(f)
            print(f"=== DEBUG: Successfully loaded code object ===")
    except Exception as e:
        print(f"=== ERROR: Failed to read pyc file {path}: {e} ===")
        raise

    return code_obj


def preprocessing_bytecode(byte_code):
    print(f"=== DEBUG: Preprocessing bytecode ===")

    # 라인 번호를 추출하기 위한 함수
    def parse_bytecode_line(bytecode_line):
        parts = bytecode_line.strip().split()
        line_number = 0

        if not parts:
            return None, None, line_number

        # 141         176 LOAD_CONST               3 (1)
        if parts[1].isdigit():
            # >>  142 LOAD_CONST               2 (None)
            if parts[0] != '>>':
                line_number = parts[0]
            offset = parts[1]
            content = parts[2:]
        # 126     >>  150 RERAISE                  0
        elif parts[1] == '>>':
            line_number = parts[0]
            offset = parts[2]
            content = parts[3:]
        else:
            offset = parts[0]
            content = parts[1:]

        return int(offset), ' '.join(content), int(line_number)

    '''
    바이트코드를 main과 def 파트로 구분해 각각 반환.
    '''
    dis_bytecode = {}
    dis_objects = []
    list_def_bcode_block_start_offsets = []

    cleanup = set()  # 바이트코드 상에 추가되는 클린업 코드(유저가 작성하지 않음)

    # StringIO 객체를 생성
    f = io.StringIO()
    # dis의 출력을 StringIO 객체로 리디렉션
    try:
        with redirect_stdout(f):
            dis.dis(byte_code)
        print(f"=== DEBUG: Disassembled bytecode ===")
    except Exception as e:
        print(f"=== ERROR: Failed to disassemble bytecode: {e} ===")
        raise

    # StringIO 객체에서 값을 얻고, 이를 줄 단위로 분할
    dis_output = f.getvalue()
    codes = dis_output.split('Disassembly of <code object')[
        0].strip().split('\n')
    print(f"=== DEBUG: Main code has {len(codes)} lines ===")

    objects = dis_output.split('Disassembly of <code object')[1:]
    print(f"=== DEBUG: Found {len(objects)} code objects ===")

    for i, obj in enumerate(objects):
        objects[i] = obj.strip().split('\n')

    # 바이트코드의 main 부분
    main_bcode_block_start_offsets = []
    processed_lines = 0
    for line in codes:
        offset, content, line_number = parse_bytecode_line(line)

        # 소스코드 기준 새로운 라인
        if line_number != 0:
            bcode_block_number = line_number
            main_bcode_block_start_offsets.append(offset)

        if not isinstance(offset, int):
            continue

        # 유저가 작성하지 않은 코드를 트래킹에서 제외
        # With, Try 등의 클린업 코드
        if 'SETUP_WITH' in content or 'SETUP_ASYNC_WITH' in content:
            cleanup.add(bcode_block_number)
            bcode_block_number += 1

        if bcode_block_number in cleanup:
            continue

        dis_bytecode[offset] = content
        processed_lines += 1

    print(f"=== DEBUG: Processed {processed_lines} main bytecode lines ===")

    processed_objects = 0
    for obj in objects:
        dis_object = {}
        first_line = obj[0].split()

        dis_object['__name'] = first_line[0]
        dis_object['__addr'] = first_line[2].replace(',', '')
        obj.pop(0)

        def_bcode_block_start_offsets = []
        object_processed_lines = 0
        for line in obj:
            offset, content, line_number = parse_bytecode_line(line)

            if line_number != 0:
                bcode_block_number = line_number
                def_bcode_block_start_offsets.append(offset)
            # line_number가 0이면 새로운 라인이 아니라는 뜻
            elif line_number == 0:
                line_number = bcode_block_number

            if not isinstance(offset, int):
                continue

            if 'SETUP_WITH' in content or 'SETUP_ASYNC_WITH' in content:
                cleanup.add(bcode_block_number)
                bcode_block_number += 1

            if line_number in cleanup:
                continue

            dis_object[offset] = content
            object_processed_lines += 1

        dis_objects.append(dis_object)
        list_def_bcode_block_start_offsets.append(
            def_bcode_block_start_offsets)
        processed_objects += 1
        print(
            f"=== DEBUG: Processed object {processed_objects}: {dis_object['__name']} with {object_processed_lines} lines ===")

    print(
        f"=== DEBUG: Preprocessing completed - {len(dis_bytecode)} main instructions, {len(dis_objects)} objects ===")
    return dis_bytecode, dis_objects, main_bcode_block_start_offsets, list_def_bcode_block_start_offsets


def postprocessing_defmap(DEF_MAP, addr_map):
    '''
    함수 이름 중복을 구분하기 위해 상위 객체까지 이름에 포함.
    상위 객체의 주소를 이름으로 치환.
    '''
    print(
        f"=== DEBUG: Postprocessing definition map with {len(DEF_MAP)} entries ===")

    obj_addrs = addr_map.keys()
    def_map = DEF_MAP.copy()
    processed_count = 0

    for key, _ in def_map.items():
        if key.split('.')[0] in obj_addrs:
            parent, value = next(iter(addr_map[key.split('.')[0]].items()))
            # 생성자는 클래스 할당 함수에 포함
            if value == '__init__':
                replace = parent
            else:
                replace = parent + '.' + value
            DEF_MAP[replace] = DEF_MAP.pop(key)
            processed_count += 1
            print(f"=== DEBUG: Replaced {key} -> {replace} ===")
        else:
            new_key = key.split('.')[1]
            DEF_MAP[new_key] = DEF_MAP.pop(key)
            processed_count += 1
            print(f"=== DEBUG: Simplified {key} -> {new_key} ===")

    print(
        f"=== DEBUG: Postprocessing completed, processed {processed_count} entries ===")


def scan_definition(definitions):
    '''
    사용자 정의 객체를 수집.
    '''
    print(
        f"=== DEBUG: Scanning definitions for {len(definitions)} objects ===")

    obj_lists = []
    obj_sets = set()

    for obj in definitions:
        __name = obj['__name']
        __addr = obj['__addr']

        obj_sets.add(__name)
        obj_lists.append({__name: __addr})
        print(f"=== DEBUG: Found definition: {__name} at {__addr} ===")

    print(
        f"=== DEBUG: Scan completed, found {len(obj_sets)} unique objects ===")
    return obj_sets, obj_lists


def merge_dictionaries(dictA, dictB):  # 이게 전체 트래킹 버전
    print(
        f"=== DEBUG: Merging dictionaries - A has {len(dictA)} entries, B has {len(dictB)} entries ===")

    merged_count = 0
    for key, value in dictB.items():
        # __builtin, __user_def 처리
        if isinstance(value, set):
            if key in dictA and isinstance(dictA[key], set):
                original_size = len(dictA[key])
                dictA[key].update(value)
                added = len(dictA[key]) - original_size
                merged_count += added
                if added > 0:
                    print(
                        f"=== DEBUG: Merged {added} items into {key} set ===")
            else:
                dictA[key] = value.copy()
                merged_count += len(value)
                print(
                    f"=== DEBUG: Added new set {key} with {len(value)} items ===")
        # 모듈 처리
        elif isinstance(value, dict):
            # dictB.key(module)가 dictA에도 존재한다면 dictA,B의 __called를 병합
            if key in dictA and '__called' in dictA[key]:
                try:
                    # FIXME: alias 중복에 대한 처리 - 기존 모듈을 트래킹에서 누락시킴
                    if dictA[key]['__origin_name'] != value['__origin_name']:
                        dictA[key] = value
                        print(
                            f"=== DEBUG: Replaced module {key} due to origin name mismatch ===")
                        continue
                except KeyError:
                    pass
                original_size = len(dictA[key]['__called'])
                dictA[key]['__called'].update(value['__called'])
                added = len(dictA[key]['__called']) - original_size
                merged_count += added
                if added > 0:
                    print(
                        f"=== DEBUG: Merged {added} functions into module {key} ===")
            else:
                # dictA[key]가 존재하지 않거나 __called 키가 없는 경우 새로운 딕셔너리와 세트를 생성
                if key not in dictA:
                    dictA[key] = {}
                dictA[key]['__called'] = value['__called'].copy()
                merged_count += len(value['__called'])
                print(
                    f"=== DEBUG: Added new module {key} with {len(value['__called'])} functions ===")

            try:
                dictA[key]['__origin_name'] = value['__origin_name']
                dictA[key]['__from'] = value['__from']
            except KeyError:
                pass

    print(f"=== DEBUG: Merge completed, added {merged_count} total items ===")
    return dictA


def find_unique_keys_values(A, B):
    """
    B에만 존재하는 키와 값을 찾아 새 딕셔너리로 반환하며,
    A와 B에 동일한 키가 있지만 값이 다른 경우도 포함한다.

    :param A: 비교 대상이 되는 첫 번째 딕셔너리
    :param B: 비교 대상이 되는 두 번째 딕셔너리
    :return: B에만 존재하는 키와 값 또는 값이 다른 키와 값이 포함된 새 딕셔너리
    """
    print(
        f"=== DEBUG: Finding unique keys/values - A has {len(A)} entries, B has {len(B)} entries ===")

    unique_to_B = {key: value for key, value in B.items()
                   if key not in A or A[key] != value}

    unique_to_B.pop('__builtin', None)
    unique_to_B.pop('__user_def', None)

    print(f"=== DEBUG: Found {len(unique_to_B)} unique entries ===")
    for key in list(unique_to_B.keys())[:5]:  # Show first 5
        print(f"=== DEBUG: Unique entry: {key} ===")
    if len(unique_to_B) > 5:
        print(
            f"=== DEBUG: ... and {len(unique_to_B) - 5} more unique entries ===")

    return unique_to_B


def dict_empty_check(dictionary):
    """
    딕셔너리가 비어있는지 확인하는 함수
    """
    if not dictionary:
        return True

    for key, value in dictionary.items():
        if key in ['__builtin', '__user_def']:
            if value:  # set이 비어있지 않으면
                return False
        else:
            if isinstance(value, dict) and '__called' in value and value['__called']:
                return False

    is_empty = True
    print(f"=== DEBUG: Dictionary empty check result: {is_empty} ===")
    return is_empty
