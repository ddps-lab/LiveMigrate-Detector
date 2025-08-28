import os
import hashlib
from collections import defaultdict
import boto3
import json

def get_file_hash(filepath):
    """Calculates the SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def get_instance_memory_details(region="us-west-2"):
    """
    Retrieves a dictionary of all EC2 instance types and their memory in GiB.
    """
    ec2_client = boto3.client('ec2', region_name=region)
    memory_details = {}
    next_token = None

    while True:
        try:
            if next_token:
                response = ec2_client.describe_instance_types(NextToken=next_token)
            else:
                response = ec2_client.describe_instance_types()
            
            for instance_type_info in response.get('InstanceTypes', []):
                instance_type = instance_type_info['InstanceType']
                memory_in_mib = instance_type_info['MemoryInfo']['SizeInMiB']
                memory_details[instance_type] = memory_in_mib / 1024 # Convert MiB to GiB
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        except Exception as e:
            print(f"An error occurred while fetching instance types: {e}")
            break
            
    return memory_details

def get_all_instance_prices(region="us-west-2"):
    """
    Retrieves a dictionary of all on-demand EC2 instance prices for a given region.
    """
    pricing_client = boto3.client('pricing', region_name='us-east-1')
    location = "US West (Oregon)" # Maps to us-west-2

    prices = {}
    next_token = None

    while True:
        filters = [
            {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': location},
            {'Type': 'TERM_MATCH', 'Field': 'termType', 'Value': 'OnDemand'},
            {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': 'Linux'},
            {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
            {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
            {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
        ]

        try:
            if next_token:
                response = pricing_client.get_products(
                    ServiceCode='AmazonEC2',
                    Filters=filters,
                    NextToken=next_token
                )
            else:
                response = pricing_client.get_products(
                    ServiceCode='AmazonEC2',
                    Filters=filters
                )

            for price_item_str in response.get('PriceList', []):
                price_item = json.loads(price_item_str)
                instance_type = price_item['product']['attributes']['instanceType']
                
                on_demand = price_item['terms']['OnDemand']
                on_demand_key = list(on_demand.keys())[0]
                price_dimensions = on_demand[on_demand_key]['priceDimensions']
                price_dimensions_key = list(price_dimensions.keys())[0]
                price_in_usd = float(price_dimensions[price_dimensions_key]['pricePerUnit']['USD'])

                if price_in_usd > 0:
                    prices[instance_type] = price_in_usd
            
            next_token = response.get('NextToken')
            if not next_token:
                break
        except Exception as e:
            print(f"An error occurred: {e}")
            break
            
    return prices

def get_cheapest_instance(instance_types, all_prices):
    """
    Finds the cheapest on-demand EC2 instance from a list of instance types using a pre-fetched price list.
    """
    min_price = float('inf')
    cheapest_instance = None

    for instance_type in instance_types:
        price = all_prices.get(instance_type)
        if price is not None and price < min_price:
            min_price = price
            cheapest_instance = instance_type

    if cheapest_instance:
        return cheapest_instance, min_price
    return None, None

def group_files_by_content(root_dir):
    """Groups files named 'isaset.csv' in subdirectories by their content."""
    groups = defaultdict(list)
    for subdir, _, files in os.walk(root_dir):
        if 'isaset.csv' in files:
            instance_type = os.path.basename(subdir)
            filepath = os.path.join(subdir, 'isaset.csv')
            file_hash = get_file_hash(filepath)
            groups[file_hash].append(instance_type)
    return groups

if __name__ == "__main__":
    base_dir = "result/0-cpuinfo-all"
    grouped_instances = group_files_by_content(base_dir)

    print("Fetching all instance prices from AWS...")
    all_prices_us_west_2 = get_all_instance_prices(region="us-west-2")
    print(f"Found prices for {len(all_prices_us_west_2)} instance types.")

    print("\nFetching instance memory details...")
    all_memory_details = get_instance_memory_details(region="us-west-2")
    print(f"Found memory details for {len(all_memory_details)} instance types.")

    warnings = []
    all_instances_in_groups = set()
    price_sum = 0
    final_instances = []

    for i, (file_hash, instances) in enumerate(grouped_instances.items()):
        all_instances_in_groups.update(instances)
        print(f"\nGroup {i + 1}:")
        for instance in sorted(instances):
            print(f"  - {instance}")

        cheapest, price = get_cheapest_instance(instances, all_prices_us_west_2)
        if cheapest and price is not None:
            price_sum += price
            final_instances.append(cheapest)
            print(f"  => Cheapest in us-west-2: {cheapest} (${price:.4f}/hour)")
        else:
            print("  => Could not determine the cheapest instance from the available price list.")
    print(f"Total Price: ${price_sum:.4f}/hour")
    print("Final Instances:", final_instances)

    for instance in sorted(list(all_instances_in_groups)):
        memory = all_memory_details.get(instance)
        if memory is not None and memory < 4:
            warnings.append(f"  - {instance}: {memory:.2f} GiB RAM")

    if warnings:
        print("\n--- Warnings: Low Memory Instances (< 4 GiB RAM) ---")
        for warning in warnings:
            print(warning)
        print("----------------------------------------------------")