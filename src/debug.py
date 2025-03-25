# This is imported by src/main.py only for debugging purposes. It is not used in production.
import debugpy # noqa
import os

debugpy.listen(("0.0.0.0", 5678))
print("🪛 debugpy listening on port 5678...")

if os.getenv("DEBUGPY_WAIT") == "true":
    print("🪛 debugpy enabled, now waiting_for_client")
    debugpy.wait_for_client()  # noqa
