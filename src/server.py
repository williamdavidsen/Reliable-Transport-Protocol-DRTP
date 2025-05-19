import socket
import struct
import sys
import time
from datetime import datetime

from filename_utils import get_unique_filename

# Protocol Flag Constants (must match those used by client and application)
FLAG_FIN = 1 << 0  # FIN flag: signals connection teardown
FLAG_ACK = 1 << 1  # ACK flag: acknowledgment for packets
FLAG_SYN = 1 << 2  # SYN flag: for connection establishment
FLAG_RST = 1 << 3  # RST flag: reset, not commonly used

def server_start(ip, port, discard_seq):
    """
    Description:
        Starts the DRTP server to receive files reliably from clients via UDP.
        Handles the three-way handshake (SYN, SYN-ACK, ACK) to establish a connection,
        then enters the data reception and file writing phases, and finally manages
        connection teardown via a FIN-ACK handshake. Optionally discards a specified packet
        (by sequence number) for testing reliability.

    Arguments:
        ip (str): The IP address to bind the server socket (e.g., '10.0.1.2').
        port (int): UDP port to listen on (1024-65535).
        discard_seq (int): If not 999999, the server will discard the packet with this sequence number (for testing).

    Use of other input and output parameters in the function:
        - server_socket: UDP socket used for communication.
        - addr: Client address tuple.
        - All flags and packet structures must match the protocol definition.

    Returns:
        None. Exits or breaks on fatal error or timeout.

    Exceptions:
        - Handles all socket creation, binding, sendto/recvfrom, and struct unpacking errors.
        - Exits or prints errors for all known failure cases.
    """

    try:
        # Create and bind the UDP server socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((ip, port))
    except socket.error as e:
        print("[-] Failed to create or bind socket: {}".format(e))
        sys.exit(1)

    discarded = False         # Whether the test discard has been performed
    total_bytes_received = 0  # For transfer stats
    start_time = None         # For timing throughput

    try:
        while True:
            server_socket.settimeout(5)
            try:
                # Wait for the initial SYN packet to establish connection
                data, addr = server_socket.recvfrom(1024)
            except socket.timeout:
                print("No SYN packet received, timing out and shutting down server.")
                break
            except socket.error as e:
                print("[-] Socket error during recvfrom: {}".format(e))
                break

            # Parse protocol header (sequence, acknowledgment, flags, window)
            seq, ack, flags, win = struct.unpack('!HHHH', data[:8])

            if flags & FLAG_SYN:
                print("SYN packet is received")
                syn_ack_flags = FLAG_SYN | FLAG_ACK
                # Send SYN-ACK to client
                response = struct.pack('!HHHH', 0, seq + 1, syn_ack_flags, 15)
                try:
                    server_socket.sendto(response, addr)
                except socket.error as e:
                    print("[-] Socket error during sendto: {}".format(e))
                    break
                print("SYN-ACK packet is sent")

                # Wait for final ACK from client to complete handshake
                try:
                    data, addr = server_socket.recvfrom(1024)
                except socket.timeout:
                    print("[-] Timeout waiting for ACK after SYN-ACK.")
                    break
                except socket.error as e:
                    print("[-] Socket error during recvfrom: {}".format(e))
                    break

                seq, ack, flags, win = struct.unpack('!HHHH', data[:8])
            if flags & FLAG_ACK:
                print("ACK packet is received")
                print("Connection established")

                expected_seq = 1     # Next expected sequence number from client
                f = None             # File object for writing received data
                start_time = time.time()  # Record transfer start time

                # --- Main Data Reception Loop ---
                while True:
                    try:
                        server_socket.settimeout(0.4)  # Short timeout for retransmissions
                        try:
                            # Wait for next data packet from client
                            packet, addr = server_socket.recvfrom(1500)
                        except socket.timeout:
                            print("Timeout while receiving data.")
                            break  # End of data transfer on timeout
                        except socket.error as e:
                            print("[-] Socket error during recvfrom: {}".format(e))
                            break
                        if not packet:
                            break  # End of file or stream

                        header = packet[:8]
                        seq, ack, flags, win = struct.unpack('!HHHH', header)
                        data = packet[8:]

                        # Discard packet with specified sequence for testing (once)
                        if discard_seq == seq and not discarded:
                            print(f"Discarding packet seq {seq} for testing")
                            discarded = True
                            continue

                        # Accept and write the packet only if its sequence matches expectation
                        if seq == expected_seq:
                            if expected_seq == 1:
                                # The first packet contains the filename and the start of the data
                                filename_len = packet[8]
                                filename = packet[9:9+filename_len].decode()
                                data = packet[9+filename_len:]
                                new_filename = "received_" + filename
                                # Ensure file does not overwrite existing file
                                new_filename = get_unique_filename(new_filename)
                                try:
                                    f = open(new_filename, 'wb')
                                except PermissionError:
                                    print("[-] Permission denied while creating {}.".format(new_filename))
                                    break
                                except Exception as e:
                                    print("[-] Error while creating file: {}".format(e))
                                    break
                            else:
                                # For all packets except the first, data is the payload after header
                                data = packet[8:]
                            if data:
                                try:
                                    # Write received data to file
                                    f.write(data)
                                    total_bytes_received += len(data)
                                except Exception as e:
                                    print("[-] Error while writing to file: {}".format(e))
                                    break
                                # Log successful packet reception with timestamp
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")
                                print(f"{timestamp} -- packet {seq} is received")
                                # Prepare and send ACK for received packet
                                ack_header = struct.pack('!HHHH', 0, seq, FLAG_ACK, 0)
                                try:
                                    server_socket.sendto(ack_header, addr)
                                except socket.error as e:
                                    print("[-] Socket error during sendto: {}".format(e))
                                    break
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")
                                print(f"{timestamp} -- sending ack for the received {seq}")
                                expected_seq += 1
                            else:
                                # If an out-of-order packet is received, log and ignore
                                print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- out-of-order packet {seq} is received")
                                continue

                            # If FIN flag is present, begin teardown handshake
                            if flags & FLAG_FIN:
                                print("FIN packet is received")
                                fin_ack_flags = FLAG_ACK | FLAG_FIN
                                fin_ack = struct.pack('!HHHH', 0, seq + 1, fin_ack_flags, 0)
                                try:
                                    server_socket.sendto(fin_ack, addr)
                                except socket.error as e:
                                    print("[-] Socket error during sendto: {}".format(e))
                                print("FIN ACK packet is sent")
                                print("Connection Closes")
                                break

                    except Exception as e:
                        print("[-] Unexpected error during data transfer: {}".format(e))
                        break

            # After transfer loop, clean up file and print statistics
            if f:
                try:
                    f.close()
                except Exception as e:
                    print("[-] Error while closing file: {}".format(e))
                end_time = time.time()
                elapsed = end_time - start_time
                throughput_mbps = (total_bytes_received * 8) / (
                    elapsed * 1_000_000
                )
                print(f"File saved as {filename}")
                print(f"The throughput is {throughput_mbps:.2f} Mbps")
                print("Connection Closes")
                
    except KeyboardInterrupt:
        print("[-] Server shutting down...")
    finally:
        # Always close the server socket to free resources
        try:
            server_socket.close()
        except Exception as e:
            print("[-] Error while closing socket: {}".format(e))
