#!/bin/bash

if [ -z "$1" ]; then
    echo "Warning: A PID must be provided as a parameter."
    exit 1
fi

if [ -z "$2" ]; then
    echo "Warning: A language type must be provided as a parameter."
    exit 1
fi

if [ "$2" == "python" ]; then
    if [ -z "$3" ]; then
        echo "Warning: A script path must be provided as a parameter for python."
        exit 1
    else
        export SCRIPT_PATH=$3
    fi
else
    if [ ! -z "$3" ]; then
        echo "Warning: A script path is not required for non-python languages."
        exit 1
    fi
fi

export WORKLOAD_PID=$1
export LANGUAGE_TYPE=$2

# xedlib
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH

# Bytecode Tracking
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking
# stdlib_list
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/.local/lib/python3.10/site-packages/
# entry path
export PYTHONPATH=$PYTHONPATH:$(dirname "$3")

export START_TIME=$(date +%s.%N)

# Run GDB
gdb -p $1 -x /home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/gdb_script_bytecode_only_exepath_tracking.py
