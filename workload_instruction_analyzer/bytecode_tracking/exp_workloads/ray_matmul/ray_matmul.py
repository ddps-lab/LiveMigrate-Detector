import ray
import time

# Ray 초기화
ray.init()


@ray.remote
def matrix_multiply(a, b):
    # Python 기본 기능으로 행렬 곱셈 구현
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])

    result = [[0 for _ in range(cols_b)] for _ in range(rows_a)]

    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += a[i][k] * b[k][j]

    return result


# 고정된 배열 생성
matrix_a = [[1, 2, 3], [4, 5, 6]]  # 2x3
matrix_b = [[7, 8], [9, 10], [11, 12]]  # 3x2

while True:
    # Ray를 사용한 행렬 곱셈
    result_ref = matrix_multiply.remote(matrix_a, matrix_b)
    result = ray.get(result_ref)

    # 결과 출력
    print(result)

    # 5초 대기
    time.sleep(5)
