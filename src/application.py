from server import server_start
from client import client_start

import argparse
import socket
import sys

# Protocol Flag Constants (should be consistent in all modules)
# FLAG_FIN: Signals a finish (connection teardown)
# FLAG_ACK: Acknowledgement flag for packet confirmation
# FLAG_SYN: Synchronize sequence numbers (used for connection setup)
FLAG_FIN = 1 << 0
FLAG_ACK = 1 << 1
FLAG_SYN = 1 << 2

def main():
    """
    Description:
        Main entry point for the DRTP reliable transport application.
        This function parses command-line arguments, validates them, and then starts
        the application in either client or server mode based on the provided arguments.

    Arguments:
        None (uses sys.argv implicitly via argparse).

    Use of other input and output parameters in the function:
        - Parses command-line arguments for mode, IP, port, file, window size, and discard index.
        - Validates user input for port range and IP address format.

    Returns:
        None. Calls sys.exit() with status 1 in case of invalid input.

    Exceptions:
        Prints an error and exits if:
            - Port number is not in the valid range [1024, 65535]
            - IP address is not in correct dotted decimal format
            - File is not specified in client mode
    """

    parser = argparse.ArgumentParser(
        description="DRTP - Reliable Transport Protocol over UDP"
    )
    # Mutually exclusive group to ensure only one mode is selected
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

    # Parse arguments from the command line
    args = parser.parse_args()

    # Validate port number
    if not (1024 <= args.port <= 65535):
        print("[-] Invalid port number: {}. Must be in range 1024-65535.".format(args.port))
        sys.exit(1)

    # Validate IP address format
    try:
        socket.inet_aton(args.ip)
    except OSError:
        print("[-] Invalid IP address: {}".format(args.ip))
        sys.exit(1)

    # Launch server or client mode based on arguments
    if args.server:
        # Start the server with specified IP, port, and discard value for debugging
        server_start(args.ip, args.port, args.discard)
    elif args.client:
        # In client mode, a file must be specified
        if not args.file:
            print("[-] You must specify a file using -f flag in client mode.")
            sys.exit(1)
        # Start the client with provided parameters
        client_start(args.ip, args.port, args.file, args.window)

if __name__ == "__main__":
    # Entry point for script execution
    main()
