#!/bin/bash

# Check if the first parameter is provided
if [ -z "$1" ]; then
    echo "Warning: A PID must be provided as a parameter."
    exit 1
fi

if [ -z "$2" ]; then
    echo "Warning: A languege type must be provided as a parameter."
    exit 1
fi

export WORKLOAD_PID=$1
export LANGUAGE_TYPE=$2

# xedlib
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH

# Bytecode Tracking
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking
# stdlib_list
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/.local/lib/python3.10/site-packages/

# Run GDB
gdb -p $1 -x /home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/gdb_script_exepath_tracking.py
