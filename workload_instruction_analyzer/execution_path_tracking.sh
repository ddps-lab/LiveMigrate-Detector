#!/bin/bash

# Enable debugging output
set -x
echo "=== DEBUG: Starting execution_path_tracking.sh ==="
echo "=== DEBUG: Script called with arguments: $@ ==="

if [ -z "$1" ]; then
    echo "ERROR: A PID must be provided as a parameter."
    exit 1
fi

if [ -z "$2" ]; then
    echo "ERROR: A language type must be provided as a parameter."
    exit 1
fi

echo "=== DEBUG: PID provided: $1 ==="
echo "=== DEBUG: Language type provided: $2 ==="

if [ "$2" == "python" ]; then
    if [ -z "$3" ]; then
        echo "ERROR: A script path must be provided as a parameter for python."
        exit 1
    else
        export SCRIPT_PATH=$3
        echo "=== DEBUG: Script path set to: $3 ==="
    fi
else
    if [ ! -z "$3" ]; then
        echo "WARNING: A script path is not required for non-python languages."
        exit 1
    fi
fi

export WORKLOAD_PID=$1
export LANGUAGE_TYPE=$2

echo "=== DEBUG: Environment variables set ==="
echo "=== DEBUG: WORKLOAD_PID=$WORKLOAD_PID ==="
echo "=== DEBUG: LANGUAGE_TYPE=$LANGUAGE_TYPE ==="
echo "=== DEBUG: SCRIPT_PATH=$SCRIPT_PATH ==="

# xedlib
export LD_LIBRARY_PATH=/home/ubuntu/xed/obj:$LD_LIBRARY_PATH
echo "=== DEBUG: LD_LIBRARY_PATH updated: $LD_LIBRARY_PATH ==="

# Bytecode Tracking
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/bytecode_tracking
echo "=== DEBUG: Added bytecode_tracking to PYTHONPATH ==="

# stdlib_list
export PYTHONPATH=$PYTHONPATH:/home/ubuntu/.local/lib/python3.10/site-packages/
echo "=== DEBUG: Added stdlib_list to PYTHONPATH ==="

# entry path
export PYTHONPATH=$PYTHONPATH:$(dirname "$3")
echo "=== DEBUG: Added entry path to PYTHONPATH: $(dirname "$3") ==="
echo "=== DEBUG: Final PYTHONPATH: $PYTHONPATH ==="

export START_TIME=$(date +%s.%N)
echo "=== DEBUG: START_TIME set to: $START_TIME ==="

# Check if process exists
if ! ps -p $1 > /dev/null; then
    echo "ERROR: Process with PID $1 does not exist"
    exit 1
fi

echo "=== DEBUG: Process $1 exists and is running ==="

# Check if GDB script exists
GDB_SCRIPT="/home/ubuntu/LiveMigrate-Detector/workload_instruction_analyzer/gdb_script_exepath_tracking.py"
if [ ! -f "$GDB_SCRIPT" ]; then
    echo "ERROR: GDB script not found at $GDB_SCRIPT"
    exit 1
fi

echo "=== DEBUG: GDB script found at $GDB_SCRIPT ==="

# Check if xed library exists
XED_LIB="/home/ubuntu/xed/obj"
if [ ! -d "$XED_LIB" ]; then
    echo "ERROR: XED library directory not found at $XED_LIB"
    exit 1
fi

echo "=== DEBUG: XED library directory found ==="

# Run GDB
echo "=== DEBUG: Starting GDB with process $1 ==="
echo "=== DEBUG: GDB command: gdb -p $1 -x $GDB_SCRIPT ==="

gdb -p $1 -x $GDB_SCRIPT

GDB_EXIT_CODE=$?
echo "=== DEBUG: GDB finished with exit code: $GDB_EXIT_CODE ==="
echo "=== DEBUG: execution_path_tracking.sh completed ==="
