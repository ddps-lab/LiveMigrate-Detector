import subprocess
import struct
from elftools.elf.elffile import ELFFile

from pprint import pprint

def get_func_list(binary_file):
    command = (
        "readelf -Ws -s "
        f"{binary_file} "
        " | awk '$4 == \"FUNC\" && ($6 == \"DEFAULT\" || $6 == \"HIDDEN\" || $6 == \"PROTECTED\") && $7 != \"UND\" {print $2}'"
    )

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    func_addrs = set()
    for addr in result.stdout.splitlines():
        func_addrs.add(hex(int(addr,16)))

    return func_addrs

def get_file_offset(elffile, address):
    # 프로그램 헤더를 통해 가상 주소를 파일 오프셋으로 변환
    for segment in elffile.iter_segments():
        if segment['p_type'] == 'PT_LOAD':
            vaddr = segment['p_vaddr']
            memsz = segment['p_memsz']
            offset = segment['p_offset']
            if vaddr <= address < vaddr + memsz:
                return address - vaddr + offset
    return None

def read_binary_data(binary_file, offset, size):
    # 바이너리 파일에서 특정 오프셋의 데이터를 읽습니다.
    with open(binary_file, 'rb') as f:
        f.seek(offset)
        return f.read(size)

def extract_string(data):
    # 문자열 추출 (예시로 첫 번째 null-terminated 문자열만 추출)
    string_value = None
    try:
        string_value = data.split(b'\x00', 1)[0].decode('utf-8')
    except:
        # 첫 번째 필드가 문자열 포인터(8바이트)가 아닌 경우
        pass
    return string_value

def get_filtered_variables(lib):
    def get_section_idx():
        command = (
            "readelf -S "
            f"{lib} "
            "| awk '/\.data/ {match($0, /\[[0-9]+\]/); print substr($0, RSTART+1, RLENGTH-2)}'"
        )

        # .data, .data.rel.ro -> 프로그램 시작 시 초기화된 후, 읽기 전용으로 변환되는 데이터를 포함. 예를 들어, const 로 선언된 변수들.
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        indexes = result.stdout.splitlines()
        idx1 = result.stdout.splitlines()[0]

        if len(indexes) > 1:
            idx2 = result.stdout.splitlines()[1]
        else:
            idx2 = None

        return idx1, idx2
    
    def get_variables(idx1, idx2):
        command = (
            "readelf -Ws --syms "
            f"{lib} "
            f"| awk '$4 == \"OBJECT\" && ($7 == \"{idx1}\" || $7 == \"{idx2}\") && $3 >= 32'"
        )
    
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        variables_addr = []
        variables_name = []
        for line in result.stdout.splitlines():
            addr = '0x' + list(filter(None, line.split(' ')))[1]
            addr = int(addr, 16)
            name = list(filter(None, line.split(' ')))[-1]

            variables_addr.append(addr)
            variables_name.append(name)


        return variables_addr, variables_name

    idx1, idx2 = get_section_idx()
    variables_addr, variables_name = get_variables(idx1, idx2)

    return variables_addr, variables_name


'''
.data, .data.rel.ro 섹션의 모든 global, static 변수를 조회하여 PyMethodDef 타입의 변수를 추론

struct PyMethodDef {
    const char  *ml_name;   /* The name of the built-in function/method */
    PyCFunction ml_meth;    /* The C function that implements it */
    int         ml_flags;   /* Combination of METH_xxx flags, which mostly
                               describe the args expected by the C func */
    const char  *ml_doc;    /* The __doc__ attribute, or NULL */
};
typedef struct PyMethodDef PyMethodDef;
'''
def infer_global_variable_type(binary_file):
    '''
    METH_VARARGS : 0x1
    METH_KEYWORDS : 0x2 # 다른 플래그와 조합해서만 사용 가능
    METH_VARARGS | METH_KEYWORDS : 0x3
    METH_NOARGS : 0x4
    METH_O : 0x8
    METH_CLASS : 0x10
    METH_CLASS | METH_O : 0x18 # 공식문서에 없는건데
    METH_STATIC : 0x20
    METH_COEXIST : 0x40
    METH_FASTCALL : 0x80
    METH_FASTCALL | METH_KEYWORDS : 0x82
    METH_STACKLESS : 0x100
    METH_METHOD : 0x200 # 다른 플래그와 조합해서만 사용 가능
    METH_METHOD | METH_FASTCALL | METH_KEYWORDS : 0x282
    '''
    ml_flags = (0x1, 0x3, 0x4, 0x8, 0x10, 0x18, 0x20, 0x40, 0x80, 0x82, 0x100, 0x282)

    variables_addr, variables_name = get_filtered_variables(binary_file)
    pointer_size = 8
    pointer_format = '<Q'  # 64비트 포인터 (리틀 엔디안)

    variables = {name: (addr, pointer_size) for name, addr in zip(variables_name, variables_addr)}

    infer_results = {}
    func_addrs = get_func_list(binary_file)

    with open(binary_file, 'rb') as f:
        elffile = ELFFile(f)
        
        for var_name, (struct_address, pointer_size) in variables.items():
            # 메모리 주소를 파일 오프셋으로 변환
            struct_offset = get_file_offset(elffile, struct_address)
            
            # 구조체의 첫 번째 필드를 읽음 (포인터)
            pointer_data = read_binary_data(binary_file, struct_offset, pointer_size)
            (string_address,) = struct.unpack(pointer_format, pointer_data)
            
            # 첫 번째 필드의 값(문자열이 담긴 주소)를 파일 오프셋으로 변환
            string_offset = get_file_offset(elffile, string_address)
            # 포인터가 가리키는 값이 주소가 아닌 경우
            if string_offset is None:
                continue
            
            # 포인터가 가리키는 주소에서 문자열 읽기
            string_data = read_binary_data(binary_file, string_offset, 256)  # 최대 256 바이트 읽기 (필요에 따라 조정)
            # 문자열 추출
            c_func_name = extract_string(string_data)
            if c_func_name == None:
                continue
            
            # 구조체의 두 번째 필드
            struct_offset = get_file_offset(elffile, struct_address + 8)
            pointer_data = read_binary_data(binary_file, struct_offset, pointer_size)
            (string_address,) = struct.unpack(pointer_format, pointer_data)
            
            # 구조체의 두 번째 필드의 값(C 함수의 주소)이 바이너리에 정의된 함수를 가리키지 않는 경우
            if hex(string_address) not in func_addrs:
                continue

            # 구조체의 세 번째 필드
            struct_offset = get_file_offset(elffile, struct_address + 16)
            pointer_data = read_binary_data(binary_file, struct_offset, pointer_size)
            (string_address,) = struct.unpack(pointer_format, pointer_data)

            if string_address not in ml_flags:
                continue

            infer_results[var_name] = c_func_name
    
    return infer_results