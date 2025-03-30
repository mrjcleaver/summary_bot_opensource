#!/bin/bash

# Ensure Fly machines auto-bridge IPv6 → IPv4 for debugpy.
# This is necessary in IPV6 because debugpy does not support IPv6 and fly.io only supports IPV6.
# It's somewhat buggy though.


printenv | egrep 'ENV|FLY_MACHINE_ID|DEBUG|PYDEVD_DISABLE_FILE_VALIDATION'

# TODO explain PYDEVD_DISABLE_FILE_VALIDATION should be 1 if I'm debugging with an IDE.

apt-get update 

apt-get install -y net-tools iproute2;
apt-get install -y tcpdump
apt-get install -y 6tunnel
apt-get install -y netcat-openbsd


tcpdump -n port 5678
nc -l 6679


ss -tnlp # 5678 and 8080 should be open
echo 5678 is the port that the debugger listens on
echo 8080 is the port that the web server listens on   

