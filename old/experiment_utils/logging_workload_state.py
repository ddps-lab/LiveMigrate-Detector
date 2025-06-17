import time
import sys
import subprocess

def workloadIsContinuous(workload):
    time.sleep(20)

    command = f"ps aux | grep 'python3 {workload}' | grep -v 'bash -c' | grep -v grep | awk '{{print $2}}'"
    result = subprocess.run(command, stdout=subprocess.PIPE, shell=True, text=True)

    if len(result.stdout) != 0:
        with open("/home/ubuntu/migration_test/timestamp.log", "a") as f:
            print("migration_success : true", file=f)
    else:
        with open("/home/ubuntu/migration_test/timestamp.log", "a") as f:
            print("migration_success : false", file=f)    

if len(sys.argv) > 1:
    workload = sys.argv[1]
    workloadIsContinuous(workload)
else:
    print("Usage: python script.py <workload>")
