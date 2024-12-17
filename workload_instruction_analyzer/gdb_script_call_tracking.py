import gdb
from collections import OrderedDict
import time

import sys
import io

check = False

def step_instruction():
    try:
        gdb.execute("stepi", to_string=True)
    except gdb.error as e:
        return False
    return True

def is_register_call():
    global check

    transfer_instructions = set(('call', 'jmp', 'ja', 'jnbe', 'jae', 'jnb', 'jb', 'jnae', 'jbe', 'jna', 'jc', 'je', 'jz', 'jnc', 'jne', 'jnz', 
    'jnp', 'jpo', 'jp', 'jpe', 'jcxz', 'jecxz', 'jg', 'jnle', 'jge', 'jnl', 'jl', 'jnge', 'jle', 'jng', 'jno', 'jns', 'jo', 'js'))
    try:
        result = gdb.execute("x/i $pc", to_string=True)
    except gdb.error as e:
        return
    
    result = result.strip().split(':')[1].strip()
    instruction = result.split(' ')[0]
    
    comment = ''
    if '#' in result:
        comment = result.split('#')[1]

    if '+' in comment:
        return
    
    if instruction in transfer_instructions:
        if not '<' in result:
            print(f"\033[91m{result}\033[0m")
            check = True

    return

def tracking():
    global check

    functions = OrderedDict()
    registers = OrderedDict()
    
    gdb.execute(f"break _start")
    gdb.execute(f"run")
    gdb.execute(f"continue")

    while(True):
        try:
            disas_result = gdb.execute(f"disas", to_string=True)
            lines = disas_result.split('\n')
        except gdb.error as e:
            if not step_instruction():
                break
            continue

        for line in lines:
            if 'Dump of assembler code for function' in line:
                func_name = line.split('function ')[1].split(':')[0]
                if '@plt' in func_name:
                    continue
                functions[func_name] = None

                if check:
                    print(f"\033[91m{func_name}\033[0m")
                    registers[func_name] = None
                    check = False
                break

        is_register_call()

        if not step_instruction():
            break
    
    print(list(functions.keys()))
    print(len(functions))

    print(list(registers.keys()))
    print(len(registers))

if __name__ == '__main__':
    start_time = time.time()
    gdb.execute("set pagination off")

    tracking()

    end_time = time.time()
    total_time = end_time - start_time

    print(f'time: {total_time}')