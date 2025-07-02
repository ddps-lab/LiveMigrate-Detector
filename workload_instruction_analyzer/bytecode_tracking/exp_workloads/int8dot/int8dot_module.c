#include <Python.h>
#include <cpuid.h>
#include <immintrin.h>
#include <stdbool.h>
#include <stdint.h>

// --- CPU 기능 감지 및 SIMD 워크로드 ---

// CPU 기능 플래그를 저장할 구조체
typedef struct
{
    bool sse41;
    bool avx2;
    bool avx512f;
    bool avx512bw;
    bool avx512_vnni;
} CpuFeatures;

// CPUID를 통해 CPU 기능 감지
void detect_cpu_features(CpuFeatures *features)
{
    unsigned int eax, ebx, ecx, edx;
    if (__get_cpuid(1, &eax, &ebx, &ecx, &edx))
    {
        features->sse41 = (ecx & bit_SSE4_1);
    }
    if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx))
    {
        features->avx2 = (ebx & bit_AVX2);
        features->avx512f = (ebx & bit_AVX512F);
        features->avx512bw = (ebx & bit_AVX512BW);
        features->avx512_vnni = (ecx & bit_AVX512VNNI);
    }
}

// 모든 워크로드 함수가 동일한 형태를 갖도록 함수 포인터 타입 정의
typedef int32_t (*workload_func_t)(const uint8_t *, const int8_t *, size_t);

// 각 SIMD 버전의 함수들 (target 속성으로 독립 컴파일)
__attribute__((target("sse4.1")))
int32_t
workload_sse(const uint8_t *a, const int8_t *b, size_t size)
{
    __m128i acc = _mm_setzero_si128();
    for (size_t i = 0; i < size; i += 16)
    {
        __m128i a_vec = _mm_loadu_si128((__m128i *)(a + i));
        __m128i b_vec = _mm_loadu_si128((__m128i *)(b + i));
        __m128i a_s16 = _mm_cvtepu8_epi16(a_vec);
        __m128i b_s16 = _mm_cvtepi8_epi16(b_vec);
        acc = _mm_add_epi32(acc, _mm_madd_epi16(a_s16, b_s16));
    }
    int32_t temp[4];
    _mm_storeu_si128((__m128i *)temp, acc);
    return temp[0] + temp[1] + temp[2] + temp[3];
}

__attribute__((target("avx2")))
int32_t
workload_avx2(const uint8_t *a, const int8_t *b, size_t size)
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

__attribute__((target("avx512f,avx512bw")))
int32_t
workload_avx512f(const uint8_t *a, const int8_t *b, size_t size)
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

__attribute__((target("avx512f,avx512vnni")))
int32_t
workload_avx512_vnni(const uint8_t *a, const int8_t *b, size_t size)
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

// 런타임에 선택된 함수 포인터와 그 이름을 저장할 전역 변수
static workload_func_t selected_workload = NULL;
static const char *selected_workload_name = NULL;

// 모듈 로딩 시 최적의 함수를 선택하는 디스패처
void resolve_workload_function()
{
    CpuFeatures features = {0};
    detect_cpu_features(&features);

    if (features.avx512_vnni)
    {
        selected_workload_name = "AVX512-VNNI";
        selected_workload = workload_avx512_vnni;
    }
    else if (features.avx512f && features.avx512bw)
    {
        selected_workload_name = "AVX512F";
        selected_workload = workload_avx512f;
    }
    else if (features.avx2)
    {
        selected_workload_name = "AVX2";
        selected_workload = workload_avx2;
    }
    else if (features.sse41)
    {
        selected_workload_name = "SSE4.1";
        selected_workload = workload_sse;
    }
    else
    {
        selected_workload_name = "Unsupported";
        selected_workload = NULL;
    }
}

// --- 파이썬 바인딩 래퍼(Wrapper) 함수들 ---

static PyObject *py_dot_product(PyObject *self, PyObject *args)
{
    Py_buffer buf_a, buf_b;
    if (!PyArg_ParseTuple(args, "y*y*", &buf_a, &buf_b))
        return NULL;
    if (buf_a.len != buf_b.len)
    {
        PyErr_SetString(PyExc_ValueError, "Input byte arrays must have the same length.");
        PyBuffer_Release(&buf_a);
        PyBuffer_Release(&buf_b);
        return NULL;
    }
    if (selected_workload == NULL)
    {
        PyErr_SetString(PyExc_RuntimeError, "No suitable SIMD workload function found for this CPU.");
        PyBuffer_Release(&buf_a);
        PyBuffer_Release(&buf_b);
        return NULL;
    }
    int32_t result = selected_workload((const uint8_t *)buf_a.buf, (const int8_t *)buf_b.buf, buf_a.len);
    PyBuffer_Release(&buf_a);
    PyBuffer_Release(&buf_b);
    return Py_BuildValue("l", (long)result);
}

static PyObject *py_get_selected_kernel(PyObject *self, PyObject *args)
{
    return Py_BuildValue("s", selected_workload_name);
}

// --- 파이썬 모듈 정의 ---

static PyMethodDef Int8DotMethods[] = {
    {"dot_product", py_dot_product, METH_VARARGS, "Calculates the dot product of two int8 byte arrays."},
    {"get_selected_kernel", py_get_selected_kernel, METH_NOARGS, "Returns the name of the selected SIMD kernel."},
    {NULL, NULL, 0, NULL}};

static struct PyModuleDef int8dotmodule = {
    PyModuleDef_HEAD_INIT, "int8dot", "High-performance int8 dot product module.", -1, Int8DotMethods};

// 모듈 초기화 함수
PyMODINIT_FUNC PyInit_int8dot(void)
{
    resolve_workload_function();
    return PyModule_Create(&int8dotmodule);
}