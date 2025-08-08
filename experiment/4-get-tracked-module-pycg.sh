#!/bin/bash

mkdir -p result/4-get-tracked-module-pycg

test_array=("fastapi/fastapi_example.py" "int8dot/int8dot_test.py" "llm/llm.py" "pku/pku_test.py" "rand/rand.py" "rsa/rsa_test.py" "sha/sha_test.py")
package_array=("fastapi" "int8dot" "llama_cpp" "pku" "rand" "rsa" "sha")

for ((i=0; i<${#test_array[@]}; i++)); do
    test=${test_array[$i]}
    package=${package_array[$i]}
    test_dir="${test%/*}"
    test_file="${test##*/}"
    strace -e trace=openat python3 -m pycg -o /dev/null --package $package /home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking/exp_workloads/$test 2>&1 | sed -n '/exp_workloads/,$ { /\.py", O_RDONLY|O_CLOEXEC) = 3/p }' > result/4-get-tracked-module-pycg/$test_dir.txt
done