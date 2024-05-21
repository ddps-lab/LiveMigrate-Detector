import subprocess
import struct
# from capstone import *
from elftools.elf.elffile import ELFFile

from pprint import pprint

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

# def disassemble_memory(data, address):
#     # Capstone 엔진 초기화
#     md = Cs(CS_ARCH_X86, CS_MODE_64)
    
#     # 디스어셈블링
#     for insn in md.disasm(data, address):
#         print("0x%x:\t%s\t%s" % (insn.address, insn.mnemonic, insn.op_str))

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
        idx1 = result.stdout.splitlines()[0]
        idx2 = result.stdout.splitlines()[1]

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
    variables_addr, variables_name = get_filtered_variables(binary_file)
    pointer_size = 8
    pointer_format = '<Q'  # 64비트 포인터 (리틀 엔디안)

    variables = {name: (addr, pointer_size) for name, addr in zip(variables_name, variables_addr)}
    pprint(variables)

    infer_results = {}
    with open(binary_file, 'rb') as f:
        elffile = ELFFile(f)
        
        for var_name, (struct_address, pointer_size) in variables.items():
            print(f"\nReading {var_name} at address 0x{struct_address:x} (pointer size: {pointer_size} bytes)")
            
            # 구조체의 첫 번째 필드를 읽음 (포인터)
            struct_offset = get_file_offset(elffile, struct_address)
            if struct_offset is None:
                print(f"Error: Could not find file offset for address 0x{struct_address:x}")
                continue
            
            pointer_data = read_binary_data(binary_file, struct_offset, pointer_size)
            
            (string_address,) = struct.unpack(pointer_format, pointer_data)
            print(f"Pointer in {var_name} points to address 0x{string_address:x}")

            if string_address < 0xffff:
                continue
            
            # 포인터가 가리키는 주소에서 문자열 읽기
            string_offset = get_file_offset(elffile, string_address)
            if string_offset is None:
                print(f"Error: Could not find file offset for address 0x{string_address:x}")
                continue
            
            string_data = read_binary_data(binary_file, string_offset, 256)  # 최대 256 바이트 읽기 (필요에 따라 조정)
            
            # 문자열 추출
            string_value = extract_string(string_data)
            print(f"String Value: {string_value}")

            if string_value == None:
                continue
            
            infer_results[var_name] = string_value

        pprint(infer_results)
            # # 디스어셈블링
            # print(f"\nDisassembly of data at pointer address (0x{string_address:x}):")
            # disassemble_memory(string_data, string_address)