#!/bin/bash

# GDB 실행 전 시간 기록
export GDB_START_TIME=$(date +%s.%N)

export WORKLOAD_PID=$1

# xedlib
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH

echo 3 > /proc/sys/vm/drop_caches

# GDB 실행
gdb -p $1 -x /home/ubuntu/migration_test/ins_disas/gdb_script_func_tracking.py

kill -9 $1