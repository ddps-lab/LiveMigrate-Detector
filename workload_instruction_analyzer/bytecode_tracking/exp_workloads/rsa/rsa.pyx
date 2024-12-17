from libc.stdlib cimport free
from libc.string cimport strlen

cdef extern from "stdio.h":
    int printf(const char *format, ...)

cdef extern from "openssl/evp.h":
    void OpenSSL_add_all_algorithms()
    void EVP_cleanup()
    void ERR_load_crypto_strings()
    void ERR_free_strings()

    ctypedef struct EVP_PKEY_CTX:  # OpenSSL의 EVP_PKEY_CTX 구조체 정의
        pass
    ctypedef struct EVP_PKEY:  # OpenSSL의 EVP_PKEY 구조체 정의
        pass

    EVP_PKEY_CTX* EVP_PKEY_CTX_new_id(int id, void *e)
    int EVP_PKEY_keygen_init(EVP_PKEY_CTX *ctx)
    int EVP_PKEY_CTX_set_rsa_keygen_bits(EVP_PKEY_CTX *ctx, int bits)
    int EVP_PKEY_keygen(EVP_PKEY_CTX *ctx, EVP_PKEY **ppkey)
    void EVP_PKEY_free(EVP_PKEY *pkey)
    void EVP_PKEY_CTX_free(EVP_PKEY_CTX *ctx)
    int EVP_PKEY_get_bn_param(EVP_PKEY *pkey, const char *param, BIGNUM **bn)

cdef extern from "openssl/rsa.h":
    ctypedef struct BIGNUM:  # OpenSSL의 BIGNUM 구조체 정의
        pass

    BIGNUM* BN_new()
    void BN_free(BIGNUM *a)
    int BN_bin2bn(const unsigned char *s, int len, BIGNUM *ret)
    char* BN_bn2hex(const BIGNUM *a)

    ctypedef struct BN_CTX:  # OpenSSL의 BN_CTX 구조체 정의
        pass

    void BN_CTX_free(BN_CTX *c)
    BN_CTX* BN_CTX_new()
    int BN_mod_exp(BIGNUM *r, const BIGNUM *a, const BIGNUM *p, const BIGNUM *m, BN_CTX *ctx)

cdef extern from "openssl/bn.h":
    void OPENSSL_free(void *addr)

cdef extern from "openssl/err.h":  # ERR_load_crypto_strings와 ERR_free_strings 선언
    void ERR_load_crypto_strings()
    void ERR_free_strings()

cdef extern from "openssl/crypto.h":
    const char *SSLeay_version(int t)

cdef extern from "openssl/crypto.h":
    int SSLEAY_VERSION

def encrypt_with_rsa(const char *plaintext_str):
    # OpenSSL 초기화
    ERR_load_crypto_strings()
    OpenSSL_add_all_algorithms()

    # OpenSSL 버전 출력
    printf("OpenSSL Version: %s\n", SSLeay_version(SSLEAY_VERSION))

    # 평문과 암호화된 텍스트를 저장하기 위한 BIGNUM 객체를 초기화
    cdef BIGNUM *plaintext_bn = BN_new()
    cdef BIGNUM *encrypted_bn = BN_new()
    cdef BN_CTX *bn_ctx = BN_CTX_new()

    # RSA 키 생성
    cdef EVP_PKEY *pkey = NULL
    cdef EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(6, NULL)  # EVP_PKEY_RSA = 6
    EVP_PKEY_keygen_init(ctx)
    EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 1024)
    EVP_PKEY_keygen(ctx, &pkey)

    # RSA 키 파라미터 추출
    cdef BIGNUM *n = NULL
    cdef BIGNUM *e = NULL
    EVP_PKEY_get_bn_param(pkey, "n", &n)
    EVP_PKEY_get_bn_param(pkey, "e", &e)

    # 평문 문자열을 BIGNUM으로 변환
    BN_bin2bn(<unsigned char *>plaintext_str, strlen(plaintext_str), plaintext_bn)

    # 모듈러 지수 연산 수행: encrypted = (plaintext ^ e) mod n
    BN_mod_exp(encrypted_bn, plaintext_bn, e, n, bn_ctx)

    # 암호화된 BIGNUM을 16진수 문자열로 변환하여 반환
    cdef char *encrypted_hex = BN_bn2hex(encrypted_bn)

    # Cleanup
    BN_free(plaintext_bn)
    BN_free(encrypted_bn)
    BN_CTX_free(bn_ctx)
    EVP_PKEY_CTX_free(ctx)
    EVP_PKEY_free(pkey)
    ERR_free_strings()
    EVP_cleanup()

    return encrypted_hex
