#!/bin/bash

# 프로세스 실행 명령어
/home/ubuntu/get_cpuid/main

# 프로세스 실행이 완료될 때까지 대기
wait

# 프로세스 실행이 완료되면 시스템 셧다운
sudo shutdown -h now