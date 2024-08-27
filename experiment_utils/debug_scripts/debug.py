import time
import csv
import glob
import subprocess
import sys

def GetPath():
    for filename in glob.glob('/home/ubuntu/migration_test/*_to_*.csv'):
        path = filename
        return path

def MigrationFailureCheck(path):
    # Restore time(us)
    column_number1 = 14
    # migration_success
    column_number2 = 20

    # CSV 파일 열기
    with open(path, newline='') as csvfile:
        # CSV reader 객체 생성
        csv_reader = csv.reader(csvfile)
        
        # 첫 번째 행(헤더) 건너뛰기
        next(csv_reader)
        
        # Restore time(us) 추출
        for row in csv_reader:
            restore_time = row[column_number1]
            migration_success = row[column_number2]
            break

    # 복원 시간이 0인 경우 CRIU 복원 중 에러가 발생으로 판단.
    if migration_success == 'false' and int(restore_time) != 0:
        return True
    else:
        return False

def Debug(PID, src):
    subprocess.run(f'nohup sudo criu restore -j -s -D "/home/ubuntu/migration_test/dump/{ src }" &', shell=True)
    time.sleep(5)
    subprocess.run(f'nohup sudo gdb python -ex "attach { PID }" -ex "source /home/ubuntu/LiveMigrate-Detector/experiment_utils/debug_scripts/gdb_script.py" &', shell=True)

if __name__ == '__main__':
    PID = sys.argv[1]
    src = sys.argv[2]
    path = GetPath()

    if(MigrationFailureCheck(path)):
        Debug(PID, src)
