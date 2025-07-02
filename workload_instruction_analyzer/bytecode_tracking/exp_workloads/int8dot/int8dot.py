import ctypes
import time
import os

# --- 1. 라이브러리 로드 및 함수 시그니처 설정 ---

lib_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'libint8dot.so')
lib = ctypes.CDLL(lib_path)

# C의 Enum 값들을 파이썬 변수로 정의
SIMD_LEVEL_SCALAR = 0
SIMD_LEVEL_SSE41 = 1
SIMD_LEVEL_AVX2 = 2
SIMD_LEVEL_AVX512 = 3
SIMD_LEVEL_VNNI = 4

# C 함수들의 반환/인자 타입을 설정
lib.get_best_simd_level.restype = ctypes.c_int

c_uint8_p = ctypes.POINTER(ctypes.c_uint8)
c_int8_p = ctypes.POINTER(ctypes.c_int8)

lib.run_dot_product_scalar.restype = ctypes.c_int32
lib.run_dot_product_scalar.argtypes = [c_uint8_p, c_int8_p, ctypes.c_size_t]

lib.run_dot_product_sse41.restype = ctypes.c_int32
lib.run_dot_product_sse41.argtypes = [c_uint8_p, c_int8_p, ctypes.c_size_t]

lib.run_dot_product_avx2.restype = ctypes.c_int32
lib.run_dot_product_avx2.argtypes = [c_uint8_p, c_int8_p, ctypes.c_size_t]

lib.run_dot_product_avx512.restype = ctypes.c_int32
lib.run_dot_product_avx512.argtypes = [c_uint8_p, c_int8_p, ctypes.c_size_t]

lib.run_dot_product_vnni.restype = ctypes.c_int32
lib.run_dot_product_vnni.argtypes = [c_uint8_p, c_int8_p, ctypes.c_size_t]


# --- 2. C 함수를 호출하는 파이썬 래퍼 함수 정의 ---

def run_scalar(a, b, size):
    return lib.run_dot_product_scalar(a, b, size)


def run_sse41(a, b, size):
    return lib.run_dot_product_sse41(a, b, size)


def run_avx2(a, b, size):
    return lib.run_dot_product_avx2(a, b, size)


def run_avx512(a, b, size):
    return lib.run_dot_product_avx512(a, b, size)


def run_vnni(a, b, size):
    return lib.run_dot_product_vnni(a, b, size)


# --- 3. 메인 스크립트 로직 ---

DATA_SIZE = 1024 * 1024 * 32

# CPU 지원 수준을 프로그램 시작 시 한 번만 확인
supported_level = lib.get_best_simd_level()

# 사용할 함수와 이름을 미리 결정
if supported_level == SIMD_LEVEL_VNNI:
    workload_name = "AVX512-VNNI"
    workload_func = run_vnni
elif supported_level == SIMD_LEVEL_AVX512:
    workload_name = "AVX512 (No VNNI)"
    workload_func = run_avx512
elif supported_level == SIMD_LEVEL_AVX2:
    workload_name = "AVX2"
    workload_func = run_avx2
elif supported_level == SIMD_LEVEL_SSE41:
    workload_name = "SSE4.1"
    workload_func = run_sse41
else:
    workload_name = "Scalar"
    workload_func = run_scalar

print(f"워크로드 시작. 선택된 함수: [{workload_name}]")
print(f"Ctrl+C를 눌러 종료하세요.")
print("-" * 30)

# 벤치마크용 데이터 생성
data_a = (ctypes.c_uint8 * DATA_SIZE)()
data_b = (ctypes.c_int8 * DATA_SIZE)()
for i in range(DATA_SIZE):
    data_a[i] = i % 128
    data_b[i] = (i % 64) - 32

# 무한 루프 시작
while True:
    # 선택된 워크로드 함수를 한 번 실행
    start_time = time.perf_counter()
    result = workload_func(data_a, data_b, DATA_SIZE)
    end_time = time.perf_counter()

    execution_time_ms = (end_time - start_time) * 1000

    # 결과 출력
    print(f"[{workload_name}] 실행 완료. 결과: {result}, 소요 시간: {execution_time_ms:.3f} ms")

    # 5초 대기
    time.sleep(5)
