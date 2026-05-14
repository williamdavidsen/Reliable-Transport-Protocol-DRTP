import socket
import sys
import time
from datetime import datetime

from filename_utils import get_unique_filename
from protocol import (
    DEFAULT_SERVER_WINDOW,
    FLAG_ACK,
    FLAG_FIN,
    FLAG_SYN,
    HEADER_SIZE,
    RETRANSMISSION_TIMEOUT,
    SERVER_IDLE_TIMEOUT,
    pack_header,
    unpack_header,
)


def send_ack(server_socket, addr, ack):
    server_socket.sendto(pack_header(ack=ack, flags=FLAG_ACK), addr)


def send_fin_ack(server_socket, addr, seq):
    server_socket.sendto(pack_header(ack=seq + 1, flags=FLAG_ACK | FLAG_FIN), addr)


def parse_first_packet(packet):
    filename_len = packet[HEADER_SIZE]
    filename_start = HEADER_SIZE + 1
    filename_end = filename_start + filename_len
    filename = packet[filename_start:filename_end].decode()
    data = packet[filename_end:]
    return filename, data


def server_start(ip, port, discard_seq, output_filename=None, verbose=False):
    """Receive a file reliably over UDP using DRTP."""

    try:
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
            server_socket.settimeout(SERVER_IDLE_TIMEOUT)
            try:
                data, addr = server_socket.recvfrom(1024)
            except socket.timeout:
                print("No SYN packet received, timing out and shutting down server.")
                break
            except socket.error as e:
                print("[-] Socket error during recvfrom: {}".format(e))
                break

            seq, ack, flags, win = unpack_header(data)

            if flags & FLAG_SYN:
                print("SYN packet is received")
                response = pack_header(ack=seq + 1, flags=FLAG_SYN | FLAG_ACK, window=DEFAULT_SERVER_WINDOW)
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

                seq, ack, flags, win = unpack_header(data)
            if flags & FLAG_ACK:
                print("ACK packet is received")
                print("Connection established")

                expected_seq = 1     # Next expected sequence number from client
                f = None             # File object for writing received data
                saved_filename = None
                total_bytes_received = 0
                start_time = time.time()  # Record transfer start time
                last_activity = start_time

                while True:
                    try:
                        server_socket.settimeout(RETRANSMISSION_TIMEOUT)
                        try:
                            # Wait for next data packet from client
                            packet, addr = server_socket.recvfrom(1500)
                        except socket.timeout:
                            if time.time() - last_activity > SERVER_IDLE_TIMEOUT:
                                print("Timeout while receiving data.")
                                break
                            continue
                        except socket.error as e:
                            print("[-] Socket error during recvfrom: {}".format(e))
                            break
                        if not packet:
                            break  # End of file or stream
                        last_activity = time.time()

                        seq, ack, flags, win = unpack_header(packet)
                        data = packet[HEADER_SIZE:]

                        if flags & FLAG_FIN:
                            print("FIN packet is received")
                            try:
                                send_fin_ack(server_socket, addr, seq)
                            except socket.error as e:
                                print("[-] Socket error during sendto: {}".format(e))
                            print("FIN ACK packet is sent")
                            break

                        # Discard packet with specified sequence for testing (once)
                        if discard_seq == seq and not discarded:
                            print(f"Discarding packet seq {seq} for testing")
                            discarded = True
                            continue

                        # Accept and write the packet only if its sequence matches expectation
                        if seq == expected_seq:
                            if expected_seq == 1:
                                filename, data = parse_first_packet(packet)
                                new_filename = output_filename or "received_" + filename
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
                                saved_filename = new_filename
                            else:
                                # For all packets except the first, data is the payload after header
                                data = packet[HEADER_SIZE:]
                            if data:
                                try:
                                    # Write received data to file
                                    f.write(data)
                                    total_bytes_received += len(data)
                                except Exception as e:
                                    print("[-] Error while writing to file: {}".format(e))
                                    break
                                # Log successful packet reception with timestamp
                                if verbose:
                                    timestamp = datetime.now().strftime("%H:%M:%S.%f")
                                    print(f"{timestamp} -- packet {seq} is received")
                                # Prepare and send ACK for received packet
                                try:
                                    send_ack(server_socket, addr, seq)
                                except socket.error as e:
                                    print("[-] Socket error during sendto: {}".format(e))
                                    break
                                if verbose:
                                    timestamp = datetime.now().strftime("%H:%M:%S.%f")
                                    print(f"{timestamp} -- sending ack for the received {seq}")
                                expected_seq += 1
                            else:
                                if verbose:
                                    print(f"{datetime.now().strftime('%H:%M:%S.%f')} -- out-of-order packet {seq} is received")
                        else:
                            try:
                                send_ack(server_socket, addr, expected_seq - 1)
                            except socket.error as e:
                                print("[-] Socket error during sendto: {}".format(e))
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
                print(f"File saved as {saved_filename}")
                print(f"The throughput is {throughput_mbps:.2f} Mbps")
                print("Connection Closes")
                f = None
                
    except KeyboardInterrupt:
        print("[-] Server shutting down...")
    finally:
        # Always close the server socket to free resources
        try:
            server_socket.close()
        except Exception as e:
            print("[-] Error while closing socket: {}".format(e))
