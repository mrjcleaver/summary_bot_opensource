# This is imported by src/main.py only for debugging purposes. It is not used in production.
"""
Debug module for remote debugging capabilities using debugpy.

This module sets up remote debugging with debugpy and provides functionality
to monitor debugger connections. It's controlled via environment variables:
- DEBUGPY_SERVER: Host to listen on (default: localhost)
- DEBUGPY_PORT: Port to listen on (default: 5678)
- DEBUGPY_WAIT: If "true", waits for debugger to attach before proceeding
- DEBUGPY_LOG_DIR: Directory for debugpy logs"
"""

import debugpy # noqa
import os
import logging
import threading
import time

logging.info("🔍 Starting debug_app module")

if os.getenv("DEBUGPY_LOG_DIR"):
    try:
        logging.info(f"🪛 local debugpy log dir: {os.getenv('DEBUGPY_LOG_DIR')}")
    except:
        print(f"❌ DEBUGPY: Failed to set log dir: {os.getenv('DEBUGPY_LOG_DIR')}")

def watch_for_debugger_connects(poll_interval=1):
    def _watch():
        thread_name = threading.current_thread().name
        logging.info(f"🔍 [{thread_name}] Starting debugger watcher thread...")
        was_connected = False

        while True:
            is_connected = debugpy.is_client_connected()
            #logging.debug(f"🔍 [{thread_name}] Debugger client connected: {is_connected}")

            if is_connected and not was_connected:
                logging.info(f"🎯 [{thread_name}] Debugger client connected")
            elif not is_connected and was_connected:
                logging.warning(f"❌ [{thread_name}] Debugger client disconnected")

            was_connected = is_connected
            time.sleep(poll_interval)

    thread = threading.Thread(
        target=_watch,
        daemon=True,
        name="debugpy-connection-watcher"
    )
    thread.start()

port = int(os.getenv("DEBUGPY_PORT", 5678))
server = os.getenv("DEBUGPY_SERVER", "localhost")


try:   
    logging.info(f"🪛 debugpy about to listen on {server}:{port}")
    endpoint = debugpy.listen((server, port))
    logging.info(f"🪛 debugpy is listening on {server}:{port} - {endpoint}")
except Exception as e:
    print(f"❌ DEBUGPY: Failed to listen to {server}:{port}: {e}")
    logging.error(f"❌ DEBUGPY: Failed to listen: {e}")

watch_for_debugger_connects()

if os.getenv("DEBUGPY_WAIT") == "true":
    logging.info("🪛 debugpy enabled, now waiting_for_client")
    debugpy.wait_for_client()  # noqa # NEVER BREAKPOINT HERE
    debugpy.breakpoint()

    logging.info("🪛 client attached")
    logging.info("Breakpoint should hit here")  # ⛔ Set breakpoint here

