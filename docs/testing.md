# Testing

The project was tested with both local loopback runs and Mininet network simulations.

<img src="screenshots/retransmission-test.png" alt="DRTP retransmission test" width="100%">

## Quick Local Test

Start the server:

```bash
python3 application.py -s -i 127.0.0.1 -p 8088
```

Start the client in another terminal:

```bash
python3 application.py -c -f iceland-safiqul.jpg -i 127.0.0.1 -p 8088 -w 5
```

## Reliability Test

The server can intentionally drop one packet to verify retransmission behavior:

```bash
python3 application.py -s -i 10.0.1.2 -p 8088 -d 5
```

The server can also write to a selected output filename:

```bash
python3 application.py -s -i 10.0.1.2 -p 8088 -o received.jpg
```

Use `--verbose` when checking packet-level behavior:

```bash
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8088 -w 5 --verbose
```

Then run the client:

```bash
python3 application.py -c -f iceland-safiqul.jpg -i 10.0.1.2 -p 8088 -w 5
```

The expected behavior is that the client times out, retransmits the active Go-Back-N window, and completes the file transfer.

The client prints a transfer summary after data delivery, including packet count, send attempts, retransmission events, window size, and duration.

## Network Experiments

The Mininet topology can be used to test:

- Different RTT values, such as `50 ms`, `100 ms`, and `200 ms`
- Random packet loss with `tc netem`
- Different sliding window sizes
- Throughput changes under delay and packet loss

## Integrity Check

After a transfer, compare the original file with the received file:

```bash
md5sum iceland-safiqul.jpg received_iceland-safiqul.jpg
```

Matching hashes confirm that the file was transferred without corruption.
