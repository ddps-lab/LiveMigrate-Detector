import subprocess
import csv
import pandas as pd

interpret_file = '/home/ubuntu/migration_test/ins_disas/log/ins_interpret.csv'

def interpret_instruction(instruction_binary):
    xed_path = "/home/ubuntu/.guix-profile/bin/xed"
    command = f"{xed_path} -64 -d {instruction_binary}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    return result