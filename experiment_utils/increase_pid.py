import subprocess
import random

value = random.randint(1, 5000)

for i in range(value):
    subprocess.call('ls', shell=True)