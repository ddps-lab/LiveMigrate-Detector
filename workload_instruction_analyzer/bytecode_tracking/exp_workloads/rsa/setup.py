from setuptools import setup, Extension
from Cython.Build import cythonize

# OpenSSL 라이브러리 경로 확인 (예시 경로, 환경에 따라 다를 수 있음)
openssl_include_dir = "/usr/include/openssl"
openssl_library_dir = "/home/ubuntu/openssl-openssl-3.1.3"

extensions = [
    Extension(
        "rsa",
        sources=["rsa.pyx"],
        include_dirs=[openssl_include_dir],
        library_dirs=[openssl_library_dir],
        libraries=["crypto", "ssl"],  # OpenSSL 라이브러리 링크
    )
]

setup(
    name="rsa",
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}),
)
