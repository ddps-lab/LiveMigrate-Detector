# filename: setup.py
from setuptools import setup, Extension
from Cython.Build import cythonize

openssl_include_dir = "/usr/include/openssl"
openssl_library_dir = "/home/ubuntu/openssl-openssl-3.1.3"

extensions = [
    Extension(
        "sha",
        sources=["sha256_hash.pyx"],    
        include_dirs=[openssl_include_dir],
        library_dirs=[openssl_library_dir],
        libraries=["crypto", "ssl"],  # OpenSSL 라이브러리 링크    
    )
]

setup(
    name="sha",
    ext_modules=cythonize(extensions, compiler_directives={'language_level': "3"}),
)