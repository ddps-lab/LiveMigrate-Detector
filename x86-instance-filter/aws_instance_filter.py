import os
import pandas as pd

csv_file = os.path.join(os.path.dirname(__file__), "AWS - ec2 price(us-west-2, 23.07.07).csv")

columns = ["API Name", "Physical Processor", "On Demand"]

df = pd.read_csv(csv_file, usecols=columns)

# Remove instances that are not available in us-west-2
df = df[df["On Demand"] != "unavailable"]

# Remove instances with ARM architecture (Graviton)
df = df[~df["Physical Processor"].str.contains("Graviton")]

# Select only the "API Name" column
df = df["API Name"]

output_csv_file = f"{os.path.dirname(__file__)}/AWS x86 instances(us-west-2, 23.07.07).csv"
df.to_csv(output_csv_file, index=False, header=False)
