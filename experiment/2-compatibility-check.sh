#!/bin/bash
set -e

snap install aws-cli --classic
cd /home/ubuntu/
aws s3 cp s3://shlee-pygration/1-collect-info.tar.zst - --region us-west-2 --no-sign-request | tar -I zstd -xvf -

# --- 변수 및 설정 ---
INFO_DIR="/home/ubuntu/1-collect-info"
RESULT_DIR="/home/ubuntu/result2"
mv /home/ubuntu/result $RESULT_DIR
mkdir -p "$RESULT_DIR"

cd /home/ubuntu/LiveMigrate-Detector/cpu_feature_collector/
./collector > $RESULT_DIR/isaset.csv

# 각 워크로드와 매칭되는 "준비 완료" 문자열
declare -A ready_strings
ready_strings["dask_matmul"]="]]"
ready_strings["dask_uuid"]="Final Result"
ready_strings["falcon_http"]="healthy"
ready_strings["int8dot"]="Execution time"
ready_strings["llm"]="remaining 1 prompt tokens to eval"
ready_strings["matmul"]="]]"
ready_strings["pku"]="Memory has been released"
ready_strings["rand"]="Generated random number"
ready_strings["rsa"]="Encrypted text"
ready_strings["sha"]="SHA-256 hash"
ready_strings["xgboost"]="mlogloss"

# --- 스크립트 시작 ---
echo "Starting Experiment 2: Restore and Validate (Concurrent Workloads)"

# 소스 인스턴스 타입별로 반복
for source_instance_dir in "$INFO_DIR"/*; do
    [ ! -d "$source_instance_dir" ] && continue
    source_instance_type=$(basename "$source_instance_dir")
    echo "==> Source Instance: $source_instance_type"

    # 심볼릭 링크 생성
    rm -rf /home/ubuntu/result
    ln -s "$source_instance_dir" /home/ubuntu/result
    cd /home/ubuntu/result

    # CPU 호환성 체크
    check_result_file="$RESULT_DIR/${source_instance_type}_check.log"
    echo "    Running criu cpuinfo check for $source_instance_type..."
    criu cpuinfo check &> "$check_result_file" || true

    # --- 1. 모든 워크로드를 백그라운드에서 동시에 시작 ---
    declare -A pids_to_names             # PID를 키로, 워크로드 이름을 값으로 저장
    declare -A pids_to_app_logs          # PID -> 앱 로그 파일 경로
    declare -A pids_to_restore_logs      # PID -> 복원 로그 파일 경로
    declare -A pids_to_ready_strings     # PID -> "준비 완료" 문자열
    declare -A pids_to_initial_sizes     # PID -> 초기 로그 파일 크기
    declare -A pids_to_dmesg_starts      # PID -> dmesg 시작 시간
    declare -A pids_to_start_times       # PID -> 타임아웃 계산을 위한 시작 시간(초)

    echo "--> Starting all workloads concurrently..."
    for workload_dir in /home/ubuntu/result/*; do
        [ ! -d "$workload_dir" ] && continue
        workload_name=$(basename "$workload_dir")
        
        # 검증에 필요한 변수 설정
        app_log_file="/home/ubuntu/result/${workload_name}.log"
        restore_log_file="$RESULT_DIR/${source_instance_type}_${workload_name}_restore.log"
        ready_string="${ready_strings[$workload_name]}"

        # 복원 전, 기존 로그 파일 크기 확인
        initial_size=0
        if [ -f "$app_log_file" ]; then
            initial_size=$(stat -c%s "$app_log_file")
        fi

        dmesg_start_time=$(date +"%F %T.%N")
        
        # 백그라운드에서 복원 실행
        (criu-ns restore -D "$workload_dir" --skip-file-rwx-check) &> "$restore_log_file" &
        restore_pid=$!
        
        echo "    Started '$workload_name' with PID: $restore_pid"

        # PID와 관련 정보들을 연관 배열에 저장
        pids_to_names[$restore_pid]="$workload_name"
        pids_to_app_logs[$restore_pid]="$app_log_file"
        pids_to_restore_logs[$restore_pid]="$restore_log_file"
        pids_to_ready_strings[$restore_pid]="$ready_string"
        pids_to_initial_sizes[$restore_pid]=$initial_size
        pids_to_dmesg_starts[$restore_pid]="$dmesg_start_time"
        pids_to_start_times[$restore_pid]=$(date +%s)
    done

    # --- 2. 모든 워크로드가 끝날 때까지 상태를 폴링하며 확인 ---
    echo "--> Waiting for all workloads to be validated (max 300s)..."
    while (( ${#pids_to_names[@]} > 0 )); do
        for pid in "${!pids_to_names[@]}"; do
            workload_name="${pids_to_names[$pid]}"
            status=""

            # 1. 프로세스 생존 여부 확인
            if ! ps -p $pid > /dev/null; then
                status="crashed"
            # 2. 로그 파일에서 "준비 완료" 문자열 확인
            elif tail -c +$(( ${pids_to_initial_sizes[$pid]} + 1 )) "${pids_to_app_logs[$pid]}" 2>/dev/null | grep -qF "${pids_to_ready_strings[$pid]}"; then
                status="success"
            # 3. 시간 초과 확인
            elif (( $(date +%s) - ${pids_to_start_times[$pid]} > 600 )); then
                status="timeout"
            fi

            # 상태가 결정되면 처리 후, 추적 목록에서 제거
            if [ -n "$status" ]; then
                restore_log_file="${pids_to_restore_logs[$pid]}"
                dmesg_start_time="${pids_to_dmesg_starts[$pid]}"

                if [ "$status" = "success" ]; then
                    echo "    [SUCCESS] '$workload_name' (PID: $pid) restored and validated."
                    echo "Success: Process $pid fully restored and validated." >> "$restore_log_file"
                elif [ "$status" = "crashed" ]; then
                    echo "    [FAILURE] '$workload_name' (PID: $pid) terminated unexpectedly."
                    echo "Failure: Process $pid terminated unexpectedly." >> "$restore_log_file"
                    journalctl -k --since "$dmesg_start_time" >> "$restore_log_file"
                else # timeout
                    echo "    [FAILURE] '$workload_name' (PID: $pid) timed out after 300 seconds."
                    echo "Failure: Timeout. Process $pid is running but did not produce ready string within 300 seconds." >> "$restore_log_file"
                    journalctl -k --since "$dmesg_start_time" >> "$restore_log_file"
                fi
                
                # 처리 완료된 PID를 모든 추적 배열에서 제거
                unset 'pids_to_names[$pid]'
                unset 'pids_to_app_logs[$pid]'
                unset 'pids_to_restore_logs[$pid]'
                unset 'pids_to_ready_strings[$pid]'
                unset 'pids_to_initial_sizes[$pid]'
                unset 'pids_to_dmesg_starts[$pid]'
                unset 'pids_to_start_times[$pid]'
            fi
        done
        sleep 0.5 # 0.5초 간격으로 모든 프로세스 상태 확인
    done
    
    echo "--> All workloads for '$source_instance_type' have been processed."

    # 모든 워크로드 처리가 끝난 후, 관련 프로세스 정리
    pkill -9 -f "python3.*\.py$" || true
    sleep 1
done

# 최종 정리
rm -rf /home/ubuntu/result
mv /home/ubuntu/result2 /home/ubuntu/result

echo "Experiment 2 finished."