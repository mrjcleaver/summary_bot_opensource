# This is imported by src/main.py only for debugging purposes. It is not used in production.
import debugpy # noqa
import os
import logging

debugpy.listen(("0.0.0.0", 5678))
logging.info("🪛 debugpy listening on port 5678...")
debugpy.wait_for_client()  # noqa
print("Breakpoint should hit here")  # ⛔ Set breakpoint here


if os.getenv("DEBUGPY_WAIT") == "true":
    logging.info("🪛 debugpy enabled, now waiting_for_client")
    debugpy.wait_for_client()  # noqa
