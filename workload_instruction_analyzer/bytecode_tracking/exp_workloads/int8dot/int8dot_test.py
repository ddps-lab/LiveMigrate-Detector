import time
import random
import int8dot

DATA_SIZE = 1024 * 1024 * 32

# CPU 기능 감지 (최초 1회)
features = int8dot.detect_features()
print("Detected CPU features:")
for key, value in sorted(features.items()):
    print(f"  {key}: {value}")

use_vnni = features.get("avx512_vnni", False)
use_avx512f = features.get(
    "avx512f", False) and features.get("avx512bw", False)
use_avx2 = features.get("avx2", False)
use_sse41 = features.get("sse41", False)

if not (use_vnni or use_avx512f or use_avx2 or use_sse41):
    print("\nNo supported SIMD kernel found for this CPU. Exiting.")
    exit(1)

print("\nStarting infinite loop (Press Ctrl+C to exit)...")
print(f"Data size per loop: {DATA_SIZE // (1024*1024)} MB\n")

loop_count = 0
while True:
    loop_count += 1
    print(f"--- Loop {loop_count} ---")

    a_bytes = bytearray(random.choices(range(256), k=DATA_SIZE))
    b_bytes = bytearray(random.choices(range(256), k=DATA_SIZE))

    result = 0
    kernel_name = "Unknown"

    start_time = time.perf_counter()

    if use_vnni:
        kernel_name = "AVX512-VNNI"
        result = int8dot.dot_product_vnni(a_bytes, b_bytes)
    elif use_avx512f:
        kernel_name = "AVX512F"
        result = int8dot.dot_product_avx512f(a_bytes, b_bytes)
    elif use_avx2:
        kernel_name = "AVX2"
        result = int8dot.dot_product_avx2(a_bytes, b_bytes)
    elif use_sse41:
        kernel_name = "SSE4.1"
        result = int8dot.dot_product_sse(a_bytes, b_bytes)

    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000

    print(f"  Kernel Used: {kernel_name}")
    print(f"  Result: {result}")
    print(f"  Execution time: {elapsed_ms:.2f} ms")

    time.sleep(5)
    print()
