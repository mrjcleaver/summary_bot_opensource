# This is imported by src/main.py only for debugging purposes. It is not used in production.
import debugpy # noqa
import os
import logging


try:
    endpoint = debugpy.listen(("127.0.0.1", 6679))
    logging.info(f"🪛 debugpy listening on {endpoint}")
except Exception as e:
    print(f"❌ DEBUGPY: Failed to listen: {e}")
    logging.error(f"❌ DEBUGPY: Failed to listen: {e}")

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
