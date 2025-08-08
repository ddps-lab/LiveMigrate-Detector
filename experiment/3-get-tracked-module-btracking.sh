#!/bin/bash

test_array=("beautifulsoup4/bs4_example.py" "dask_matmul/dask_matmul.py" "dask_uuid/dask_uuid.py" "falcon_http/falcon_http.py" "fastapi/fastapi_example.py" "int8dot/int8dot_test.py" "llm/llm.py" "matmul/matmul.py" "matplotlib/matplotlib_example.py" "pku/pku_test.py" "rand/rand.py" "rsa/rsa_test.py" "sha/sha_test.py" "sklearn/sklearn_example.py" "xgboost/xgb_example.py")

for test in "${test_array[@]}"; do
    test_dir="${test%/*}"
    test_file="${test##*/}"
    strace -e trace=openat -o /dev/stdout python3 btracking_only.py /home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking/exp_workloads/$test | sed -n '/exp_workloads/,$ { /\.pyc", O_RDONLY|O_CLOEXEC) = 3/p }' > result/3-get-tracked-module-btracking/$test_dir.txt
done