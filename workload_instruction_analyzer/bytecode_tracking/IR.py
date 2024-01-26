import dis

with open('main.py', 'r') as f:
    source_code = f.read()

byte_code = compile(source_code, '<string>', 'exec')
print(dis.dis(byte_code))