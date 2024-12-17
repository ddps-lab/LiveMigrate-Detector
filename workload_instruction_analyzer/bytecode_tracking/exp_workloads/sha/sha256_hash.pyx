from libc.stdlib cimport malloc, free
from cpython.bytes cimport PyBytes_FromStringAndSize

# 외부 C 함수 및 구조체 선언
cdef extern from "openssl/sha.h":
    ctypedef struct SHA256_CTX:
        pass

    int SHA256_Init(SHA256_CTX *c)
    int SHA256_Update(SHA256_CTX *c, const unsigned char *data, size_t len)
    int SHA256_Final(unsigned char *md, SHA256_CTX *c)

# Python에서 호출할 수 있는 함수로 수정
def sha256_hash(bytes message) -> bytes:
    cdef SHA256_CTX sha256
    cdef unsigned char* hash = <unsigned char*>malloc(32 * sizeof(unsigned char))
    cdef Py_ssize_t length = len(message)
    
    # SHA-256 컨텍스트 초기화
    if SHA256_Init(&sha256) != 1:
        free(hash)
        raise RuntimeError("SHA256_Init failed")
    
    # 해시 계산
    if SHA256_Update(&sha256, message, length) != 1:
        free(hash)
        raise RuntimeError("SHA256_Update failed")
    
    if SHA256_Final(hash, &sha256) != 1:
        free(hash)
        raise RuntimeError("SHA256_Final failed")
    
    # 결과를 Python 바이트 객체로 변환 (char*로 캐스팅)
    py_hash = PyBytes_FromStringAndSize(<char*>hash, 32)
    
    # 메모리 해제
    free(hash)
    
    return py_hash