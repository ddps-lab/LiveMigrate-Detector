import time
import random
import int8dot  # 빌드한 C 확장 모듈

# --- 설정 ---
DATA_SIZE = 1024 * 1024 * 32  # 32MB

# 1. 어떤 커널이 선택되었는지 확인
selected_kernel = int8dot.get_selected_kernel()
print(f"✅ Runtime selected kernel: {selected_kernel}")
print(f"✅ Data size for each loop: {DATA_SIZE // (1024*1024)} MB")
print("--- Starting infinite loop (Press Ctrl+C to exit) ---\n")

# 2. 무한 루프 시작
loop_count = 0
while True:
    loop_count += 1
    print(f"--- Loop {loop_count} ---")

    # 데이터 생성
    a_bytes = bytearray(random.choices(range(128), k=DATA_SIZE))
    b_bytes = bytearray(random.choices(range(256), k=DATA_SIZE))

    # 성능 측정
    start_time = time.perf_counter()
    result = int8dot.dot_product(a_bytes, b_bytes)
    end_time = time.perf_counter()

    elapsed_ms = (end_time - start_time) * 1000

    print(f"   Result: {result}")
    print(f"   Execution time: {elapsed_ms:.2f} ms")

    # 5초 대기
    time.sleep(5)
    print()  # 루프 사이에 한 줄 띄우기
