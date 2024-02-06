from pathlib import Path
import sys
import os

import ctypes
import time

rootdir = str(Path(__file__).resolve().parent)
sys.path.append(rootdir)

# FIXME: 아래처럼 변수로 라이브러리를 로드하는 경우 변수 값을 모름..
# libpath = rootdir + '/libxedwrapper.so'
# libxedwrapper = ctypes.CDLL(libpath)

# xed wrapper 라이브러리 로드
libxedwrapper = ctypes.CDLL(f'{rootdir}/libxedwrapper.so')

class XedResult(ctypes.Structure):
    _fields_ = [("isa_set", ctypes.c_char_p),
                ("disassembly", ctypes.c_char_p)]

# 함수 프로토타입 정의
libxedwrapper.print_isa_set.argtypes = [ctypes.c_char_p]
libxedwrapper.print_isa_set.restype = XedResult

def print_isa_set():
    result = libxedwrapper.print_isa_set('c5f9efc0'.encode())
    print(result.isa_set.decode('utf-8'))
    print(result.disassembly.decode('utf-8'))