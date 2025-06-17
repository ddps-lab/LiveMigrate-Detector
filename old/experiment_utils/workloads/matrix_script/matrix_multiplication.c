#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <cblas.h>

int main() {
    // 행렬의 크기를 설정합니다.
    int m = 4, n = 4, k = 4;
    // 행렬 A, B, C를 선언합니다.
    double A[m*k], B[k*n], C[m*n];
    int i, j;

    // 행렬 A와 B를 초기화합니다.
    for (i = 0; i < m; ++i) {
        for (j = 0; j < k; ++j) {
            A[i*k + j] = i*k + j + 1;
        }
    }

    for (i = 0; i < k; ++i) {
        for (j = 0; j < n; ++j) {
            B[i*n + j] = i*n + j + 1;
        }
    }

    while(1){
        // OpenBLAS를 사용하여 행렬 곱셈을 수행합니다.
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, m, n, k, 1.0, A, k, B, n, 0.0, C, n);

        // 결과 행렬 C를 출력합니다.
        printf("Result matrix C:\n");
        for (i = 0; i < m; ++i) {
            for (j = 0; j < n; ++j) {
                printf("%.2f ", C[i*n + j]);
            }
            printf("\n");
        }

        sleep(3);
    }

    return 0;
}
