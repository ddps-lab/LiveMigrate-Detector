from sha import sha256_hash
import time

# 해시할 메시지
message = b"Hello, World!"

while(True):
    # sha256_hash 함수를 호출하여 해시 값을 얻음
    hash_value = sha256_hash(message)
    
    # 해시 값을 16진수 문자열로 변환하여 출력
    print(f"SHA-256 hash of '{message.decode()}': {hash_value.hex()}")

    time.sleep(3)
