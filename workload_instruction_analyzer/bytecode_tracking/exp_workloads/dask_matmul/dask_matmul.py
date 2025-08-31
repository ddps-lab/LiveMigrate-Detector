import dask.array as da
import time

# 고정된 배열 생성
matrix_a = da.from_array([[1, 2, 3], [4, 5, 6]])  # 2x3
matrix_b = da.from_array([[7, 8], [9, 10], [11, 12]])  # 3x2

while True:
    # 행렬 곱셈
    result = da.dot(matrix_a, matrix_b).compute()

    # 결과 출력
    print(result, flush=True)

    # 5초 대기
    time.sleep(5)
