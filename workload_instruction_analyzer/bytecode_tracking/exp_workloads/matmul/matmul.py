import numpy as np
import time

while True:
    # 두 개의 행렬 정의
    A = np.array([[1, 2, 3],
                  [4, 5, 6]])

    B = np.array([[7, 8],
                  [9, 10],
                  [11, 12]])

    # 행렬곱 수행
    C = np.dot(A, B)
    D = np.matmul(A, B)

    print("Matrix A:", flush=True)
    print(A, flush=True)
    print("\nMatrix B:", flush=True)
    print(B, flush=True)
    print("\nMatrix A * B(dot):", flush=True)
    print(C, flush=True)
    print("\nMatrix A * B(matmul):", flush=True)
    print(D, flush=True)
    time.sleep(5)
