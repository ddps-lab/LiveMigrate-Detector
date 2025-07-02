from setuptools import setup, Extension

# C 확장 모듈 정의
int8dot_module = Extension(
    'int8dot',                         # 최종 모듈 이름 (import int8dot)
    sources=['int8dot_module.c'],      # 컴파일할 소스 파일
    extra_compile_args=['-fPIC']  # 최적화 및 위치 독립 코드 옵션
)

setup(
    name='int8dot',
    version='1.0',
    description='Python interface for high-performance int8 dot product',
    ext_modules=[int8dot_module]
)
