import os
import socket
import sys
import time
from datetime import datetime

from protocol import (
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    HANDSHAKE_TIMEOUT,
    HEADER_SIZE,
    MAX_FILENAME_SIZE,
    PAYLOAD_SIZE,
    RETRANSMISSION_TIMEOUT,
    has_flags,
    pack_header,
    unpack_header,
)

def client_start(ip, port, filename, window_size, verbose=False):
    """Send a file reliably over UDP using DRTP and Go-Back-N."""

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error as e:
        print("[-] Failed to create socket: {}".format(e))
        sys.exit(1)
    server_addr = (ip, port)

    print("Connection Establishment Phase:\n")

    # Three-way handshake: SYN, SYN-ACK, ACK.
    try:
        syn_packet = pack_header(flags=FLAG_SYN)
        try:
            client_socket.sendto(syn_packet, server_addr)
        except socket.error as e:
            print("[-] Socket error during sendto: {}".format(e))
            sys.exit(1)
        print("SYN packet is sent")

        client_socket.settimeout(HANDSHAKE_TIMEOUT)
        try:
            # Wait for SYN-ACK response from server
            data, addr = client_socket.recvfrom(1024)
        except socket.timeout:
            print("[-] Connection failed: Timeout (waiting for SYN-ACK)")
            sys.exit(1)
        except socket.error as e:
            print("[-] Socket error during recvfrom: {}".format(e))
            sys.exit(1)
        seq, ack, flags, win = unpack_header(data)

        if has_flags(flags, FLAG_SYN | FLAG_ACK):
            print("SYN-ACK packet is received")
            ack_packet = pack_header(ack=seq + 1, flags=FLAG_ACK, window=win)
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
            client_window = window_size # Client window size (from CLI)
            server_window = win         # Server window size (received from SYN-ACK)
            sender_window = min(client_window, server_window) # Effective window
            base = 1                   # Base of the sliding window (oldest unacknowledged packet)
            next_seq = 1               # Next sequence number to send
            packets = []               # List to store prepared data packets

            # Prepare the first packet (filename transfer packet)
            filename_bytes = filename.encode()
            filename_len = len(filename_bytes)
            if filename_len > MAX_FILENAME_SIZE:
                print("[-] Filename too long!")
                sys.exit(1)

            # Read data for the first packet, leaving space for filename info
            data = f.read(PAYLOAD_SIZE - (1 + filename_len))
            header = pack_header(seq=1)
            # First packet format: [header][filename length][filename][data]
            first_packet = header + bytes([filename_len]) + filename_bytes + data
            packets.append(first_packet)
            
            # Prepare and append the rest of the data packets to the list
            next_seq = 2
            while True:
                # Read up to 992 bytes for each packet (to fit UDP payload)
                data = f.read(PAYLOAD_SIZE)
                if not data:
                    break  # End of file
                header = pack_header(seq=next_seq)
                packet = header + data
                packets.append(packet)
                next_seq += 1
            f.close()

            # Initialize sequence tracking for Go-Back-N
            next_seq = 1
            total_packets = len(packets)
            total_bytes = os.path.getsize(filename)
            packets_sent = 0
            retransmission_events = 0
            transfer_start = time.time()
            client_socket.settimeout(RETRANSMISSION_TIMEOUT)

            # Main Go-Back-N transmission loop
            while base <= total_packets:
                # Send all packets in the current window
                while next_seq < base + sender_window and next_seq <= total_packets:
                    try:
                        client_socket.sendto(packets[next_seq - 1], server_addr)
                    except socket.error as e:
                        print("[-] Socket error during sendto: {}".format(e))
                        sys.exit(1)
                    packets_sent += 1
                    # Print information about the sliding window and packet
                    if verbose:
                        current_window = list(range(base, next_seq + 1))
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")
                        print(f"{timestamp} -- packet with seq = {next_seq} is sent, sliding window = {current_window}")
                    next_seq += 1
                try:
                    # Wait for ACK from server
                    ack_packet, _ = client_socket.recvfrom(1500)
                except socket.timeout:
                    print("Timeout, resending window...")
                    retransmission_events += 1
                    next_seq = base
                    continue  # Retransmit the window after timeout
                except socket.error as e:
                    print("[-] Socket error during recvfrom: {}".format(e))
                    sys.exit(1)
                # Unpack ACK packet header
                seq, ack, flags, win = unpack_header(ack_packet)
                if flags & FLAG_ACK:
                    if verbose:
                        print(f"ACK for packet = {ack} is received")
                    base = ack + 1  # Slide window base forward on valid ACK

            transfer_duration = time.time() - transfer_start
            print("\nTransfer Summary:")
            print(f"File size: {total_bytes} bytes")
            print(f"Total packets: {total_packets}")
            print(f"Packet send attempts: {packets_sent}")
            print(f"Retransmission events: {retransmission_events}")
            print(f"Window size: {sender_window}")
            print(f"Duration: {transfer_duration:.2f}s")

            # --- Connection teardown phase using FIN-ACK handshake ---
            fin_packet = pack_header(flags=FLAG_FIN)
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
                    seq, ack, flags, win = unpack_header(fin_ack_packet)
                    if has_flags(flags, FLAG_FIN | FLAG_ACK):
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


            
