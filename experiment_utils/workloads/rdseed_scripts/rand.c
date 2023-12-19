#include <stdio.h>
#include <unistd.h>
#include <cpuid.h>

#include <immintrin.h>

// RDSEED 명령어를 사용하여 64비트 난수를 생성하는 함수
unsigned long long generate_random_number_rdseed() {
    unsigned long long random_number;
    while (_rdseed64_step(&random_number) == 0);
    return random_number;
}

// RDRAND 명령어를 사용하여 64비트 난수를 생성하는 함수
unsigned long long generate_random_number_rdrand() {
    unsigned long long random_number;
    while (_rdrand64_step(&random_number) == 0);
    return random_number;
}

int check_rdseed_support() {
    unsigned int eax, ebx, ecx, edx;
    eax = 7;
    ecx = 0;
    __get_cpuid_count(eax, ecx, &eax, &ebx, &ecx, &edx);
    return (ebx >> 18) & 1; // rdseed 지원은 ebx의 18번째 비트
}

int check_rdrand_support() {
    unsigned int eax, ebx, ecx, edx;
    eax = 1;
    ecx = 0;
    __get_cpuid_count(eax, ecx, &eax, &ebx, &ecx, &edx);
    return (ecx >> 30) & 1; // rdrand 지원은 ecx의 30번째 비트
}

int main() {
    unsigned int eax, ebx, ecx, edx;
    if (!__get_cpuid(1, &eax, &ebx, &ecx, &edx)) {
        printf("Error: CPUID instruction not supported.\n");
        return 1;
    }

    int is_rdseed_support;
    int is_rdrand_support;

    is_rdseed_support = check_rdseed_support();
    is_rdrand_support = check_rdrand_support();

    while(1){
        unsigned long long random_number;
        if (is_rdseed_support) {
            printf("RDSEED is supported.\n");
            random_number = generate_random_number_rdseed();
        } else if (is_rdrand_support) {
            printf("RDSEED is not supported, but RDRAND is supported.\n");
            random_number = generate_random_number_rdrand();
        } else {
            printf("Error: Neither RDSEED nor RDRAND is supported on this CPU.\n");
            return 1;
        }

        printf("Generated random number: %llu\n", random_number);
        sleep(3);
    }

    return 0;
}
