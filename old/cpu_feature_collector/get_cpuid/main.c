#include "cpuid_info.h"
#include "csv_util.h"
#include "tsx.h"

#include <stdio.h>
#include <string.h>

#define MAX_ITEMS 151
#define MAX_TOKEN_LENGTH 50

int main() {
    int values[MAX_ITEMS] = {0};
    char columns[MAX_ITEMS][MAX_TOKEN_LENGTH] = { "" };
    // leaf, subleaf, regi, bit
    int args[4] = {0};
    init_info_array();

    for (int i = 0; i < MAX_ITEMS - 1; i++) {
        bool is_available = true;
        // If the ISA being checked is rtm
        if (i == 145){
            // cpuinfo에서 rtm flag 체크
            values[i] = is_rtm_visible();
            snprintf(columns[i], sizeof(columns[i]), "%s", info_array[i].ISA_SET);

            continue;
        }
        
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

    /* TSX를 지원하지만 TAA(TSX Asynchronous Abort) 보안이슈로 트랜젝션 메모리를 제한한 경우 xbegin, xend를 제외한 명령은 사용 가능함.
    *  이를 별도로 확인하여 워크로드에서 트랜젝션 메모리를 사용하지 않으나 xtest와 같은 명령이 포함된 경우 호환되지 않음으로 판단하는 오차를 제거함
    */
    snprintf(columns[MAX_ITEMS - 1], sizeof(columns[MAX_ITEMS - 1]), "%s", "XTEST");
    values[MAX_ITEMS - 1] = try_xtest();

    create_csv(columns, values, MAX_ITEMS);

    return 0;
}