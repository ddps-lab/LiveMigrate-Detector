#include "csv_util.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CSV_PATH "/home/ubuntu/get_cpuid/cpuid.csv"

void remove_prefix(char* str) {
    char prefix[] = "XED_ISA_SET_";
    char *result = strstr(str, prefix);
    if (result != NULL) {
        strcpy(str, str + strlen(prefix));
    }
}

void get_instance_type(char* instance_type) {
    FILE *fp;
    char return_value[30];

    /* Open the command for reading. */
    fp = popen("curl http://169.254.169.254/latest/meta-data/instance-type", "r");
    if (fp == NULL) {
        printf("Failed to run command\n" );
        exit(1);
    }

    /* Read the output a line at a time - output it. */
    while (fgets(return_value, sizeof(return_value)-1, fp) != NULL) {
        strcpy(instance_type, return_value);
    }

    /* close */
    pclose(fp);
}

void get_lscpu(char lscpu_values[5][128]) {
    FILE *fp;
    char str[4096];

    char Architecture[128];
    char Vendor_ID[128];
    char Model_name[128];
    char CPU_family[128];
    char Stepping[128];

    /* Open the command for reading. */
    fp = popen("lscpu", "r");
    if (fp == NULL) {
        printf("Failed to run command\n" );
        exit(1);
    }

    /* Read the output a line at a time - output it. */
    while (fgets(str, sizeof(str)-1, fp) != NULL) {
        if (sscanf(str, "Architecture: %s", Architecture) == 1){
            strcpy(lscpu_values[0], Architecture);
        }
        else if (sscanf(str, "Vendor ID: %s", Vendor_ID) == 1){
            strcpy(lscpu_values[1], Vendor_ID);
        }
        else if (sscanf(str, "Model name: %[^\n]", Model_name) == 1){
            strcpy(lscpu_values[2], Model_name);
        }
        else if (sscanf(str, "CPU family: %[^\n]", CPU_family) == 1){
            strcpy(lscpu_values[3], CPU_family);
        }
        else if (sscanf(str, "Stepping: %[^\n]", Stepping) == 1){
            strcpy(lscpu_values[4], Stepping);
        }
    }

    /* close */
    pclose(fp);
}

void write_csv_headers(FILE *file, char lscpu_columns[][128], char columns[][MAX_TOKEN_LENGTH], int len) {
    fprintf(file, "InstanceType,");
    
    for (int i = 0; i < MAX_LSCPU_COLUMNS; i++) {
        fprintf(file, "%s,", lscpu_columns[i]);
    }
    
    for (int i = 0; i < len; i++) {
        if (i != 0) {
            fprintf(file, ",");
        }
        fprintf(file, "%s", columns[i]);
    }
    
    fprintf(file, "\n");
}

void write_csv_values(FILE *file, char *instance_type, char lscpu_values[][128], int *values, int len) {
    fprintf(file, "%s,", instance_type);
    
    for (int i = 0; i < MAX_LSCPU_COLUMNS; i++) {
        fprintf(file, "%s,", lscpu_values[i]);
    }
    
    for (int i = 0; i < len; i++) {
        if (i != 0) {
            fprintf(file, ",");
        }
        fprintf(file, "%d", values[i]);
    }
    
    fprintf(file, "\n");
}

int create_csv(char columns[MAX_ITEMS][MAX_TOKEN_LENGTH], int values[MAX_ITEMS], int len) {
    FILE *file;
    char instance_type[30] = "";
    char lscpu_columns[5][128] = {"Architecture", "Vendor_ID", "Model_name", "CPU_family", "Stepping"};
    char lscpu_values[5][128] = {""};
    
    get_instance_type(instance_type);
    get_lscpu(lscpu_values);

    file = fopen(CSV_PATH, "w");
    if (file == NULL) {
        printf("Could not open file\n");
        return -1;
    }

    for(int i = 0; i < MAX_ITEMS; i++){
        remove_prefix(columns[i]);
    }

    write_csv_headers(file, lscpu_columns, columns, len);
    write_csv_values(file, instance_type, lscpu_values, values, len);
    
    fclose(file);

    return 0;
}