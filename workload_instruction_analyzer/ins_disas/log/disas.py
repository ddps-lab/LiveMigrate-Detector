import gdb
from pprint import pprint

disas_file = '/home/ubuntu/migration_test/ins_disas/log/disas.txt'

def get_text_sections():
    files = gdb.execute("info files", to_string=True)

    lines = files.split('\n')

    sections = []

    for line in lines:
        # If line contains ".text" save the section addresses
        # The format is 0x0000564c59c75ae0 - 0x0000564c59f24b9e is .text
        if ".text" in line:
            addresses = line.split()
            sections.append((int(addresses[0], 16), int(addresses[2], 16), ' '.join(addresses[4:])))

    return sections

def disas(start_addr, end_addr, buffered_output, call_regi):
    transfer_instructions = set(('call', 'jmp', 'ja', 'jnbe', 'jae', 'jnb', 'jb', 'jnae', 'jbe', 'jna', 'jc', 'je', 'jz', 'jnc', 'jne', 'jnz', 
    'jnp', 'jpo', 'jp', 'jpe', 'jcxz', 'jecxz', 'jg', 'jnle', 'jge', 'jnl', 'jl', 'jnge', 'jle', 'jng', 'jno', 'jns', 'jo', 'js'))
    
    disas_result = gdb.execute(f"disas /r {start_addr},{end_addr}", to_string=True)

    lines = disas_result.split('\n')

    for line in lines:

        parts = line.strip().split(":")
        parts = list(filter(None, parts))

        # If there's no instruction part, skip this line
        if len(parts) < 2:
            continue    

        # ex) "48 8d 3d bb 02 00 00	lea    rdi,[rip+0x2bb]        # 0x56116174033a <main>"
        instruction_part = parts[1].strip()
        instruction = instruction_part.split('\t')[1].split(' ')[0]

        gdb_comment = instruction_part.split(' ')[-1]

        # if '-' in line or '.cold' in line:
        #     continue

        if instruction in transfer_instructions:       
            if gdb_comment.startswith('0x'):
                buffered_output.append(line)
                continue

            if not gdb_comment.startswith('<'):
                call_regi.append(line)

        buffered_output.append(line)


if __name__ == '__main__':
    sections = get_text_sections()
    pprint(sections)

    call_regi = []
    
    seen = set()
    buffered_output = []
    for start_addr, end_addr, name in sections:
        disas(start_addr, end_addr, buffered_output, call_regi)
    
    with open(disas_file, 'w') as f:
        f.write('\n'.join(buffered_output))

    with open('call_regi.txt', 'w') as f:
        f.write('\n'.join(call_regi))