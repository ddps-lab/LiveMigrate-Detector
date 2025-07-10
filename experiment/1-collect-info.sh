#!/bin/bash
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH
export LD_BIND_NOW=1

cd /home/ubuntu/LiveMigrate-Detector
git pull

cd /home/ubuntu/result
sudo criu cpuinfo dump

root_path="/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking/exp_workloads"
result_path="/home/ubuntu/result"

# 각 테스트와 매칭되는 "준비 완료" 문자열을 저장하는 연관 배열
# IMPORTANT: 각 테스트에 맞는 실제 출력 문자열로 반드시 수정해주세요.
declare -A ready_strings
ready_strings["dask_matmul/dask_matmul.py"]="]]"
ready_strings["falcon_http/falcon_http.py"]="healthy"
ready_strings["int8dot/int8dot_test.py"]="Execution time"
ready_strings["llm/llm.py"]="remaining 1 prompt tokens to eval"
ready_strings["matmul/matmul.py"]="]]"
ready_strings["pku/pku_test.py"]="Memory has been released"
ready_strings["rand/rand.py"]="Generated random number"
ready_strings["rsa/rsa_test.py"]="Encrypted text"
ready_strings["sha/sha_test.py"]="SHA-256 hash"
ready_strings["xgboost/xgb_example.py"]="mlogloss"

# 실행할 테스트 목록
test_array=("dask_matmul/dask_matmul.py" "falcon_http/falcon_http.py" "int8dot/int8dot_test.py" "llm/llm.py" "matmul/matmul.py" "pku/pku_test.py" "rand/rand.py" "rsa/rsa_test.py" "sha/sha_test.py" "xgboost/xgb_example.py")

# --- 스크립트 시작 ---

cd /home/ubuntu/LiveMigrate-Detector/cpu_feature_collector/
./collector > $result_path/isaset.csv

for test in "${test_array[@]}"; do
    test_dir="${test%/*}"
    test_file="${test##*/}"
    log_file="$result_path/$test_dir.log"
    ready_string="${ready_strings[$test]}"

    echo "--- [START] Test: $test ---"

    # 로그 파일을 위한 디렉토리 생성
    mkdir -p "$(dirname "$log_file")"

    # 워크로드 디렉토리로 이동
    cd "$root_path/$test_dir"

    # 파이썬 스크립트를 백그라운드에서 실행하고 로그 파일에 출력 저장
    setsid python3 "$test_file" < /dev/null &> "$log_file" &
    pid=$(pgrep -f "python3 $test_file")
    echo "  -> Process started with PID: $pid"
    echo "  -> Logging to: $log_file"

    # 프로젝트의 루트 디렉토리로 복귀
    cd ../../../

    # 로그 파일에서 특정 "준비 완료" 문자열이 나타날 때까지 대기
    echo "  -> Waiting for ready string: '$ready_string'"
    while true; do
        # 로그 파일이 존재하고, 지정된 문자열이 포함되어 있는지 확인
        # -q: 출력 없음, -F: 고정 문자열로 검색 (정규식 아닌)
        if [ -f "$log_file" ] && grep -qF "$ready_string" "$log_file"; then
            echo "  -> Ready string found! Proceeding..."
            break
        fi

        # 프로세스가 예기치 않게 종료되었는지 확인
        if ! kill -0 $pid 2>/dev/null; then
            echo "  -> ERROR: Process $pid exited prematurely. Check log file for details."
            # 다음 테스트로 넘어가기 위해 바깥쪽 루프를 continue
            continue 2
        fi

        sleep 1 # 1초 간격으로 확인하여 CPU 사용량 줄임
    done

    # criu dump를 위한 디렉토리 생성
    mkdir -p "$result_path/$test_dir"

    # 이전 추적 결과 삭제
    rm -rf log/isa_set.csv

    # 실행 경로 추적 시작
    echo "  -> Running execution path tracking for $pid..."
    sudo -E ./execution_path_tracking.sh $pid native &> "$result_path/${test_dir}_native_ept.log"

    # 추적 결과 복사
    cp log/isa_set.csv "$result_path/$test_dir.native.csv"
    echo "  -> Result copied to $result_path/$test_dir.native.csv"

    # 이전 추적 결과 삭제
    rm -rf log/isa_set.csv

    # 바이트코드 실행 경로 추적 시작
    echo "  -> Running bytecode execution path tracking for $pid..."
    sudo -E ./execution_path_tracking.sh $pid python "$root_path/$test" &> "$result_path/${test_dir}_bytecode_ept.log"

    # 추적 결과 복사
    cp log/isa_set.csv "$result_path/$test_dir.bytecode.csv"
    echo "  -> Result copied to $result_path/$test_dir.bytecode.csv"

    # 프로세스 상태 덤프
    echo "  -> Dumping process $pid..."
    sudo criu-ns dump -t $pid -D "$result_path/$test_dir"
    if [ $? -ne 0 ]; then
        echo "  -> ERROR: CRIU dump failed for PID $pid."
        echo "  -> Killing process $pid."
        kill -9 $pid
    fi

    echo "--- [DONE] Test: $test ---"
    echo "" # 가독성을 위한 줄바꿈
done

echo "All tests completed."

sudo chown -R ubuntu:ubuntu /home/ubuntu/result