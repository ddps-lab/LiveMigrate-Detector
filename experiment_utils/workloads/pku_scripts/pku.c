#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <string.h>
#include <setjmp.h>
#include <cpuid.h>
#include <unistd.h>

#define PAGE_SIZE 4096

static sigjmp_buf jump_buffer;

// segfault 발생 시 처리할 함수
void segfault_sigaction(int signal, siginfo_t *si, void *arg) {
    printf("Caught segfault at address %p\n", si->si_addr);
    siglongjmp(jump_buffer, 1);
}

void *thread_func(void *arg) {
    if (sigsetjmp(jump_buffer, 1) == 0) {
        char *buffer = (char *) arg;
        printf("Thread attempting to write to protected memory...\n");
        *buffer = 'A';  // 여기서 segfault 발생
    } else {
        printf("Thread recovered from segfault.\n");
    }
    return NULL;
}

// PKU 지원 여부를 체크하는 함수
int check_pku_support() {
    unsigned int eax, ebx, ecx, edx;
    eax = 7; // 확장된 기능을 위한 리프 번호
    ecx = 0; // 확장된 기능의 세부 사항을 지정
    __get_cpuid(eax, &eax, &ebx, &ecx, &edx);
    return (ecx >> 3) & 1; // PKU 지원은 ecx의 3번째 비트
}

int main() {
    int pku_supported = check_pku_support();

    while (1){
        char *buffer;
        struct sigaction sa;

        memset(&sa, 0, sizeof(sigaction));
        sigemptyset(&sa.sa_mask);
        sa.sa_flags     = SA_SIGINFO;
        sa.sa_sigaction = segfault_sigaction;
        sigaction(SIGSEGV, &sa, NULL);

        if (posix_memalign((void**)&buffer, PAGE_SIZE, PAGE_SIZE) != 0) {
            perror("posix_memalign");
            return 1;
        }

        memset(buffer, 'B', PAGE_SIZE);

        int pkey;

        // PKU를 지원하면 PKU를 사용하고, 그렇지 않으면 mprotect 사용
        if (pku_supported) {
            pkey = pkey_alloc(0, 0);
            if (pkey == -1) {
                perror("pkey_alloc");
                return 1;
            }
            if (pkey_mprotect(buffer, PAGE_SIZE, PROT_READ | PROT_WRITE, pkey)) {
                perror("pkey_mprotect");
                return 1;
            }
            if (pkey_set(pkey, PKEY_DISABLE_WRITE)) {
                perror("pkey_set");
                return 1;
            }
        } else {
            if (mprotect(buffer, PAGE_SIZE, PROT_READ)) {
                perror("mprotect");
                return 1;
            }
        }

        pthread_t thread;
        if (pthread_create(&thread, NULL, thread_func, buffer)) {
            perror("pthread_create");
            return 1;
        }

        pthread_join(thread, NULL);

        // 메모리 보호를 해제함
        if (pku_supported) {
            if (pkey_set(pkey, 0)) {
                perror("pkey_set - lift protection");
                return 1;
            }
        } else {
            if (mprotect(buffer, PAGE_SIZE, PROT_READ | PROT_WRITE)) {
                perror("mprotect - lift protection");
                return 1;
            }
        }

        printf("Protection lifted. Writing to memory...\n");
        buffer[0] = 'C'; // 보호 해제 후 쓰기 성공해야 함
        printf("Main thread wrote to memory: %c\n", buffer[0]);

        printf("Finished!\n");

        // 자원 정리
        free(buffer);
        if (pku_supported) {
            pkey_free(pkey);
        }

        sleep(3);
    }

    return 0;
}
