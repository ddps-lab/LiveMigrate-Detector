#include "cpuid_info.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cpuid.h>

#define CPUID_PATH "/home/ubuntu/get_cpuid/cpuid.txt"

CPUID_info info_array[MAX_ITEMS];

void parse_line(char* line, int index) {
    char delimit[] = " ,\t\n";

    char *token = strtok(line, delimit);

    strcpy(info_array[index].ISA_SET, token);

    for (int i = 0; 1; i++) {
        token = strtok(NULL, delimit);

        if (token == NULL) {
            break;
        }
        strcpy(info_array[index].cpuids[i], token);
    }    
}

void init_info_array() {
    FILE *file = fopen(CPUID_PATH, "r");
    if (file == NULL) {
        fprintf(stderr, "Could not open file\n");
        exit(1);
    }

    char line[MAX_LINE_LENGTH];
    int index = 0;

    while (fgets(line, MAX_LINE_LENGTH, file) != NULL && index < MAX_ITEMS) {
        parse_line(line, index);
        index++;
    }

    fclose(file);
}

int is_cpuid_available(int leaf, int subleaf, int regi, int bit){
    unsigned int eax, ebx, ecx, edx;
    unsigned int* registers[] = {&eax, &ebx, &ecx, &edx};

    __get_cpuid_count(leaf, subleaf, &eax, &ebx, &ecx, &edx);

    // EBX 레지스터의 16번째 비트를 확인합니다.
    if (*registers[regi] & (1 << bit)) {
        return 1;
    } else {
        return 0;
    }
}

int parse_cpuid(char* cpuid, int args[]){
    char cpuid_copy[MAX_TOKEN_LENGTH];
    strncpy(cpuid_copy, cpuid, MAX_TOKEN_LENGTH);  // cpuid 문자열 복사
    cpuid_copy[MAX_TOKEN_LENGTH - 1] = '\0';  // Null 종료 문자를 추가합니다.
    
    char *token;

    token = strtok(cpuid_copy, ".");

    // 첫번째 토큰은 필요하지 않으므로 Pass.
    for (int i = 0; 1; i++) {
        token = strtok(NULL, ".");

        if (token == NULL) {
            break;
        }

        // If the token value is not registered.
        if(i != 2){ 
            args[i] = atoi(token);
            continue;
        }

        if(strcmp(token, "eax") == 0){
            args[i] = EAX;
        } else if(strcmp(token, "ebx") == 0){
            args[i] = EBX;
        } else if(strcmp(token, "ecx") == 0){
            args[i] = ECX;
        } else if(strcmp(token, "edx") == 0){
            args[i] = EDX;
        }                      
    }
}