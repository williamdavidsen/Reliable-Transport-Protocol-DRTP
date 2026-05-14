from server import server_start
from client import client_start

import argparse
import socket
import sys

# Protocol flags shared by the client and server.
FLAG_FIN = 1 << 0
FLAG_ACK = 1 << 1
FLAG_SYN = 1 << 2

def main():
    """Parse CLI arguments and start DRTP in client or server mode."""

    parser = argparse.ArgumentParser(
        description="DRTP - Reliable Transport Protocol over UDP"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-s", "--server", action="store_true", help="Run in server mode")
    group.add_argument("-c", "--client", action="store_true", help="Run in client mode")
    parser.add_argument("-i", "--ip", type=str, default="10.0.1.2",
                        help="IP address of server (dotted decimal notation, e.g. 10.0.1.2)")
    parser.add_argument("-p", "--port", type=int, default=8088,
                        help="Port number (integer in the range [1024, 65535])")
    parser.add_argument("-f", "--file", type=str,
                        help="File to transfer (required in client mode only)")
    parser.add_argument("-w", "--window", type=int, default=3,
                        help="Sliding window size (default: 3)")
    parser.add_argument("-d", "--discard", type=int, default=999999,
                        help="Packet to discard (for server test/debugging reliability)")

    args = parser.parse_args()

    if not (1024 <= args.port <= 65535):
        print("[-] Invalid port number: {}. Must be in range 1024-65535.".format(args.port))
        sys.exit(1)

    try:
        socket.inet_aton(args.ip)
    except OSError:
        print("[-] Invalid IP address: {}".format(args.ip))
        sys.exit(1)

    if args.server:
        server_start(args.ip, args.port, args.discard)
    elif args.client:
        if not args.file:
            print("[-] You must specify a file using -f flag in client mode.")
            sys.exit(1)
        client_start(args.ip, args.port, args.file, args.window)

if __name__ == "__main__":
    main()
