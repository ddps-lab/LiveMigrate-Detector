#include <Python.h>
#include <cpuid.h>
#include <immintrin.h>
#include <stdbool.h>
#include <stdint.h>

// CPU 기능 감지 결과를 파이썬 딕셔너리로 반환
static PyObject *detect_features(PyObject *self, PyObject *args)
{
    unsigned int eax, ebx, ecx, edx;
    bool sse41 = false, avx2 = false, avx512f = false, avx512bw = false, avx512_vnni = false;

    if (__get_cpuid(1, &eax, &ebx, &ecx, &edx))
    {
        sse41 = (ecx & bit_SSE4_1);
    }
    if (__get_cpuid_count(7, 0, &eax, &ebx, &ecx, &edx))
    {
        avx2 = (ebx & bit_AVX2);
        avx512f = (ebx & bit_AVX512F);
        avx512bw = (ebx & bit_AVX512BW);
        avx512_vnni = (ecx & bit_AVX512VNNI);
    }
    return Py_BuildValue("{s:b, s:b, s:b, s:b, s:b}",
                         "sse41", sse41, "avx2", avx2,
                         "avx512f", avx512f, "avx512bw", avx512bw,
                         "avx512_vnni", avx512_vnni);
}

// SSE4.1을 사용한 내적 연산 함수
__attribute__((target("sse4.1"))) static PyObject *dot_product_sse(PyObject *self, PyObject *args)
{
    Py_buffer buf_a, buf_b;
    if (!PyArg_ParseTuple(args, "y*y*", &buf_a, &buf_b))
        return NULL;
    if (buf_a.len != buf_b.len)
    {
        PyErr_SetString(PyExc_ValueError, "Byte arrays must have same length.");
        PyBuffer_Release(&buf_a);
        PyBuffer_Release(&buf_b);
        return NULL;
    }

    const uint8_t *a = (const uint8_t *)buf_a.buf;
    const int8_t *b = (const int8_t *)buf_b.buf;
    size_t size = buf_a.len;
    __m128i acc = _mm_setzero_si128();

    for (size_t i = 0; i < size; i += 16)
    {
        __m128i a_s16 = _mm_cvtepu8_epi16(_mm_loadu_si128((__m128i *)(a + i)));
        __m128i b_s16 = _mm_cvtepi8_epi16(_mm_loadu_si128((__m128i *)(b + i)));
        acc = _mm_add_epi32(acc, _mm_madd_epi16(a_s16, b_s16));
    }
    int32_t temp[4];
    _mm_storeu_si128((__m128i *)temp, acc);
    int32_t result = temp[0] + temp[1] + temp[2] + temp[3];

    PyBuffer_Release(&buf_a);
    PyBuffer_Release(&buf_b);
    return Py_BuildValue("l", (long)result);
}

// AVX2를 사용한 내적 연산 함수
__attribute__((target("avx2"))) static PyObject *dot_product_avx2(PyObject *self, PyObject *args)
{
    Py_buffer buf_a, buf_b;
    if (!PyArg_ParseTuple(args, "y*y*", &buf_a, &buf_b))
        return NULL;
    if (buf_a.len != buf_b.len)
    {
        PyErr_SetString(PyExc_ValueError, "Byte arrays must have same length.");
        PyBuffer_Release(&buf_a);
        PyBuffer_Release(&buf_b);
        return NULL;
    }

    const uint8_t *a = (const uint8_t *)buf_a.buf;
    const int8_t *b = (const int8_t *)buf_b.buf;
    size_t size = buf_a.len;
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
    int32_t result = temp[0] + temp[1] + temp[2] + temp[3] + temp[4] + temp[5] + temp[6] + temp[7];

    PyBuffer_Release(&buf_a);
    PyBuffer_Release(&buf_b);
    return Py_BuildValue("l", (long)result);
}

// AVX512F를 사용한 내적 연산 함수
__attribute__((target("avx512f,avx512bw"))) static PyObject *dot_product_avx512f(PyObject *self, PyObject *args)
{
    Py_buffer buf_a, buf_b;
    if (!PyArg_ParseTuple(args, "y*y*", &buf_a, &buf_b))
        return NULL;
    if (buf_a.len != buf_b.len)
    {
        PyErr_SetString(PyExc_ValueError, "Byte arrays must have same length.");
        PyBuffer_Release(&buf_a);
        PyBuffer_Release(&buf_b);
        return NULL;
    }

    const uint8_t *a = (const uint8_t *)buf_a.buf;
    const int8_t *b = (const int8_t *)buf_b.buf;
    size_t size = buf_a.len;
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
    int32_t result = _mm512_reduce_add_epi32(acc);

    PyBuffer_Release(&buf_a);
    PyBuffer_Release(&buf_b);
    return Py_BuildValue("l", (long)result);
}

// AVX-512 VNNI를 사용한 내적 연산 함수
__attribute__((target("avx512f,avx512vnni"))) static PyObject *dot_product_vnni(PyObject *self, PyObject *args)
{
    Py_buffer buf_a, buf_b;
    if (!PyArg_ParseTuple(args, "y*y*", &buf_a, &buf_b))
        return NULL;
    if (buf_a.len != buf_b.len)
    {
        PyErr_SetString(PyExc_ValueError, "Byte arrays must have same length.");
        PyBuffer_Release(&buf_a);
        PyBuffer_Release(&buf_b);
        return NULL;
    }

    const uint8_t *a = (const uint8_t *)buf_a.buf;
    const int8_t *b = (const int8_t *)buf_b.buf;
    size_t size = buf_a.len;
    __m512i acc = _mm512_setzero_si512();

    for (size_t i = 0; i < size; i += 64)
    {
        __m512i a_vec_u8 = _mm512_loadu_si512(a + i);
        __m512i b_vec_s8 = _mm512_loadu_si512(b + i);
        acc = _mm512_dpbusd_epi32(acc, a_vec_u8, b_vec_s8);
    }
    int32_t result = _mm512_reduce_add_epi32(acc);

    PyBuffer_Release(&buf_a);
    PyBuffer_Release(&buf_b);
    return Py_BuildValue("l", (long)result);
}

// 모듈에 포함될 메서드 정의
static PyMethodDef Int8DotMethods[] = {
    {"detect_features", detect_features, METH_NOARGS, "Detects CPU features."},
    {"dot_product_sse", dot_product_sse, METH_VARARGS, "Dot product using SSE4.1."},
    {"dot_product_avx2", dot_product_avx2, METH_VARARGS, "Dot product using AVX2."},
    {"dot_product_avx512f", dot_product_avx512f, METH_VARARGS, "Dot product using AVX512F."},
    {"dot_product_vnni", dot_product_vnni, METH_VARARGS, "Dot product using AVX512-VNNI."},
    {NULL, NULL, 0, NULL}};

// 모듈 정의
static struct PyModuleDef int8dotmodule = {
    PyModuleDef_HEAD_INIT, "int8dot", "A library of int8 dot product functions.", -1, Int8DotMethods};

// 모듈 초기화 함수
PyMODINIT_FUNC PyInit_int8dot(void)
{
    return PyModule_Create(&int8dotmodule);
}