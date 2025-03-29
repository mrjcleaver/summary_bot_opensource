import os
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")

def find_debugpy_logs(log_dir="/tmp"):
    log_dir = Path(log_dir)
    pattern = re.compile(r"debugpy\.(adapter|launcher)-.*\.log")
    return [f for f in log_dir.iterdir() if f.is_file() and pattern.match(f.name)]

def highlight_headers(lines):
    header_lines = []
    capturing = False

    for line in lines:
        if b'GET / HTTP/1.1' in line or b'Host:' in line or b'User-Agent:' in line:
            capturing = True
        if capturing:
            if line.strip() == b'':
                break
            header_lines.append(line.decode(errors='replace').strip())

    return header_lines

def summarize_log_file(filepath, max_tail=20):
    logging.info(f"\n📄 Analyzing: {filepath.name}")
    try:
        with open(filepath, "rb") as f:
            lines = f.readlines()
    except Exception as e:
        logging.error(f"❌ Failed to read {filepath}: {e}")
        return

    if not lines:
        logging.info("⚠️ Empty log file.")
        return

    log_text = b''.join(lines).decode(errors='replace')

    # Highlight common events
    if "Client[" in log_text:
        connect_count = log_text.count("Accepted incoming Client connection")
        disconnect_count = log_text.count("has disconnected")

        logging.info(f"🔌 Client connections: {connect_count}")
        logging.info(f"🔌 Client disconnections: {disconnect_count}")

    if "Content-Length is missing" in log_text:
        logging.warning("🚨 Missing Content-Length (likely browser hit or bad attach)")

    if "GET / HTTP/1.1" in log_text:
        logging.warning("🌐 Looks like an HTTP request hit debugpy (maybe a browser?)")

        # Show headers
        headers = highlight_headers(lines)
        if headers:
            logging.info("\n📬 HTTP-like client headers:")
            for line in headers:
                logging.info("  " + line)

    # Show tail
    logging.info(f"\n🔚 Last {max_tail} lines:")
    for line in lines[-max_tail:]:
        logging.info("  " + line.decode(errors='replace').strip())

def main():
    logging.info("🔍 Scanning for debugpy logs in /tmp...\n")
    log_files = find_debugpy_logs("/tmp")

    if not log_files:
        logging.warning("⚠️ No debugpy log files found in /tmp.")
        return

    for log_file in sorted(log_files):
        summarize_log_file(log_file)

if __name__ == "__main__":
    main()
