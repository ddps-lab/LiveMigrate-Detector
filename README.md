# Workload-Aware Live Migratable Cloud Instance Detector

### A project to extract the CPU features used in a workload to achieve migration compatibility.

computing provides a variety of distinct computing resources on demand. Supporting live migration in the cloud can be beneficial to dynamically build a reliable and cost-optimal environment, especially when using spot instances. Users can apply the process of live migration technology using the Checkpoint/Restore In Userspace (CRIU) to achieve the goal. Due to the nature of live migration, ensuring the compatibility of the central processing unit (CPU) features between the source and target hosts is crucial for flawsless execution after migration. To detect migratable instances precisely while lowering falsenegative detection on the cloud-scale, we propose a workloadaware migratable instance detector. Unlike the implementation of the CRIU compatibility checking algorithm, which audits the source and target host CPU features, the proposed system thoroughly investigates instructions used in a migrating process to consider CPU features that are actually in use. With a thorough evaluation under various workloads, we demonstrate that the proposed system improves the recall of migratable instance detection over 5× compared to the default CRIU implementation with 100% detection accuracy. To demonstrate its practicability, we apply it to the spot-instance environment, revealing that it can improve the median cost savings by 16% and the interruption ratio by 15% for quarter cases.

## CPU Feature Collector

Various instance types, even a few hundred with unique CPU features, are offered by public cloud service providers. The CPU feature collector module gathers CPU features of unique instance types off-line to make a prompt decision about migratable instance types. In systems with X86 architecture, CPU features can be extracted using the CPUID instruction. 

## Workload Instruction Analyzer

The proposed system analyzes the operations of a workload with respect to the CPU features that the workload needs in a new host. To extract the CPU features, we propose two methods: the text-segment full scan and execution path tracking. These methods analyze the text section of the process memory, which contains all instructions and function calls from an executable binary file and the shared libraries that might be executed during the program runtime. For the extracted operations, the system applies the Intel X86 Encoder Decoder (XED), which can encode and decode details of X86 instructions, to identify the mapping of an instruction to a CPU feature.

The text-segment full scan method analyzes all executable code loaded into a process, which can lead to significant overhead and produce inaccurate inspection results. There is a concern of unnecessary inspection overhead and the extraction of unused CPU features because there is no guarantee that all code from loaded libraries will be executed.

On the other hand, execution path tracking traces branching instructions such as call and jmp. Therefore, it includes only code that is likely to be actually executed, ensuring low overhead and very high accuracy. **We recommend this method.**

In Python, the source code is not loaded into the process memory as executable instructions, making it impossible to perform accurate compatibility checks using Execution Path Tracking. Bytecode Tracking is **recommended for Python workloads**, as it traces the native functions invoked by the intermediate representation (bytecode) interpreted and executed by the Python Virtual Machine. It then collects the CPU features used by these native functions to ensure accurate compatibility checks.

### Mandatory requirements

Unlike lazy binding, the now binding approach resolves the addresses of all external symbols at the beginning. With now binding, execution path tracking can trace all function addresses even at the beginning of program execution, enabling tracking at any point during the process runtime. Due to the limited function address identification of lazy binding, **the current system supports the now binding approach.**

You can easily enable now binding by setting environment variables as follows and running the process: ```export LD_BIND_NOW=1```

### Dependencies

[GNU Debugger (GDB)](https://www.sourceware.org/gdb/)  
[Intel® X86 Encoder Decoder (Intel® XED)](https://github.com/intelxed/xed)

## Compatibility Checker

The compatibility checker module determines the compatibility of the source and destination hosts based on the CPU features of a process extracted from the workload instruction analyzer and the CPU feature collector. Compatibility checking is conducted by comparing whether the CPU features used in the migrating workload on the source hosts are present on the destination host. Although this evaluation method is similar to the default CRIU implementation, it focuses on the CPU features that a target workload uses.

## Reproducing the Experiments

All experiment procedures are conducted within the `experiment` folder. If you encounter issues with Spot Instances during any step, you can disable them by setting `USE_SPOT` to `false` in `main.go`.

**Step 1: AWS CLI Setup** Install and log in to the AWS CLI.

**Step 2: Create a Base AMI** Navigate to the EC2 console and create a `t2.medium` instance (or any instance with at least 4GB RAM) using an Ubuntu 22.04 image. Ensure it has ample storage (approx. 140GB). Copy and execute the contents of `experiment/0-ami.sh` on the instance to set it up. After setup, create an AMI from this configured instance. Finally, update the `AMI_ID` variable in `experiment/main.go` with your new AMI ID.

**Step 3: Collect and Group CPU Information** First, create an `instance.txt` file and populate it with all target AWS instance types. Run `go run main.go 0-cpuinfo.sh` to collect the CPU data. Afterward, group the instances using `0-cpuinfo-group.py` and update `instance.txt` with the representative instance from each group. For validation, rename the `experiment/result/0-cpuinfo` folder to `0-cpuinfo-all`, and re-run `go run main.go 0-cpuinfo.sh`. You can then verify the collection with `0-cpuinfo-all-check.py`.

**Step 4: Collect Workload Instruction Data** Execute `go run main.go 1-collect-info.sh` to run the workloads and dump the process information for various methods (CRIU, Pygration). You can validate the process using `1-collect-info-validate.py`.

**Step 5: Upload Results to S3** Compress the results folder (`experiment/result/1-collect-info`) using a command like `tar --no-xattr -c 1-collect-info | zstd -5 > 1-collect-info.tar.zst`. Upload the compressed archive to an S3 bucket. Ensure the uploaded file has public read access, as the experiment scripts download it using the `--no-sign-request` flag. Finally, update the S3 path in `experiment/2-compatibility-check.sh` accordingly.

**Step 6: Run Compatibility Check** Run `go run main.go 2-compatibility-check.sh` to collect the final compatibility results. You can analyze and verify these results using `2-experiment-analysis.py`.

---

If you are interested in our pre-collected results without running the full experiment pipeline, you can find them in the compressed archive: [Download Link](https://example.com).