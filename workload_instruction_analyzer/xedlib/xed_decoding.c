#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "xed-interface.h"

typedef struct {
    char* isa_set;
    char* disassembly;
} xed_result;

void hex_string_to_byte_array(const char* hex_str, unsigned char* byte_array, int byte_array_max) {
    int hex_str_len = strlen(hex_str);
    int i = 0, j = 0;

    // 문자열을 바이트로 변환
    while (i < hex_str_len && j < byte_array_max) {
        sscanf(&hex_str[i], "%2hhx", &byte_array[j]);
        i += 2;  // 2개의 16진수 문자가 한 바이트
        j++;
    }
}

char* disassemble(xed_decoded_inst_t* xedd) {
    xed_bool_t ok;
    xed_print_info_t pi;
    #define XBUFLEN 200
    char* buf = malloc(XBUFLEN);  // 동적 메모리 할당

    if (!buf) return NULL;  // 메모리 할당 실패 시 NULL 반환

    xed_init_print_info(&pi);
    pi.p = xedd;
    pi.blen = XBUFLEN;
    pi.buf = buf;
    pi.buf[0] = 0; // 초기화

    ok = xed_format_generic(&pi);
    if (!ok) {
        free(buf); // 실패 시 메모리 해제
        return NULL;
    }

    return buf; // 성공 시 문자열 반환
}


xed_result print_isa_set(const char* byte_sequence) {
    xed_decoded_inst_t xedd;
    xed_error_enum_t xed_error;
    xed_state_t state;

    // xed 초기화
    xed_tables_init();

    // 디코딩할 바이트코드의 상태 설정
    xed_state_zero(&state);
    state.mmode = XED_MACHINE_MODE_LONG_64;

    // 16진수 문자열을 바이트 배열로 변환
    int byte_sequence_len = strlen(byte_sequence) / 2;
    unsigned char* bytes = (unsigned char*)malloc(byte_sequence_len);
    
    xed_result result;
    result.isa_set = NULL;
    result.disassembly = NULL;

    if (!bytes) {
        return result; // 반환 객체의 멤버는 NULL로 설정됨
    }

    hex_string_to_byte_array(byte_sequence, bytes, byte_sequence_len);

    // 인스트럭션 디코딩
    xed_decoded_inst_zero_set_mode(&xedd, &state);
    xed_error = xed_decode(&xedd, bytes, byte_sequence_len);
    free(bytes);

    if (xed_error != XED_ERROR_NONE) {
        return result; // 반환 객체의 멤버는 NULL로 설정됨
    }

    // ISA set 조회
    xed_isa_set_enum_t isaset = xed_decoded_inst_get_isa_set(&xedd);
    const char* isa_set_name = xed_isa_set_enum_t2str(isaset);

    result.isa_set = strdup(isa_set_name);
    result.disassembly = disassemble(&xedd);

    return result;
}