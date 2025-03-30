#!/bin/bash
# This script is used if you want to manually set up a 6tunnel to bridge IPv6 to IPv4 for debugpy.


apt-get update && apt-get install -y 6tunnel
6tunnel -6 -l :: 5678 127.0.0.1 5678
