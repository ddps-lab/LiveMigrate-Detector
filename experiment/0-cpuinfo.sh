#!/bin/bash
cd /home/ubuntu/LiveMigrate-Detector
git pull

cd /home/ubuntu/result
sudo criu cpuinfo dump

cd /home/ubuntu/LiveMigrate-Detector/cpu_feature_collector/
./collector > /home/ubuntu/result/isaset.csv

sudo chown -R ubuntu:ubuntu /home/ubuntu/result