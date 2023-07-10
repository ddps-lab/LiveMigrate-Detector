#include "cpuid_info.h"
#include "csv_util.h"

#include <stdio.h>
#include <string.h>

#define MAX_ITEMS 153
#define MAX_TOKEN_LENGTH 50

int main() {
    int values[MAX_ITEMS] = {0};
    char columns[MAX_ITEMS][MAX_TOKEN_LENGTH] = { "" };
    // leaf, subleaf, regi, bit
    int args[4] = {0};
    init_info_array();

    for (int i = 0; i < MAX_ITEMS; i++) {
        bool is_available = true;
        snprintf(columns[i], sizeof(columns[i]), "%s", info_array[i].ISA_SET);

        for (int j = 0; j < MAX_CPUIDS; j++) {
            if (strlen(info_array[i].cpuids[j]) > 0) {
                parse_cpuid(info_array[i].cpuids[j], args);

                if(!is_cpuid_available(args[0], args[1], args[2], args[3])){
                    is_available = false;
                }
            }
        }
        if(is_available){
            values[i] = 1;
        }
    }

    create_csv(columns, values, MAX_ITEMS);

    return 0;
}