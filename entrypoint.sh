#! /bin/bash

# Ensure Fly machines auto-bridge IPv6 → IPv4 for debugpy.

rm -f 6tunnel.pid
if [ ! -z "$DEBUGPY_ENABLE" ]; then
    echo    "DEBUGPY_ENABLE is set, running 6tunnel to bridge IPv6 to IPv4 for debugpy."
    echo    "This is necessary because debugpy does not support IPv6."

    # See https://github.com/microsoft/debugpy/issues/1252
    6tunnel -6 -l :: 5678 127.0.0.1 6679 -p 6tunnel.pid &
else
    echo    "DEBUGPY_ENABLE is not set, skipping 6tunnel."  
fi

# Run the application using the virtual environment (python is using venv's poetry)
# TODO  make frozen_modules dependent on the environment INSTALL_DEV using an external script 
python -Xfrozen_modules=off src/main.py
