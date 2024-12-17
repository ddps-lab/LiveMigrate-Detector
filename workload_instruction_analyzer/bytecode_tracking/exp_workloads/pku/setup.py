from setuptools import setup, Extension

module = Extension('pku',
                   sources=['pku.c'],
                   extra_compile_args=['-pthread', '-std=gnu99', '-mpku'])

setup(name='pku',
      version='1.0',
      description='Python interface for using PKU (Protection Keys for Userspace)',
      ext_modules=[module])
