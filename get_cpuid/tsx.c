#include <stdio.h>
#include <immintrin.h> // TSX 관련 함수 포함
#include <signal.h>
#include <setjmp.h>

int xtest_available = 1;
sigjmp_buf jump_buffer;

void handle_sigill(int sig) {
    // xtest is illegal instruction
    xtest_available = 0;
    siglongjmp(jump_buffer, 1);
}

void handle_gpf(int sig) {
    // Handle the general protection fault
    xtest_available = 0;
    siglongjmp(jump_buffer, 1);
}

int try_xtest(){
    if (sigsetjmp(jump_buffer, 1)) {
        // This block is executed if handle_sigill has been called
        return xtest_available;
    }

    signal(SIGILL, handle_sigill);
    signal(SIGSEGV, handle_gpf);

    int inTx = _xtest();

    // xtest is available
    return xtest_available;
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
