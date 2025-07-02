// gcc -o libint8dot.so -shared -fPIC libint8dot.c
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <cpuid.h>
#include <immintrin.h>

// 파이썬으로 반환할 SIMD 지원 수준 Enum
typedef enum
{
    SIMD_LEVEL_SCALAR = 0,
    SIMD_LEVEL_SSE41,
    SIMD_LEVEL_AVX2,
    SIMD_LEVEL_AVX512,
    SIMD_LEVEL_VNNI
} SimdLevel;

// 외부에 노출할 함수 1: CPU가 지원하는 최고의 SIMD 레벨을 반환
SimdLevel get_best_simd_level()
{
    unsigned int eax, ebx, ecx, edx;

    // VNNI가 최우선
    if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx) && (ecx & bit_AVX512VNNI))
    {
        return SIMD_LEVEL_VNNI;
    }
    // 그 다음 AVX512
    if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx) && (ebx & bit_AVX512F) && (ebx & bit_AVX512BW))
    {
        return SIMD_LEVEL_AVX512;
    }
    // 그 다음 AVX2
    if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx) && (ebx & bit_AVX2))
    {
        return SIMD_LEVEL_AVX2;
    }
    // 그 다음 SSE4.1
    if (__get_cpuid(1, &eax, &ebx, &ecx, &edx) && (ecx & bit_SSE4_1))
    {
        return SIMD_LEVEL_SSE41;
    }

    // 모두 미지원이면 Scalar
    return SIMD_LEVEL_SCALAR;
}

// --- 각 SIMD 레벨에 맞는 실제 연산 함수들 ---
// 이 함수들은 파이썬에서 직접 호출하지는 않음.

// Scalar
int32_t run_dot_product_scalar(const uint8_t *a, const int8_t *b, size_t size)
{
    int32_t result = 0;
    for (size_t i = 0; i < size; ++i)
        result += a[i] * b[i];
    return result;
}

// SSE4.1
__attribute__((target("sse4.1")))
int32_t
run_dot_product_sse41(const uint8_t *a, const int8_t *b, size_t size)
{
    __m128i acc = _mm_setzero_si128();
    for (size_t i = 0; i < size; i += 16)
    {
        __m128i a_s16 = _mm_cvtepu8_epi16(_mm_loadu_si128((__m128i *)(a + i)));
        __m128i b_s16 = _mm_cvtepi8_epi16(_mm_loadu_si128((__m128i *)(b + i)));
        acc = _mm_add_epi32(acc, _mm_madd_epi16(a_s16, b_s16));
    }
    int32_t temp[4];
    _mm_storeu_si128((__m128i *)temp, acc);
    return temp[0] + temp[1] + temp[2] + temp[3];
}

// AVX2
__attribute__((target("avx2")))
int32_t
run_dot_product_avx2(const uint8_t *a, const int8_t *b, size_t size)
{
    __m256i acc = _mm256_setzero_si256();
    for (size_t i = 0; i < size; i += 32)
    {
        __m256i a_s16_lo = _mm256_cvtepu8_epi16(_mm_loadu_si128((__m128i *)(a + i)));
        __m256i b_s16_lo = _mm256_cvtepi8_epi16(_mm_loadu_si128((__m128i *)(b + i)));
        acc = _mm256_add_epi32(acc, _mm256_madd_epi16(a_s16_lo, b_s16_lo));
        __m256i a_s16_hi = _mm256_cvtepu8_epi16(_mm_loadu_si128((__m128i *)(a + i + 16)));
        __m256i b_s16_hi = _mm256_cvtepi8_epi16(_mm_loadu_si128((__m128i *)(b + i + 16)));
        acc = _mm256_add_epi32(acc, _mm256_madd_epi16(a_s16_hi, b_s16_hi));
    }
    int32_t temp[8];
    _mm256_storeu_si256((__m256i *)temp, acc);
    return temp[0] + temp[1] + temp[2] + temp[3] + temp[4] + temp[5] + temp[6] + temp[7];
}

// AVX512
__attribute__((target("avx512f,avx512bw")))
int32_t
run_dot_product_avx512(const uint8_t *a, const int8_t *b, size_t size)
{
    __m512i acc = _mm512_setzero_si512();
    for (size_t i = 0; i < size; i += 64)
    {
        __m512i a_s16 = _mm512_cvtepu8_epi16(_mm256_loadu_si256((__m256i *)(a + i)));
        __m512i b_s16 = _mm512_cvtepi8_epi16(_mm256_loadu_si256((__m256i *)(b + i)));
        acc = _mm512_add_epi32(acc, _mm512_madd_epi16(a_s16, b_s16));
        a_s16 = _mm512_cvtepu8_epi16(_mm256_loadu_si256((__m256i *)(a + i + 32)));
        b_s16 = _mm512_cvtepi8_epi16(_mm256_loadu_si256((__m256i *)(b + i + 32)));
        acc = _mm512_add_epi32(acc, _mm512_madd_epi16(a_s16, b_s16));
    }
    return _mm512_reduce_add_epi32(acc);
}

// VNNI
__attribute__((target("avx512f,avx512vnni")))
int32_t
run_dot_product_vnni(const uint8_t *a, const int8_t *b, size_t size)
{
    __m512i acc = _mm512_setzero_si512();
    for (size_t i = 0; i < size; i += 64)
    {
        __m512i a_vec_u8 = _mm512_loadu_si512(a + i);
        __m512i b_vec_s8 = _mm512_loadu_si512(b + i);
        acc = _mm512_dpbusd_epi32(acc, a_vec_u8, b_vec_s8);
    }
    return _mm512_reduce_add_epi32(acc);
}