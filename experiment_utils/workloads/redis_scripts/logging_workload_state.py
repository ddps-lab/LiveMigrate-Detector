import time
import redis

def pidCheck():
    src_pids = []
    dst_pids = []
    with open("/home/ubuntu/migration_test/src-pids.log", "r") as file:
        lines = file.readlines()

        src_pids = [int(item.strip()) for item in lines]

    with open("/home/ubuntu/migration_test/dst-pids.log", "r") as file:
        lines = file.readlines()

        dst_pids = [int(item.strip()) for item in lines]

    if any(item in dst_pids for item in src_pids):
        with open("/home/ubuntu/migration_test/timestamp.log", "a") as f:
            print("migration_success : PID conflict", file=f)

        exit()

def processIsContinuous():
    try:
        # Redis 서버에 연결
        r = redis.StrictRedis(host='localhost', port=7777, db=0)

        # 데이터 읽기 (Read)
        value = r.get('testKey')
        print(value)
        if value == None:
            return False
        
        if value.decode() == 'testValue':
            print(f'value: {value.decode()}')
            return True
    except redis.exceptions.ConnectionError:
        return False

if __name__ == '__main__':
    pidCheck()
    isSuccess = processIsContinuous()

    if isSuccess:
        with open("/home/ubuntu/migration_test/timestamp.log", "a") as f:
            print("migration_success : true", file=f)
    else:
        with open("/home/ubuntu/migration_test/timestamp.log", "a") as f:
            print("migration_success : false", file=f)