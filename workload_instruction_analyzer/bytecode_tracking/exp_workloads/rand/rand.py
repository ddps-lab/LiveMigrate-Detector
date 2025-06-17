import ctypes
import time

# librand.so 파일을 로드합니다.
librand = ctypes.CDLL(f'/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking/exp_workloads/rand/librand.so')

# 반환 유형과 인자 유형을 설정합니다.
# 이 경우, 함수는 unsigned long long 타입을 반환하고, 인자는 없습니다.
librand.generate_random_number_rdseed.restype = ctypes.c_ulonglong

def generate_random_number_rdseed():
    return librand.generate_random_number_rdseed()

def generate_random_number_rdrand():
   return librand.generate_random_number_rdrand()

def check_rdseed_support():
    return librand.check_rdseed_support()

is_rdseed_support = check_rdseed_support()

while(True):
  # 함수를 호출하고 결과를 출력합니다.
  if is_rdseed_support:
    random_number = generate_random_number_rdseed()
    print(f"Generated random number using RDSEED: {random_number}")
  else:
    random_number = generate_random_number_rdrand()
    print(f"Generated random number using RDRAND: {random_number}")     

  time.sleep(5)