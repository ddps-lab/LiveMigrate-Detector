import time

import example
import testpymodule
import temp2
from temp import tempfunc1 as t, tempfunc2
import importlib
import xml.parsers.expat.model
import collections.abc as asdgsadg
import numpy as np

# 두 행렬 A와 B 정의
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])

# 행렬 곱 계산
C = np.matmul(A, B)

class ExampleClass:
    def __init__(self, value):
        self.value = value

    def example_method(self):
        print(f"The value is {self.value}")

def asd():
    print('asd')
    C = np.matmul(A, B)
    math = importlib.import_module("math")
    return ttttest(C)

def ttttest(tlist):
    print(tlist)
    return 1

# 동적으로 모듈 임포트
math = importlib.import_module("math")
# 제곱근 계산 예제
number = 16
sqrt_number = math.sqrt(number)
print(f"The square root of {number} is {sqrt_number}")

testpymodule.print_isa_set()
result = example.add(3, 4)
print(result)

tlist = [0,1,2]
num = ttttest(tlist)

# 클래스의 인스턴스를 생성합니다.
example_instance = ExampleClass(10)

# 인스턴스 메서드를 호출합니다.
example_instance.example_method()

asd()

class InnerClass:
    def inner_method(self, arg1):
        print(f"Inner method called {arg1}")

class OuterClass:
    def __init__(self):
        self.inner_obj = InnerClass()

if __name__ == '__main__':
    # 객체 생성 및 메서드 호출
    outer = OuterClass()
    outer.inner_obj.inner_method('ttt')
    t()
    tempfunc2()
    time.sleep(10000)