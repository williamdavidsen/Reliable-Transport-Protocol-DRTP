# DATA2410 Reliable Transport Protocol (DRTP)

## About This Project

This project was written for the DATA2410 course to implement a reliable file transfer application over UDP.
A custom protocol, named DATA2410 Reliable Transport Protocol (DRTP) , was designed and coded to ensure reliable, ordered file transfer between two nodes (client and server) in Python.

TCP was not used for reliability. Instead, all reliability, connection management, and teardown mechanisms were implemented from scratch over UDP.
Therefore:

* Connections are established and closed with custom handshakes.
* Data is delivered reliably, in the correct order, and without duplication.
* Retransmissions, windowing, and all network errors are handled by the application code.

---

## Project Structure

The following structure was used in this project:


src/
  application.py    # The main function is located in application.py.
  client.py
  server.py
  filename_utils.py
  simple-topo.py  
my_inspera_id_documentation.pdf
|
README.md
  

* All implementation files are placed inside src/.
* This README and the project documentation PDF are located in the root folder.

---

## Requirements

* Python 3.13.3 used.
* Only the standard Python library was chosen (no external dependencies).
* The application was written for Linux (Mininet or similar), but can be run on any OS supporting UDP and Python.

---

## How to Use

* All commands must be executed inside the src/ directory.

### 1. Running the Server (Receiver)

First, the server must be started on the receiver node (e.g., Mininet host h2):


python3 application.py -s -i <server_ip> -p <port> [-d <seq_to_discard>]


Arguments:

* -s / --server: Activates server mode.
* -i / --ip : IP address to bind (default: 10.0.1.2).
* -p / --port : UDP port to listen on (default: 8088).
* -d / --discard : (Optional) Sequence number of the packet to discard for testing 

* Example:


python3 application.py -s -i 10.0.1.2 -p 8088


### 2. Running the Client (Sender)

The client is started from the sender node (e.g., Mininet host h1 ):


python3 application.py -c -f <file> -i <server_ip> -p <port> -w <window_size>


Arguments:

* -c / --client : Activates client mode.
* -f / --file : File to be sent (e.g., Photo.jpg).
* -i / --ip : IP address of the server.
* -p / --port : UDP port (must match server).
* -w / --window : (Optional) Sliding window size for Go-Back-N (used 3,5,10,15,20,25).

* Example:


python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8088 -w 5




## Protocol Description

* Chunk Size: Files are split into 992-byte chunks. Each packet is 1000 bytes (8-byte header + 992 bytes data).

* Custom Header: Each DRTP packet header contains a sequence number, acknowledgment number, flags (SYN, ACK, FIN), and receiver window size.

* Connection Setup: A three-way handshake (SYN, SYN-ACK, ACK) is used.

* Connection Teardown: A two-way handshake (FIN, FIN-ACK) is used.

* Reliability: Go-Back-N protocol was implemented for retransmission and sliding window. Default timeout is 400 ms.

* Testing Retransmission: The -d flag can be used on the server to drop a specific packet and force client retransmission.

* Unique Filenames: Incoming files are saved with a unique name using filename_utils.py . Existing files are never overwritten.

* Logging: Timestamped console output is produced for all major protocol events (sending, receiving, acks, etc.).

---

## Sample Output

* Server Output (h2):



SYN packet is received
SYN-ACK packet is sent
ACK packet is received
Connection established
21:20:58.675875 -- packet 1 is received
21:20:58.675940 -- sending ack for the received 1
...
Timeout while receiving data.
File saved as file.jpg
The throughput is 0.97 Mbps
Connection Closes
No SYN packet received, timing out and shutting down server.
  

* Client Output (h1):

Connection Establishment Phase:

SYN packet is sent
SYN-ACK packet is received
ACK packet is sent
Connection established

Data Transfer:

20:07:21.630782 -- packet with seq = 1 is sent, sliding window = [1]
ACK for packet = 1 is received
...
[-] FIN-ACK not received, retrying...
FIN packet is sent
[-] FIN-ACK not received, retrying...
[-] FIN-ACK not received after retries, closing anyway.
Connection Closes
  

---

## Tips, Troubleshooting, and Testing

* The server should always be started on h2 and the client on h1 in Mininet in Linux.
* If the server is not running, the client will timeout after sending the SYN packet.
* The -d flag is for retransmission tests; the client must retransmit any dropped packet.
* The -w flag allows window size changes to test throughput.
* Mininet or tc-netem may be used for advanced network simulation.

* Timeouts:
A 400 ms retransmission timeout was set.

* Defaults:
If no IP, port, or window size is specified, default values are used.

* Filenames:
The client always sends the file name at the beginning of the transfer.
The server saves incoming files with a received_ prefix, and creates a unique filename if needed.

---

## Testing & Evaluation

The following tests are recommended to demonstrate protocol reliability and performance:

1. Throughput vs. Window Size:

  * Test with window sizes of 3, 5, 10, 15, 20, 25 using the -w flag.
  * Measure throughput on both client and server.

2. Varying RTT (Network Delay):

  * Change RTT to 50 ms and 200 ms in simple-topo.py (The following line in simple-topo.py was changed: net["r"].cmd("tc qdisc add dev r-eth1 root netem delay 100ms")).

  * Repeat throughput tests for each RTT.

3. Packet Loss and Retransmission Test (-d flag):

  * Start the server with -d <seq_num> to drop a specific packet once.
  * Confirm that the client retransmits, and the protocol recovers.

4. Simulated Packet Loss (tc-netem):

  * Enable packet loss (e.g., loss 2% , loss 5% , loss 50% ).
  * Check that the file transfer completes and throughput is measured under loss.

5. FIN-ACK Loss Scenario:

  * After file transfer, simulate loss of the FIN-ACK (e.g., by disconnecting or dropping the packet).
  * Observe the client’s retransmission and protocol behavior.

Note: After all transmissions between the client and the server, the original and the received jpg files were verified to be identical using the md5sum command.





