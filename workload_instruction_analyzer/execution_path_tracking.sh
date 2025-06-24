#!/bin/bash

echo "[SHELL] Starting execution_path_tracking.sh with parameters: $@"

if [ -z "$1" ]; then
    echo "[SHELL ERROR] A PID must be provided as a parameter."
    exit 1
fi

if [ -z "$2" ]; then
    echo "[SHELL ERROR] A language type must be provided as a parameter."
    exit 1
fi

echo "[SHELL] PID: $1"
echo "[SHELL] Language Type: $2"

if [ "$2" == "python" ]; then
    if [ -z "$3" ]; then
        echo "[SHELL ERROR] A script path must be provided as a parameter for python."
        exit 1
    else
        export SCRIPT_PATH=$3
        echo "[SHELL] Script Path: $3"
    fi
else
    if [ ! -z "$3" ]; then
        echo "[SHELL WARNING] A script path is not required for non-python languages."
        exit 1
    fi
fi

export WORKLOAD_PID=$1
export LANGUAGE_TYPE=$2

# xedlib
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH
echo "[SHELL] XED library path set: $LD_LIBRARY_PATH"

# Bytecode Tracking
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking
# stdlib_list
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/.local/lib/python3.10/site-packages/
# entry path
export PYTHONPATH=$PYTHONPATH:$(dirname "$3")

echo "[SHELL] PYTHONPATH set: $PYTHONPATH"

export START_TIME=$(date +%s.%N)
echo "[SHELL] Start time recorded: $START_TIME"

echo "[SHELL] Starting GDB with process $1..."

# Run GDB
gdb -p $1 -x /home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/gdb_script_exepath_tracking.py

echo "[SHELL] GDB execution completed"
