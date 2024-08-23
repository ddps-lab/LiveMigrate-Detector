#define _GNU_SOURCE
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
#include <pthread.h>
#include <signal.h>
#include <string.h>
#include <setjmp.h>
#include <cpuid.h>

#define PAGE_SIZE 4096

static sigjmp_buf jump_buffer;
static int pkey = -1;
static char *buffer = NULL;

// segfault 발생 시 처리할 함수
void segfault_sigaction(int signal, siginfo_t *si, void *arg) {
    printf("Caught segfault at address %p\n", si->si_addr);
    siglongjmp(jump_buffer, 1);
}

// PKU 지원 여부를 체크하는 함수
static PyObject* check_pku_support(PyObject *self, PyObject *args) {
    unsigned int eax, ebx, ecx, edx;

    eax = 7;
    ecx = 0;

    __cpuid_count(eax, ecx, eax, ebx, ecx, edx);

    return PyBool_FromLong((ecx >> 3) & 1);
}

// PKU를 사용하여 메모리를 보호하는 함수
static PyObject* protect_memory_pku(PyObject *self, PyObject *args) {
    unsigned long buffer_address;

    if (!PyArg_ParseTuple(args, "k", &buffer_address)) {
        return NULL;
    }

    buffer = (char*)buffer_address;

    pkey = pkey_alloc(0, 0);
    if (pkey == -1) {
        perror("pkey_alloc");
        return PyErr_SetFromErrno(PyExc_RuntimeError);
    }

    if (pkey_mprotect(buffer, PAGE_SIZE, PROT_READ | PROT_WRITE, pkey)) {
        perror("pkey_mprotect");
        return PyErr_SetFromErrno(PyExc_RuntimeError);
    }

    if (pkey_set(pkey, PKEY_DISABLE_WRITE)) {
        perror("pkey_set");
        return PyErr_SetFromErrno(PyExc_RuntimeError);
    }

    Py_RETURN_NONE;
}

// mprotect를 사용하여 메모리를 보호하는 함수
static PyObject* protect_memory_mprotect(PyObject *self, PyObject *args) {
    unsigned long buffer_address;

    if (!PyArg_ParseTuple(args, "k", &buffer_address)) {
        return NULL;
    }

    char *buffer = (char *)buffer_address;

    if (mprotect(buffer, PAGE_SIZE, PROT_READ)) {
        perror("mprotect");
        return PyErr_SetFromErrno(PyExc_RuntimeError);
    }

    Py_RETURN_NONE;
}

// 메모리 보호를 해제하는 함수
static PyObject* unprotect_memory(PyObject *self, PyObject *args) {
    int pku_supported;

    if (!PyArg_ParseTuple(args, "ik", &pku_supported, &buffer)) {
        return NULL;
    }

    if (pku_supported) {
        if (pkey_set(pkey, 0)) {
            perror("pkey_set - lift protection");
            return PyErr_SetFromErrno(PyExc_RuntimeError);
        }
    } else {
        if (mprotect(buffer, PAGE_SIZE, PROT_READ | PROT_WRITE)) {
            perror("mprotect - lift protection");
            return PyErr_SetFromErrno(PyExc_RuntimeError);
        }
    }

    Py_RETURN_NONE;
}

// 메모리를 읽는 함수
static PyObject* read_memory(PyObject *self, PyObject *args) {
    unsigned long buffer_address;

    // 메모리 주소를 인자로 받아옴
    if (!PyArg_ParseTuple(args, "k", &buffer_address)) {
        return NULL;
    }

    // 전달된 메모리 주소를 buffer 포인터로 캐스팅
    buffer = (char*)buffer_address;

    // 메모리에서 값을 읽음
    char value = buffer[0];

    // 읽은 값을 반환
    return Py_BuildValue("c", value);
}


// 메모리를 쓰는 함수
static PyObject* write_memory(PyObject *self, PyObject *args) {
    char value;
    unsigned long buffer_address;

    if (!PyArg_ParseTuple(args, "ck", &value, &buffer_address)) {
        return NULL;
    }

    buffer = (char*)buffer_address;

    // 세그멘테이션 폴트 처리
    if (sigsetjmp(jump_buffer, 1) == 0) {
        buffer[0] = value;
        Py_RETURN_NONE;
    } else {
        PyErr_SetString(PyExc_RuntimeError, "Segmentation fault occurred during memory write");
        return NULL;
    }
}

// 모듈 메서드 정의
static PyMethodDef pkuMethods[] = {
    {"check_pku_support", check_pku_support, METH_NOARGS, "Check if the CPU supports PKU."},
    {"protect_memory_pku", protect_memory_pku, METH_VARARGS, "Protect memory using PKU."},
    {"protect_memory_mprotect", protect_memory_mprotect, METH_VARARGS, "Protect memory using mprotect."},
    {"unprotect_memory", unprotect_memory, METH_VARARGS, "Unprotect memory."},
    {"read_memory", read_memory, METH_VARARGS, "Read a value from protected memory."},
    {"write_memory", write_memory, METH_VARARGS, "Write a value to protected memory."},
    {NULL, NULL, 0, NULL}
};

// 모듈 정의
static struct PyModuleDef pkumodule = {
    PyModuleDef_HEAD_INIT,
    "pku",
    NULL,
    -1,
    pkuMethods
};

// 모듈 초기화 함수
PyMODINIT_FUNC PyInit_pku(void) {
    struct sigaction sa;

    // 세그멘테이션 폴트 신호 핸들러 설정
    sa.sa_flags = SA_SIGINFO;
    sa.sa_sigaction = segfault_sigaction;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGSEGV, &sa, NULL);

    return PyModule_Create(&pkumodule);
}
