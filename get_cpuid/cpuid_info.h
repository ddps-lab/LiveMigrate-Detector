#ifndef CPUID_INFO_H
#define CPUID_INFO_H

#include <stdbool.h>

#define MAX_CPUIDS 4
#define MAX_TOKEN_LENGTH 50
#define MAX_ITEMS 151
#define MAX_LINE_LENGTH 120

#define EAX 0
#define EBX 1
#define ECX 2
#define EDX 3

typedef struct {
    char ISA_SET[50];
    char cpuids[MAX_CPUIDS][MAX_TOKEN_LENGTH];
} CPUID_info;

extern CPUID_info info_array[MAX_ITEMS];

void parse_line(char* line, int index);
void init_info_array();
int is_cpuid_available(int leaf, int subleaf, int regi, int bit);
int parse_cpuid(char* cpuid, int args[]);

#endif
