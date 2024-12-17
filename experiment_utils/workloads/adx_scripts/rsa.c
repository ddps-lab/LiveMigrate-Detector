#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/bn.h>
#include <openssl/err.h>

int main() {
    printf("OpenSSL Version: %s\n", OpenSSL_version(OPENSSL_VERSION));

    while(1){
        // OpenSSL의 오류 문자열과 알고리즘들을 초기화.
        // Load error messages
        ERR_load_crypto_strings();
        // Add all ciphers and digests algorithms to the EVP library
        OpenSSL_add_all_algorithms();

        // 평문을 문자열로 정의하고, 평문과 암호화된 텍스트를 저장하기 위한 BIGNUM 객체를 초기화
        // 또한, 중간 연산을 위한 BN_CTX 객체도 초기화
        const char *plaintext_str = "Hello, OpenSSL!";
        BIGNUM *plaintext_bn = BN_new();
        BIGNUM *encrypted_bn = BN_new();
        BN_CTX *bn_ctx = BN_CTX_new();

        // Key generation
        EVP_PKEY *pkey = NULL;
        EVP_PKEY_CTX *ctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
        EVP_PKEY_keygen_init(ctx);
        EVP_PKEY_CTX_set_rsa_keygen_bits(ctx, 1024);
        EVP_PKEY_keygen(ctx, &pkey);

        // Extract RSA key parameters
        BIGNUM *n = NULL, *e = NULL;
        EVP_PKEY_get_bn_param(pkey, "n", &n);
        EVP_PKEY_get_bn_param(pkey, "e", &e);

        // Convert plaintext string to BIGNUM
        BN_bin2bn((unsigned char *)plaintext_str, strlen(plaintext_str), plaintext_bn);

        // Perform modular exponentiation: encrypted = (plaintext ^ e) mod n
        BN_mod_exp(encrypted_bn, plaintext_bn, e, n, bn_ctx);

        // Print encrypted BIGNUM as a hexadecimal string
        char *encrypted_hex = BN_bn2hex(encrypted_bn);
        printf("Encrypted text: %s\n", encrypted_hex);
        OPENSSL_free(encrypted_hex);

        // Cleanup
        BN_free(plaintext_bn);
        BN_free(encrypted_bn);
        BN_CTX_free(bn_ctx);
        EVP_PKEY_CTX_free(ctx);
        EVP_PKEY_free(pkey);
        ERR_free_strings();
        EVP_cleanup();

        sleep(3);
    }
    return 0;
}
