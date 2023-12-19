#include <openssl/sha.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main() {
    // 초기화할 메시지
    unsigned char message[] = "Hello, World!";
    
    while(1){
        // SHA-256 해시를 저장할 배열
        unsigned char hash[SHA256_DIGEST_LENGTH];
        
        // SHA-256 컨텍스트 초기화
        SHA256_CTX sha256;
        SHA256_Init(&sha256);
        
        // 해시 계산
        SHA256_Update(&sha256, message, strlen((char*)message));
        SHA256_Final(hash, &sha256);
        
        // 해시 출력
        int i;
        for (i = 0; i < SHA256_DIGEST_LENGTH; i++) {
            printf("%02x", hash[i]);
        }
        printf("\n");

        sleep(3);
    }

    return 0;
}