import subprocess

result = subprocess.run(['sudo', 'criu', 'cpuinfo', 'check'], cwd='/home/ubuntu/migration_test', stdout=subprocess.PIPE)

if result.returncode == 0:
    with open('/home/ubuntu/migration_test/cpuinfo.log', 'a') as f:
        print('compatibility : true', file=f)
else:
    with open('/home/ubuntu/migration_test/cpuinfo.log', 'a') as f:
        print('compatibility : false', file=f)