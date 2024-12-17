import numpy as np
import time

# 두 개의 행렬 정의
A = np.array([[1, 2, 3],
              [4, 5, 6]])

B = np.array([[7, 8],
              [9, 10],
              [11, 12]])

# 행렬곱 수행
C = np.dot(A, B)
D = np.matmul(A, B)

print("Matrix A:")
print(A)
print("\nMatrix B:")
print(B)
print("\nMatrix A * B(dot):")
print(C)
print("\nMatrix A * B(matmul):")
print(D)

time.sleep(10000)