# Testing

Tests were run with local loopback and Mininet.

<img src="screenshots/retransmission-test.png" alt="DRTP retransmission test" width="100%">

## Quick Local Test

Start the server:

```bash
python3 application.py -s -i 127.0.0.1 -p 8088 --verbose
```

Start the client in another terminal:

```bash
python3 application.py -c -f iceland-safiqul.jpg -i 127.0.0.1 -p 8088 -w 5 --verbose
```

## Reliability Test

The server can intentionally drop one packet:

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

Expected result: the client times out, retransmits the active Go-Back-N window, and completes the transfer.

After data delivery, the client prints packet count, send attempts, retransmission events, window size, and duration.

## Network Experiments

The Mininet topology is useful for:

- Different RTT values, such as `50 ms`, `100 ms`, and `200 ms`
- Random packet loss with `tc netem`
- Different sliding window sizes
- Throughput changes under delay and packet loss

Start the topology from `src/`:

```bash
sudo python3 simple-topo.py
```

The default topology applies `100ms` delay on the router-to-server link. Edit `LINK_DELAY` or `PACKET_LOSS` in `simple-topo.py` to run other scenarios.

## Integrity Check

After a transfer, compare the original file with the received file:

```bash
md5sum iceland-safiqul.jpg received_iceland-safiqul.jpg
```

Matching hashes confirm that the received file is identical to the original.
