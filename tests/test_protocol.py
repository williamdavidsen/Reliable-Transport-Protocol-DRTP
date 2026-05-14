import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol import (  # noqa: E402
    FLAG_ACK,
    FLAG_SYN,
    HEADER_SIZE,
    PAYLOAD_SIZE,
    has_flags,
    pack_header,
    unpack_header,
)


class ProtocolHeaderTests(unittest.TestCase):
    def test_pack_and_unpack_header(self):
        packet = pack_header(seq=7, ack=6, flags=FLAG_SYN | FLAG_ACK, window=15)

        self.assertEqual(len(packet), HEADER_SIZE)
        self.assertEqual(unpack_header(packet), (7, 6, FLAG_SYN | FLAG_ACK, 15))

    def test_has_flags_requires_all_expected_bits(self):
        flags = FLAG_SYN | FLAG_ACK

        self.assertTrue(has_flags(flags, FLAG_SYN))
        self.assertTrue(has_flags(flags, FLAG_SYN | FLAG_ACK))
        self.assertFalse(has_flags(FLAG_SYN, FLAG_SYN | FLAG_ACK))

    def test_payload_size_matches_packet_layout(self):
        self.assertEqual(HEADER_SIZE + PAYLOAD_SIZE, 1000)


if __name__ == "__main__":
    unittest.main()
