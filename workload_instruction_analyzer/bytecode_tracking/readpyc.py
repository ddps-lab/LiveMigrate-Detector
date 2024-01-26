import dis
import marshal
import types
import sys
import os

def read_pyc(filename):
    with open(filename, 'rb') as f:
        # Python 3.7 이상에서 .pyc 파일의 헤더는 16바이트입니다
        f.read(16)
        # marshal 모듈을 사용하여 코드 객체를 로드합니다
        code_obj = marshal.load(f)
        # 바이트코드 디스어셈블
        dis.dis(code_obj)

# 사용 예시
rootdir = os.path.dirname(os.path.abspath(__file__))
read_pyc(f'{rootdir}/__pycache__/testpymodule.cpython-310.pyc')
