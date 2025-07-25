#!/bin/bash

# 첫 번째 인자가 비어있는지 확인하여 사용법 안내
if [ -z "$1" ]; then
    echo "❌ 오류: 분석할 Python 스크립트 경로를 인자로 전달해야 합니다."
    echo "사용법: $0 <path_to_your_python_script.py>"
    exit 1
fi

# 인자로 받은 Python 스크립트 경로를 변수에 저장
PYTHON_SCRIPT_PATH=$1

# 분석할 명령어 정의 (인자 사용)
COMMAND="python3 btracking_only.py ${PYTHON_SCRIPT_PATH}"
RUNS=5
WARMUP=2 # 제외할 앞부분 실행 횟수
SAMPLES=$((RUNS - WARMUP))

# 결과를 저장할 배열 선언
declare -a mem_usages
declare -a elapsed_times

echo "분석 대상: ${PYTHON_SCRIPT_PATH}"
echo "스크립트 성능 측정을 시작합니다... (총 ${RUNS}회 실행)"
echo "----------------------------------------"

# 지정된 횟수만큼 명령어 실행
for (( i=1; i<=RUNS; i++ ))
do
    echo "=> 실행 ${i}/${RUNS}"
    
    # /usr/bin/time -v의 출력은 stderr로 나오므로 stdout으로 리디렉션(2>&1)하여 변수에 저장
    output=$(/usr/bin/time -v $COMMAND 2>&1)
    
    # 최대 메모리 사용량 (kbytes) 추출
    mem=$(echo "$output" | grep "Maximum resident set size" | awk '{print $NF}')
    mem_usages+=($mem)
    
    # 총 소요 시간 (m:ss.ss 형식) 추출 후 초 단위로 변환
    time_str=$(echo "$output" | grep "Elapsed (wall clock) time" | awk '{print $NF}')
    minutes=$(echo "$time_str" | cut -d: -f1)
    seconds=$(echo "$time_str" | cut -d: -f2)
    total_seconds=$(echo "$minutes * 60 + $seconds" | bc)
    elapsed_times+=($total_seconds)
    
    echo "메모리: ${mem} KB, 시간: ${total_seconds} 초"
done

echo "----------------------------------------"
echo "처음 ${WARMUP}회 실행 결과는 제외하고 뒤 ${SAMPLES}회 실행 결과로 평균을 계산합니다."

# 평균 계산을 위한 변수 초기화
total_mem=0
total_time=0.0

# WARMUP 이후의 결과들만 합산
for (( i=WARMUP; i<RUNS; i++ ))
do
    total_mem=$((total_mem + mem_usages[i]))
    total_time=$(echo "$total_time + ${elapsed_times[i]}" | bc)
done

# bc를 사용하여 소수점 계산
avg_mem=$(echo "scale=2; $total_mem / $SAMPLES" | bc)
avg_time=$(echo "scale=2; $total_time / $SAMPLES" | bc)

echo "----------------------------------------"
printf "📈 **최종 결과 (뒤 %d회 평균)**\n" $SAMPLES
printf "   - 최대 메모리 사용량 평균: %.2f kbytes\n" $avg_mem
printf "   - 소요 시간 평균: %.2f 초\n" $avg_time
echo "----------------------------------------"