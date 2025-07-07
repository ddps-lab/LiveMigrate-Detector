import pku
import ctypes
import mmap
import time

# 1. 페이지 크기 확인
PAGE_SIZE = mmap.PAGESIZE

# 2. CPU가 PKU를 지원하는지 확인
pku_supported = pku.check_pku_support()
print(f"PKU supported: {pku_supported}", flush=True)

while (True):
    # 3. 페이지 경계에 맞게 메모리 할당
    # mmap을 이용해 페이지 경계에 맞는 메모리 블록 할당
    buffer = mmap.mmap(-1, PAGE_SIZE, prot=mmap.PROT_READ | mmap.PROT_WRITE)

    # 4. 메모리 주소를 가져오기
    buffer_address = ctypes.addressof(ctypes.c_char.from_buffer(buffer))
    print(f"Buffer address: {buffer_address:#x}",
          flush=True)  # 메모리 주소를 16진수로 출력

    # 5. 페이지 정렬 확인
    if buffer_address % PAGE_SIZE != 0:
        raise RuntimeError(
            f"Buffer address is not aligned: {buffer_address:#x}")

    # 6. 메모리에 값을 씀
    value_to_write = b'A'
    print(
        f"Attempting to write value '{value_to_write.decode()}' to memory at address {buffer_address:#x}", flush=True)
    pku.write_memory(value_to_write, buffer_address)
    print(f"Value written to memory: {value_to_write.decode()}", flush=True)

    # 7. 메모리를 보호
    if pku_supported:
        pku.protect_memory_pku(buffer_address)
        print("Memory protected using PKU.", flush=True)
    else:
        pku.protect_memory_mprotect(buffer_address)
        print("Memory protected using mprotect.", flush=True)

    # 8. 보호된 메모리에 값을 쓰려고 시도 (여기서 세그멘테이션 오류가 발생할 수 있음)
    try:
        value_to_write = b'B'
        print(
            f"Attempting to write value '{value_to_write.decode()}' to memory at address {buffer_address:#x}", flush=True)
        pku.write_memory(value_to_write, buffer_address)
    except RuntimeError as e:
        pass

    # 9. 메모리 보호 해제
    pku.unprotect_memory(pku_supported, buffer_address)
    print("Memory protection lifted.", flush=True)

    # 10. 보호 해제된 메모리에 값을 다시 씀
    pku.write_memory(b'C', buffer_address)
    print("Value written to memory after unprotecting: C", flush=True)

    # 11. 메모리에서 값을 읽음
    value_read = pku.read_memory(buffer_address)
    print(f"Value read from memory: {value_read.decode()}", flush=True)

    # 12. 메모리 해제
    buffer.close()
    print("Memory has been released.", flush=True)

    time.sleep(5)
