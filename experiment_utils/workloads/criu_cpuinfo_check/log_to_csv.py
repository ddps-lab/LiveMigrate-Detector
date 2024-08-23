import csv
from datetime import datetime

# Read performance.log
result = {}
with open("/home/ubuntu/migration_test/cpuinfo.log", "r") as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        if ":" in line:
            parts = line.split(":")

            key = parts[0].strip()
            value = parts[1].strip()
                
            result[key] = key
            result[key] = value


# Prepare data for CSV
data = {
    "Source": result.get("src", ""),
    "Destination": result.get("dst", ""),
    "Compatibility": result.get("compatibility", ""),
}

# Write data to CSV file
csv_filename = "/home/ubuntu/migration_test/cpuinfo.csv"
with open(csv_filename, "w", newline="") as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=data.keys())
    writer.writeheader()
    writer.writerow(data)
