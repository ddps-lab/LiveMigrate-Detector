#!/bin/bash

# Check if the first parameter is provided
if [ -z "$1" ]; then
    echo "Warning: A PID must be provided as a parameter."
    exit 1
fi

export WORKLOAD_PID=$1

# xedlib
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH

# Run GDB
gdb -p $1 -x /home/ubuntu/migration_test/ins_disas/gdb_script_exepath_tracking.py
