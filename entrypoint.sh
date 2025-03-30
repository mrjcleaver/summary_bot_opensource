#! /bin/bash

# Ensure Fly machines auto-bridge IPv6 → IPv4 for debugpy.

set -xv

rm -f 6tunnel.pid
if [ -n "$DEBUGPY_TUNNEL" ]; then
    echo    "DEBUGPY_TUNNEL is set, running 6tunnel to bridge IPv6 to IPv4 for debugpy."
    echo    "This is necessary in IPV6 because debugpy does not support IPv6 and fly.io only supports IPV6."

    # See https://github.com/microsoft/debugpy/issues/1252
    6tunnel -6 -l :: 5678 127.0.0.1 6679 -p 6tunnel.pid &
    export DEBUGPY_PORT=6679 #this will be used by debugpy instead of 5678 in debugpy.py
else
    echo    "DEBUGPY_TUNNEL is not set, skipping 6tunnel."  
fi


# Activate virtual environment
#source /app/.venv/bin/activate

env

# Run the application using the virtual environment (python is using venv's poetry)
# TODO  make frozen_modules dependent on the environment INSTALL_DEV using an external script 
python -Xfrozen_modules=off src/main.py
