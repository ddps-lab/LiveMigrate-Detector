import time
import sys
import subprocess

def workloadIsContinuous(workload):
    time.sleep(20)

    result = subprocess.run(['pidof', workload], stdout=subprocess.PIPE)

    if result.returncode == 0:
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
