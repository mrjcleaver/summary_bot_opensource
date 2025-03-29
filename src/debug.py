# This is imported by src/main.py only for debugging purposes. It is not used in production.
import debugpy # noqa
import os
import logging
import threading
import time

import os
os.environ["DEBUGPY_LOG_DIR"] = "/tmp"

if os.getenv("DEBUGPY_LOG_DIR"):
    logging.info(f"🪛 local debugpy log dir: {os.getenv('DEBUGPY_LOG_DIR')}")

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

if True:
    if os.getenv("DEBUGPY_WAIT") == "true":
        logging.info("🪛 debugpy enabled, now waiting_for_client")
        debugpy.wait_for_client()  # noqa # NEVER BREAKPOINT HERE
        debugpy.breakpoint()

        logging.info("🪛 client attached")
        logging.info("Breakpoint should hit here")  # ⛔ Set breakpoint here

#if os.getenv("DEBUGPY_WAIT") == "true":
#    logging.info("🪛 debugpy enabled, now waiting_for_client")
#    debugpy.wait_for_client()  # noqa
