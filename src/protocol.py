import struct


HEADER_FORMAT = "!HHHH"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PAYLOAD_SIZE = 1000 - HEADER_SIZE
MAX_FILENAME_SIZE = 255

DEFAULT_SERVER_WINDOW = 15
RETRANSMISSION_TIMEOUT = 0.4
HANDSHAKE_TIMEOUT = 2
SERVER_IDLE_TIMEOUT = 5

FLAG_FIN = 1 << 0
FLAG_ACK = 1 << 1
FLAG_SYN = 1 << 2
FLAG_RST = 1 << 3


def pack_header(seq=0, ack=0, flags=0, window=0):
    """Pack a DRTP header into network byte order."""
    return struct.pack(HEADER_FORMAT, seq, ack, flags, window)


def unpack_header(packet):
    """Return sequence, ack, flags, and window fields from a packet."""
    return struct.unpack(HEADER_FORMAT, packet[:HEADER_SIZE])


def has_flags(flags, expected):
    """Check whether all expected flags are set."""
    return (flags & expected) == expected
