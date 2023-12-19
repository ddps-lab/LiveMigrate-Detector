#!/bin/bash

# GDB 실행 전 시간 기록
export GDB_START_TIME=$(date +%s.%N)

# xedlib
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH

echo 3 > /proc/sys/vm/drop_caches

# GDB 실행
gdb -p 1964 -x gdb_script_entire_scanning.py
