import rsa
import time

plaintext = "Hello, OpenSSL!"

while True:
    # plaintext를 bytes로 변환
    encrypted_text = rsa.encrypt_with_rsa(plaintext.encode('utf-8'))
    print("Encrypted text:", encrypted_text)

    time.sleep(5)
