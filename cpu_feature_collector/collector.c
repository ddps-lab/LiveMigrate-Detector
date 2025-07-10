#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include "xed-interface.h"
#include <cpuid.h>
#include <immintrin.h>
#include <signal.h>
#include <setjmp.h>

// CPUID 명령을 실행하는 크로스-플랫폼 래퍼 함수
void cpuid(unsigned int leaf, unsigned int subleaf, unsigned int *eax, unsigned int *ebx, unsigned int *ecx, unsigned int *edx)
{
    __cpuid_count(leaf, subleaf, *eax, *ebx, *ecx, *edx);
}

/**
 * @brief 주어진 ISA-SET이 현재 CPU에서 지원되는지 확인합니다.
 *
 * @param isa_set 확인할 ISA-SET 열거형 값
 * @return true ISA-SET이 지원됨
 * @return false ISA-SET이 지원되지 않거나 CPUID 정보가 없음
 */
bool is_isa_set_supported(xed_isa_set_enum_t isa_set)
{
    // 1. ISA-SET -> CPUID 그룹 목록 (OR 관계)
    // CPUID 그룹 중 하나라도 지원되면 ISA-SET은 지원되는 것입니다.
    for (int i = 0; i < XED_MAX_CPUID_GROUPS_PER_ISA_SET; ++i)
    {
        xed_cpuid_group_enum_t group = xed_get_cpuid_group_enum_for_isa_set(isa_set, i);
        if (group == XED_CPUID_GROUP_INVALID)
        {
            return !i; // i가 0이라면 초창기 ISA-SET이므로 항상 지원된다고 판단, 1 이상이라면 미지원
        }

        bool group_supported = true; // 현재 그룹이 지원되는지 여부 (AND를 위해 true로 시작)

        // 2. CPUID 그룹 -> CPUID 레코드 목록 (AND 관계)
        // 그룹 내의 모든 CPUID 레코드가 충족되어야 그룹이 지원됩니다.
        for (int j = 0; j < XED_MAX_CPUID_RECS_PER_GROUP; ++j)
        {
            xed_cpuid_rec_enum_t rec_enum = xed_get_cpuid_rec_enum_for_group(group, j);
            if (rec_enum == XED_CPUID_REC_INVALID)
            {
                break; // 이 그룹에 대한 더 이상의 레코드는 없음
            }

            xed_cpuid_rec_t crec;
            if (!xed_get_cpuid_rec(rec_enum, &crec))
            {
                fprintf(stderr, "Error: Could not find cpuid leaf information for a record.\n");
                group_supported = false;
                break;
            }

            // 3. 실제 CPUID 실행 및 비교
            unsigned int eax, ebx, ecx, edx;
            cpuid(crec.leaf, crec.subleaf, &eax, &ebx, &ecx, &edx);

            unsigned int host_reg_val = 0;
            switch (crec.reg)
            {
            case XED_REG_EAX:
                host_reg_val = eax;
                break;
            case XED_REG_EBX:
                host_reg_val = ebx;
                break;
            case XED_REG_ECX:
                host_reg_val = ecx;
                break;
            case XED_REG_EDX:
                host_reg_val = edx;
                break;
            default:
                fprintf(stderr, "Error: Unexpected register in CPUID record.\n");
                group_supported = false;
                break;
            }
            if (!group_supported)
                break;

            // 특정 비트(들) 추출
            unsigned int width = crec.bit_end - crec.bit_start + 1;
            unsigned int mask = (width == 32) ? 0xFFFFFFFF : (1U << width) - 1;
            unsigned int host_val = (host_reg_val >> crec.bit_start) & mask;

            // 요구되는 값과 실제 값을 비교
            if (host_val != crec.value)
            {
                group_supported = false; // 하나라도 다르면 이 그룹은 지원 안됨
                break;
            }
        } // 레코드 루프 끝

        if (group_supported)
        {
            // 이 그룹의 모든 조건이 충족되었으므로 ISA-SET은 지원됩니다.
            // (그룹 간은 OR 관계이므로 더 이상 확인할 필요가 없습니다.)
            return true;
        }
    } // 그룹 루프 끝

    // 모든 그룹을 확인했지만, 지원되는 그룹을 찾지 못했습니다.
    return false;
}

int xtest_available = 1;
sigjmp_buf jump_buf;

void handler(int sig)
{
    xtest_available = 0;
    siglongjmp(jump_buf, 1);
}

int try_xtest()
{
    if (sigsetjmp(jump_buf, 1))
    {
        return xtest_available;
    }

    signal(SIGILL, handler);
    signal(SIGSEGV, handler);

    _xtest();

    return xtest_available;
}

int main(int argc, char **argv)
{
    xed_tables_init();

    xed_isa_set_enum_t last_isa = xed_isa_set_enum_t_last();

    for (xed_isa_set_enum_t isa = XED_ISA_SET_INVALID + 1; isa < last_isa; isa++)
    {
        printf(isa == XED_ISA_SET_INVALID + 1 ? "%s" : ",%s", xed_isa_set_enum_t2str(isa));
    }

    puts(",XTEST");

    for (xed_isa_set_enum_t isa = XED_ISA_SET_INVALID + 1; isa < last_isa; isa++)
    {
        printf(isa == XED_ISA_SET_INVALID + 1 ? "%d" : ",%d", is_isa_set_supported(isa));
    }

    printf(",%d", try_xtest());

    return 0;
}