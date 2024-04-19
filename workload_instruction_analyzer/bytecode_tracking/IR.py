import dis

# with open('/usr/lib/python3.10/importlib/__init__.py', 'r') as f:
# with open('example_scripts/branch.py', 'r') as f:
# with open('example_scripts/import_test.py', 'r') as f:
with open('example_scripts/comprehension.py', 'r') as f:
# with open('test.py', 'r') as f:
# with open('example_scripts/main.py', 'r') as f:
# with open('example_scripts/testpymodule.py', 'r') as f:
    source_code = f.read()

byte_code = compile(source_code, '<string>', 'exec')
print(dis.dis(byte_code))