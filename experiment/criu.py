import sys
import argparse
import cpuinfo_pb2

# Convert the x86_ins_capability_mask array from the C code to a Python list.
# This mask defines the essential instruction set-related CPU features required for migration.
# Index values (CPUID_*)
CPUID_1_EDX          = 0
CPUID_8000_0001_EDX  = 1
CPUID_LNX_1          = 2
CPUID_1_ECX          = 3
CPUID_8000_0001_ECX  = 4
CPUID_7_0_EBX        = 5
CPUID_D_1_EAX        = 6
CPUID_7_0_ECX        = 7
CPUID_8000_0008_EBX  = 8
CPUID_7_0_EDX        = 9
NCAPINTS = 12 # Set array size to match NCAPINTS_V2 from the C code.

# Directly ported values from the x86_ins_capability_mask in the C code.
x86_ins_capability_mask = [0] * NCAPINTS
x86_ins_capability_mask[CPUID_1_EDX] = 0x178bfbff
x86_ins_capability_mask[CPUID_8000_0001_EDX] = 0x2c100800
x86_ins_capability_mask[CPUID_LNX_1] = 0x0000000a
x86_ins_capability_mask[CPUID_1_ECX] = 0x9e982201
x86_ins_capability_mask[CPUID_8000_0001_ECX] = 0x0000179b
x86_ins_capability_mask[CPUID_7_0_EBX] = 0x1ed8c6a9
x86_ins_capability_mask[CPUID_D_1_EAX] = 0x0000000e
x86_ins_capability_mask[CPUID_7_0_ECX] = 0x00027f6e
x86_ins_capability_mask[CPUID_8000_0008_EBX] = 0x00000001
x86_ins_capability_mask[CPUID_7_0_EDX] = 0x0000000c


def parse_cpuinfo(img_path: str) -> cpuinfo_pb2.cpuinfo_x86_entry:
    """
    Parses a cpuinfo.img file and returns a cpuinfo_x86_entry protobuf message.
    """
    try:
        with open(img_path, 'rb') as f:
            # Skip MAGIC (8 bytes) + MSG_SIZE (4 bytes) = 12 bytes
            f.seek(12)
            proto_data = f.read()

        # First, parse the main container message (cpuinfo_entry).
        cpu_info = cpuinfo_pb2.cpuinfo_entry()
        cpu_info.ParseFromString(proto_data)

        # Check that there is exactly one x86_entry, same as the C code logic.
        if len(cpu_info.x86_entry) != 1:
            raise ValueError(f"File '{img_path}' contains {len(cpu_info.x86_entry)} x86_entry messages (expected 1).")

        # Return the first x86_entry, which contains the actual CPU info.
        return cpu_info.x86_entry[0]

    except FileNotFoundError:
        print(f"Error: File '{img_path}' not found.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: Failed to parse '{img_path}': {e}", file=sys.stderr)
        return None


def check_migration(src: cpuinfo_pb2.cpuinfo_x86_entry, dst: cpuinfo_pb2.cpuinfo_x86_entry) -> list:
    """
    Compares source and destination CPU information to check for migration compatibility.
    Follows the logic from the C function cpu_validate_features.
    """
    errors = []

    # 1. Check XSAVE related features (FPU capabilities)
    # The destination's (dst) xfeatures_mask must include all bits from the source's (src).
    # In other words, there should be no bits set in src that are not set in dst.
    if (src.xfeatures_mask & ~dst.xfeatures_mask) != 0:
        missing_bits = src.xfeatures_mask & ~dst.xfeatures_mask
        errors.append(f"XSAVE feature mismatch: Destination CPU is missing required xfeatures bits (0x{missing_bits:x}).")

    # The XSAVE area size must match exactly.
    if src.xsave_size != dst.xsave_size:
        errors.append(f"XSAVE size mismatch: src({src.xsave_size}) != dst({dst.xsave_size})")

    if src.xsave_size_max != dst.xsave_size_max:
        errors.append(f"Max XSAVE size mismatch: src({src.xsave_size_max}) != dst({dst.xsave_size_max})")

    # 2. Check instruction set related features (Instruction capabilities)
    # Same logic as the cpu_validate_ins_features function in the C code.
    # First, check the length of the capability array.
    if len(src.capability) > len(dst.capability):
        errors.append(f"CPU capability array length mismatch: src({len(src.capability)}) > dst({len(dst.capability)})")
    else:
        # Only compare up to the common length.
        common_len = min(len(src.capability), len(x86_ins_capability_mask))
        for i in range(common_len):
            # Apply the mask to compare only the essential instruction set features.
            src_masked = src.capability[i] & x86_ins_capability_mask[i]
            dst_masked = dst.capability[i] & x86_ins_capability_mask[i]

            # If a feature required by the source is missing in the destination.
            if (src_masked & ~dst_masked) != 0:
                missing_bits = src_masked & ~dst_masked
                errors.append(f"Instruction set mismatch: Destination CPU is missing required bits in capability[{i}] (0x{missing_bits:x}).")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Compares two cpuinfo.img files to check for migration compatibility.")
    parser.add_argument("src_cpuinfo_img", help="Path to the source system's cpuinfo.img file")
    parser.add_argument("dst_cpuinfo_img", help="Path to the destination system's cpuinfo.img file")
    args = parser.parse_args()

    print(f"[*] Parsing source CPU info from: {args.src_cpuinfo_img}")
    src_info = parse_cpuinfo(args.src_cpuinfo_img)
    if not src_info:
        sys.exit(1)

    print(f"[*] Parsing destination CPU info from: {args.dst_cpuinfo_img}")
    dst_info = parse_cpuinfo(args.dst_cpuinfo_img)
    if not dst_info:
        sys.exit(1)

    print("\n[!] Starting migration compatibility check...")
    
    # Print model information
    print(f"  - Source CPU Model: {src_info.model_id.strip() if src_info.model_id else 'N/A'}")
    print(f"  - Destination CPU Model: {dst_info.model_id.strip() if dst_info.model_id else 'N/A'}")
    print("-" * 40)

    errors = check_migration(src_info, dst_info)

    if not errors:
        print("\n[Result] ✅ Migration is possible.")
    else:
        print("\n[Result] ❌ Migration is not possible. Reasons:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()