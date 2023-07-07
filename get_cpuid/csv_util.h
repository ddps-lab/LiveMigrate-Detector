#ifndef CSV_UTIL_H
#define CSV_UTIL_H

#include <stdio.h>

#define MAX_ITEMS 153
#define MAX_LSCPU_COLUMNS 5
#define MAX_TOKEN_LENGTH 50

void remove_prefix(char* str);
void get_instance_type(char* instance_type);
void get_lscpu(char lscpu_values[5][128]);
void write_csv_headers(FILE *file, char lscpu_columns[][128], char columns[][MAX_TOKEN_LENGTH], int len);
void write_csv_values(FILE *file, char *instance_type, char lscpu_values[][128], int *values, int len);
int create_csv(char columns[MAX_ITEMS][MAX_TOKEN_LENGTH], int values[MAX_ITEMS], int len);

#endif