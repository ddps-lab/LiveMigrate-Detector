#!/bin/bash

/home/ubuntu/get_cpuid/main

wait

aws s3 cp /home/ubuntu/get_cpuid/cpuid.csv s3://us-west-2-cpuid-x86/$(curl http://169.254.169.254/latest/meta-data/instance-type).csv

wait

sudo shutdown -h now
