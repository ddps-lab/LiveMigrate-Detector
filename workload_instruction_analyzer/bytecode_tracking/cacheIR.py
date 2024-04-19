import dis
import marshal

def read_pyc(path):
    with open(path, 'rb') as f:
        # Python 3.7 이상에서 .pyc 파일의 헤더는 16바이트입니다
        f.read(16)
        # marshal 모듈을 사용하여 코드 객체를 로드합니다
        code_obj = marshal.load(f)
    
    print(code_obj)
    return code_obj

path = '/home/ubuntu/.local/lib/python3.10/site-packages/numpy/__pycache__/__init__.cpython-310.pyc'
# path = '/usr/lib/python3.10/collections/__pycache__/abc.cpython-310.pyc'
# path = '/usr/lib/python3.10/importlib/__pycache__/__init__.cpython-310.pyc'
dis.dis(read_pyc(path))