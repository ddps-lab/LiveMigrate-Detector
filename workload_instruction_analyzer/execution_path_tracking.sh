#!/bin/bash
set -e

# Validate arguments
if [ $# -ne 3 ]; then
    echo "=== ERROR: Usage: $0 <PID> <LANGUAGE_TYPE> <SCRIPT_PATH> ==="
    exit 1
fi

PID=$1
LANGUAGE_TYPE=$2
SCRIPT_PATH=$3

echo "=== DEBUG: Starting execution path tracking ==="
echo "=== DEBUG: PID: $PID, Language: $LANGUAGE_TYPE ==="

# Validate PID
if ! kill -0 "$PID" 2>/dev/null; then
    echo "=== ERROR: Process $PID does not exist ==="
    exit 1
fi

# Validate script path
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "=== ERROR: Script file $SCRIPT_PATH not found ==="
    exit 1
fi

# Get script directory
SCRIPT_DIR=$(dirname "$(realpath "$0")")
echo "=== DEBUG: Script directory: $SCRIPT_DIR ==="

# Check XED library
XED_LIB="$SCRIPT_DIR/xedlib/libxedwrapper.so"
if [ ! -f "$XED_LIB" ]; then
    echo "=== ERROR: XED library not found: $XED_LIB ==="
    exit 1
fi

# Set environment variables
export START_TIME=$(date +%s.%N)
export WORKLOAD_PID=$PID
export LANGUAGE_TYPE=$LANGUAGE_TYPE
export SCRIPT_PATH=$SCRIPT_PATH
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

echo "=== DEBUG: Environment configured ==="

# Execute GDB script
echo "=== DEBUG: Launching GDB ==="
if gdb -batch -ex "attach $PID" -ex "source $SCRIPT_DIR/gdb_script_exepath_tracking.py" -ex "detach" -ex "quit"; then
    echo "=== DEBUG: GDB execution completed successfully ==="
    exit 0
else
    echo "=== ERROR: GDB execution failed ==="
    exit 1
fi
