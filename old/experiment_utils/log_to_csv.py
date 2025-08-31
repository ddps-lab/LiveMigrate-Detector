import csv
from datetime import datetime

# Read performance.log
performance_data = {}
with open("/home/ubuntu/migration_test/performance.log", "r") as performance_file:
    lines = performance_file.readlines()
    for line in lines:
        line = line.strip()
        if ":" in line:
            parts = line.split(":")

            if len(parts) != 2:
                continue

            key = parts[0].strip()
            value = parts[1].strip()
                
            # 단위 제거 183 us -> 183
            if " " in value:
                parts = value.split(" ")
                performance_data[key] = parts[0].strip()
            else:
                performance_data[key] = value


# Read timestamp.log
timestamp_data = {}
with open("/home/ubuntu/migration_test/timestamp.log", "r") as timestamp_file:
    lines = timestamp_file.readlines()
    for line in lines:
        line = line.strip()
        if " : " in line:
            parts = line.split(" : ")

            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                timestamp_data[key] = value

# Prepare data for CSV
data = {
    "Source": performance_data.get("src", ""),
    "Destination": performance_data.get("dst", ""),
    "Freezing time(us)": int(performance_data.get("Freezing time", 0)),
    "Frozen time(us)": int(performance_data.get("Frozen time", 0)),
    "Memory dump time(us)": int(performance_data.get("Memory dump time", 0)),
    "Memory write time(us)": int(performance_data.get("Memory write time", 0)),
    "IRMAP resolve time(us)": int(performance_data.get("IRMAP resolve time", 0)),
    "Memory pages scanned(dec)": int(performance_data.get("Memory pages scanned", 0)),
    "Memory pages skipped from parent(dec)": int(performance_data.get("Memory pages skipped from parent", 0)),
    "Memory pages written(dec)": int(performance_data.get("Memory pages written", 0)),
    "Lazy memory pages(dec)": int(performance_data.get("Lazy memory pages", 0)),
    "Pages compared(dec)": int(performance_data.get("Pages compared", 0)),
    "Pages skipped COW(dec)": int(performance_data.get("Pages skipped COW", 0)),
    "Pages restored(dec)": int(performance_data.get("Pages restored", 0)),
    "Restore time(us)": int(performance_data.get("Restore time", 0)),
    "Forking time(us)": int(performance_data.get("Forking time", 0)),
    "Start checkpoint": timestamp_data.get("start checkpoint", ""),
    "End checkpoint": timestamp_data.get("end checkpoint", ""),
    "Start restore": timestamp_data.get("start restore", ""),
    "End restore": timestamp_data.get("end restore", ""),
    "migration_success": timestamp_data.get("migration_success", ""),
    "count1": timestamp_data.get("count1", ""),
    "count2": timestamp_data.get("count2", "")
}

# Write data to CSV file
csv_filename = "/home/ubuntu/migration_test/migration_data.csv"
with open(csv_filename, "w", newline="") as csv_file:
    writer = csv.DictWriter(csv_file, fieldnames=data.keys())
    writer.writeheader()
    writer.writerow(data)
