#! /usr/local/bin/python
"""
# connections.py - A script to inspect TCP connections for 6tunnel tunneling between IPv4 and IPv6 for debugpy.
#
# This script checks the TCP connections for debugpy and 6tunnel, interpreting their states and logging the results.
# It is designed to be run on a Linux system with access to the /proc/net/tcp and /proc/net/tcp6 files.
# The script requires root privileges to access these files.
#
# Usage:    python connections.py
#           python connections.py --port_v4 6679 --port_v6 5678 
#           python connections.py --port_v4 5678 --port_v6 5678
# """


import logging
import socket
import sys
import os

logging.basicConfig(level=logging.INFO)

logging.info(f"Python executable: {sys.executable}")
logging.info(f"sys.path: {sys.path}")


def hex_to_ip(hex_ip):
    bytes_ip = [int(hex_ip[i:i + 2], 16) for i in (6, 4, 2, 0)]
    return ".".join(map(str, bytes_ip))


def hex_to_ipv6(hex_ip):
    return socket.inet_ntop(socket.AF_INET6, bytes.fromhex(hex_ip))


def hex_to_port(hex_port):
    return int(hex_port, 16)


def decode_tcp_state(state_hex):
    tcp_states = {
        '01': 'ESTABLISHED',
        '02': 'SYN_SENT',
        '03': 'SYN_RECV',
        '04': 'FIN_WAIT1',
        '05': 'FIN_WAIT2',
        '06': 'TIME_WAIT',
        '07': 'CLOSE',
        '08': 'CLOSE_WAIT',
        '09': 'LAST_ACK',
        '0A': 'LISTEN',
        '0B': 'CLOSING'
    }
    return tcp_states.get(state_hex.upper(), f"UNKNOWN ({state_hex})")


def parse_tcp_file(path, hex_port, is_ipv6=False):
    found = {
        'LISTEN': False,
        'ESTABLISHED': 0,
        'CLOSE_WAIT': 0,
        'other': []
    }

    with open(path) as f:
        next(f)  # Skip header
        for line in f:
            cols = line.strip().split()
            local_address, remote_address, state = cols[1], cols[2], cols[3]
            local_ip_hex, local_port_hex = local_address.split(':')

            if local_port_hex.upper() == hex_port:
                remote_ip_hex, remote_port_hex = remote_address.split(':')
                local_ip = hex_to_ipv6(local_ip_hex) if is_ipv6 else hex_to_ip(local_ip_hex)
                remote_ip = hex_to_ipv6(remote_ip_hex) if is_ipv6 else hex_to_ip(remote_ip_hex)
                remote_port = hex_to_port(remote_port_hex)
                state_desc = decode_tcp_state(state)

                if state_desc == 'LISTEN':
                    found['LISTEN'] = True
                elif state_desc == 'ESTABLISHED':
                    found['ESTABLISHED'] += 1
                elif state_desc == 'CLOSE_WAIT':
                    found['CLOSE_WAIT'] += 1
                else:
                    found['other'].append(state_desc)

                logging.info(f"🔗 {state_desc}: {remote_ip}:{remote_port} → {local_ip}:{hex_to_port(hex_port)}")

    return found


def interpret_connections(port_v4=6679, port_v6=5678):
    logging.info("🔍 Inspecting debugpy/6tunnel connection status")

    hex_v4 = f"{int(port_v4):04X}"
    hex_v6 = f"{int(port_v6):04X}"

    logging.info(f"🌐 Checking IPv4 (/proc/net/tcp) for port {port_v4} (hex {hex_v4})")
    result_v4 = parse_tcp_file("/proc/net/tcp", hex_v4, is_ipv6=False)

    logging.info(f"🌐 Checking IPv6 (/proc/net/tcp6) for port {port_v6} (hex {hex_v6})")
    result_v6 = parse_tcp_file("/proc/net/tcp6", hex_v6, is_ipv6=True)

    # Interpretation logic
    if result_v4['LISTEN']:
        logging.info(f"✅ debugpy is listening on 127.0.0.1 (port {port_v4})")
    else:
        logging.warning("❌ debugpy is NOT listening on 127.0.0.1")

    if result_v6['LISTEN']:
        logging.info(f"✅ 6tunnel is listening on [::] (port {port_v6})")
    else:
        logging.warning(f"❌ 6tunnel is NOT listening on port {port_v6} (check tunnel setup)")

    if result_v6['ESTABLISHED'] >= 1:
        logging.info("🎯 VS Code (or another client) is CONNECTED via IPv6 tunnel ✅")
    else:
        logging.warning(f"⚠️ No active client connection detected via IPv6 (port {port_v6})")

    if result_v4['ESTABLISHED'] >= 1:
        logging.info("🧠 debugpy has an ACTIVE debugger session!")
    else:
        logging.warning(f"⚠️ debugpy is waiting for a debugger (no ESTABLISHED connection on port {port_v4})")


# Run it

if __name__ == "__main__":
    logging.info("🔍 Starting connection interpreter")
    # Check if the script is run with root privileges
    if os.geteuid() != 0:
        logging.error("❌ This script must be run as root to access /proc/net/tcp and /proc/net/tcp6")
        sys.exit(1)

    # Call the function to interpret connections
    logging.info(os.environ.get("DEBUGPY_PORT"))
    # interpret_connections(port_v4=6679, port_v6=5678)

    logging.info("\nChecking for normal debugpy connections")
    interpret_connections(port_v4=5678, port_v6=5678)

#    logging.info("\nChecking for 6tunnel-based IPV6 to IPV4 tunneled connections")
#    interpret_connections(port_v4=6679, port_v6=5678)
