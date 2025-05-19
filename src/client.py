import socket
import struct
import sys
from datetime import datetime

# Protocol Flag Constants (must match server and application)
FLAG_FIN = 1 << 0  # FIN flag: indicates connection teardown
FLAG_ACK = 1 << 1  # ACK flag: indicates acknowledgment
FLAG_SYN = 1 << 2  # SYN flag: indicates connection establishment (synchronization)
FLAG_RST = 1 << 3  # RST flag: indicates connection reset (not always used)

def client_start(ip, port, filename, window_size):
    """
    Description:
        Initiates and manages a DRTP client to send a file reliably over UDP.
        Handles connection establishment (three-way handshake), data transfer using
        sliding window protocol, and file reading.
    Arguments:
        ip (str): IP address of the server in dotted decimal notation (e.g., '10.0.1.2').
        port (int): UDP port number for the server (1024-65535).
        filename (str): Path to the file to send.
        window_size (int): Sliding window size for Go-Back-N protocol.
    Use of other input and output parameters in the function:
        - server_addr: Tuple of (ip, port) for the server.
        - client_socket: The UDP socket for communication.
        - All flags and packet structures must match those expected by the server.
    Returns:
        None. Exits with sys.exit() on fatal error.
    Exceptions:
        - Handles socket creation, sendto/recvfrom, file opening, and struct errors.
        - Exits and prints user-friendly error messages for all known failure cases.
    """

    # Attempt to create a UDP socket for the client
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as e:
        print("[-] Failed to create socket: {}".format(e))
        sys.exit(1)
    server_addr = (ip, port)

    print("Connection Establishment Phase:\n")

    # --- Three-way handshake: Send SYN, wait for SYN-ACK, send ACK ---
    try:
        syn_flags = FLAG_SYN
        # Pack SYN packet header (all fields are zero except flags)
        syn_packet = struct.pack('!HHHH', 0, 0, syn_flags, 0)
        try:
            # Send SYN packet to server
            client_socket.sendto(syn_packet, server_addr)
        except socket.error as e:
            print("[-] Socket error during sendto: {}".format(e))
            sys.exit(1)
        print("SYN packet is sent")

        client_socket.settimeout(2)
        try:
            # Wait for SYN-ACK response from server
            data, addr = client_socket.recvfrom(1024)
        except socket.timeout:
            print("[-] Connection failed: Timeout (waiting for SYN-ACK)")
            sys.exit(1)
        except socket.error as e:
            print("[-] Socket error during recvfrom: {}".format(e))
            sys.exit(1)
        # Unpack the header of the received SYN-ACK
        seq, ack, flags, win = struct.unpack('!HHHH', data[:8])

        if (flags & FLAG_SYN) and (flags & FLAG_ACK):
            print("SYN-ACK packet is received")
            ack_flags = FLAG_ACK
            # Send final ACK to complete handshake
            ack_packet = struct.pack('!HHHH', 0, seq + 1, ack_flags, win)
            try:
                client_socket.sendto(ack_packet, server_addr)
            except socket.error as e:
                print("[-] Socket error during sendto: {}".format(e))
                sys.exit(1)
            print("ACK packet is sent")
            print("Connection established")

            print("\nData Transfer:\n")

            # --- Attempt to open file for reading in binary mode ---
            try:
                f = open(filename, 'rb')
            except FileNotFoundError:
                print("[-] File {} not found.".format(filename))
                sys.exit(1)
            except PermissionError:
                print("[-] Permission denied while opening {}.".format(filename))
                sys.exit(1)
            except Exception as e:
                print("[-] Unexpected error while opening {}: {}".format(filename, e))
                sys.exit(1)

            # Initialize sequence variables for Go-Back-N sliding window protocol
            sequence_number = 1        # Sequence number for packets (starts at 1)
            client_window = window_size # Client window size (from CLI)
            server_window = win         # Server window size (received from SYN-ACK)
            sender_window = min(client_window, server_window) # Effective window
            base = 1                   # Base of the sliding window (oldest unacknowledged packet)
            next_seq = 1               # Next sequence number to send
            packets = []               # List to store prepared data packets

            # Prepare the first packet (filename transfer packet)
            filename_bytes = filename.encode()
            filename_len = len(filename_bytes)
            if filename_len > 255:
                print("[-] Filename too long!")
                sys.exit(1)

            # Read data for the first packet, leaving space for filename info
            data = f.read(992 - (1 + filename_len))
            header = struct.pack('!HHHH', 1, 0, 0, 0)
            # First packet format: [header][filename length][filename][data]
            first_packet = header + bytes([filename_len]) + filename_bytes + data
            packets.append(first_packet)
            
            # Prepare and append the rest of the data packets to the list
            next_seq = 2
            while True:
                # Read up to 992 bytes for each packet (to fit UDP payload)
                data = f.read(992)
                if not data:
                    break  # End of file
                header = struct.pack('!HHHH', next_seq, 0, 0, 0)
                packet = header + data
                packets.append(packet)
                next_seq += 1

            # Initialize sequence tracking for Go-Back-N
            next_seq = 1
            total_packets = len(packets)
            client_socket.settimeout(0.4)  # Short timeout for retransmissions

            # Main Go-Back-N transmission loop
            while base <= total_packets:
                next_seq = base
                # Send all packets in the current window
                while next_seq < base + sender_window and next_seq <= total_packets:
                    try:
                        client_socket.sendto(packets[next_seq - 1], server_addr)
                    except socket.error as e:
                        print("[-] Socket error during sendto: {}".format(e))
                        sys.exit(1)
                    # Print information about the sliding window and packet
                    current_window = list(range(base, next_seq + 1))
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")
                    print(f"{timestamp} -- packet with seq = {next_seq} is sent, sliding window = {current_window}")
                    next_seq += 1
                try:
                    # Wait for ACK from server
                    ack_packet, _ = client_socket.recvfrom(1500)
                except socket.timeout:
                    print("Timeout, resending window...")
                    next_seq = base + sender_window
                    continue  # Retransmit the window after timeout
                except socket.error as e:
                    print("[-] Socket error during recvfrom: {}".format(e))
                    sys.exit(1)
                # Unpack ACK packet header
                ack_header = ack_packet[:8]
                seq, ack, flags, win = struct.unpack('!HHHH', ack_header)
                if flags & FLAG_ACK:
                    print(f"ACK for packet = {ack} is received")
                    base = ack + 1  # Slide window base forward on valid ACK

            # --- Connection teardown phase using FIN-ACK handshake ---
            fin_flags = FLAG_FIN
            fin_packet = struct.pack('!HHHH', 0, 0, fin_flags, 0)
            retries = 5
            fin_ack_received = False

            # Retry sending FIN packet up to 5 times if necessary
            for attempt in range(retries):
                try:
                    client_socket.sendto(fin_packet, server_addr)
                except socket.error as e:
                    print("[-] Socket error during sendto: {}".format(e))
                    continue
                print("FIN packet is sent")
                try:
                    # Wait for FIN-ACK from server
                    fin_ack_packet, _ = client_socket.recvfrom(1024)
                    seq, ack, flags, win = struct.unpack('!HHHH', fin_ack_packet[:8])
                    if (flags & FLAG_FIN) and (flags & FLAG_ACK):
                        print("FIN ACK packet is received")
                        print("Connection Closes")
                        fin_ack_received = True
                        break
                except socket.timeout:
                    print("[-] FIN-ACK not received, retrying...")
                except socket.error as e:
                    print("[-] Socket error during recvfrom: {}".format(e))
                    continue

            if not fin_ack_received:
                print("[-] FIN-ACK not received after retries, closing anyway.")
                print("Connection Closes")

    except socket.timeout:
        print("[-] Connection failed: Timeout")
        sys.exit(1)
    except Exception as e:
        print("[-] Unexpected error in client_start: {}".format(e))
        sys.exit(1)
    finally:
        # Ensure the client socket is closed properly
        try:
            client_socket.close()
        except Exception as e:
            print("[-] Error while closing socket: {}".format(e))


            