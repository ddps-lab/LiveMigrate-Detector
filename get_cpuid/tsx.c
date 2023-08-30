#include <stdio.h>
#include <immintrin.h> // TSX 관련 함수 포함
#include <unistd.h>
#include <signal.h>
#include <stdlib.h>

int xtest_availabe = 1;
volatile int globalVar = 0;

void handle_sigill(int sig) {
    // xtest is illegal instruction
    xtest_availabe = 0;
}

int try_xtest(){
    signal(SIGILL, handle_sigill);

    int inTx = _xtest();
    
    // xtest is available
    return xtest_availabe;
}

int is_rtm_visible(){
    FILE *fp;
    char buffer[1024];
    int hasResult = 0;

    // popen을 사용하여 명령을 실행하고 그 결과를 파일 포인터로 받아옴
    fp = popen("lscpu | grep rtm", "r");
    if (fp == NULL) {
        perror("Error opening pipe");
        return 0;
    }

    // 출력을 읽음. 결과가 있다면 hasResult를 1로 설정
    while (fgets(buffer, sizeof(buffer), fp) != NULL) {
        hasResult = 1;
    }

    // popen에 대한 자원을 해제
    pclose(fp);

    // 결과에 따라 메시지 출력
    if (hasResult) {
        return 1;
    } else {
        return 0;
    }
}