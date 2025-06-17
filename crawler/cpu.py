import requests
from bs4 import BeautifulSoup
from decimal import Decimal
import json


def get_cpu_name(name):
    if name.startswith("2nd Gen "):
        name = name[8:]
    data = {
        "Intel Xeon Platinum 8175": [
            "Intel Skylake P-8175",
        ],
        "Intel Xeon E7-8880v3": [
            "Intel Xeon E7 8880 v3",
            "Intel Haswell E7 8880v3",
        ],
        "Intel Xeon E5-2676v3": [
            "Intel Xeon E52676v3",
        ],
        "Intel Xeon Platinum 8259L": [
            "Intel Xeon P-8259L",
        ],
        "Intel Xeon E5-2686v4": [
            "Intel Xeon E5-2686 v4",
            "Intel Broadwell E5-2686v4",
        ],
        "Intel Xeon Platinum 8375C": [
            "Intel Xeon Ice Lake 8375C",
        ],
        "Intel Xeon Platinum 8259CL": [
            "Intel Cascade Lake P-8259CL",
        ],
        "Intel Xeon E5-2650": [
            "Intel E5-2650",
        ],
        "Intel Xeon Platinum 8275CL": [
            "Intel Xeon P-8275CL",
        ],
        "Intel Xeon Emerald Rapids": [
            "Intel Emerald Rapids",
        ]
    }
    for i in data:
        if name in data[i]:
            return i

    return name


datas = {}
for i in ["gp", "co", "mo", "so", "ac", "hpc", "pg"]:
    html = requests.get(
        f"https://docs.aws.amazon.com/en_us/ec2/latest/instancetypes/{i}.html").content.decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")
    hwlist = soup.select(f"#{i}_hardware + .table-container table > tr")
    for j in hwlist:
        tds = j.select("td")
        if len(tds) == 1:
            continue
        instance, _, memory, processor, vcpu, cores, * \
            _ = map(lambda x: x.text.strip(), tds)
        if not "Intel" in processor and not "AMD" in processor:
            continue
        processor = get_cpu_name(processor)
        if processor not in datas:
            datas[processor] = []
        datas[processor].append({
            "instance": instance,
            "memory": memory,
            "vcpu": vcpu,
            "cores": cores,
        })

with open("cpu-instance.json", "w") as f:
    f.write(json.dumps(datas, indent=4))

with open("cpu.txt", "w") as f:
    for i in datas:
        f.write(i + "\n")
