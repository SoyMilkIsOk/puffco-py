"""
Unit tests for Lorax packet framing and SHA-256 challenge-response authentication.
"""

import hashlib
import unittest

from puffco_py.constants import (
    LORAX_MASTER_HANDSHAKE_KEY,
    LORAX_OP_GET_ACCESS_SEED,
    LORAX_OP_READ_SHORT,
    LORAX_OP_UNLOCK_ACCESS,
    LORAX_OP_WRITE_SHORT,
)
from puffco_py.protocol import (
    calculate_lorax_auth_token,
    pack_lorax_cmd,
    pack_lorax_read_short,
    pack_lorax_write_short,
    unpack_lorax_reply,
)


class TestProtocol(unittest.TestCase):
    def test_lorax_auth_token_calculation(self):
        """Verify SHA-256 token matches SHA256(MasterKey + Seed[0:16])[0:16]."""
        dummy_seed = bytes([i for i in range(16)])
        expected_hash = hashlib.sha256(LORAX_MASTER_HANDSHAKE_KEY + dummy_seed).digest()[:16]

        token = calculate_lorax_auth_token(dummy_seed)
        self.assertEqual(token, expected_hash)
        self.assertEqual(len(token), 16)

    def test_lorax_auth_seed_too_short(self):
        """Verify error raised if seed is less than 16 bytes."""
        short_seed = b"\x01\x02\x03"
        with self.assertRaises(ValueError):
            calculate_lorax_auth_token(short_seed)

    def test_pack_lorax_cmd(self):
        """Verify packet header serialization: [seq: uint16 LE, opcode: uint8]."""
        pkt = pack_lorax_cmd(seq=1, opcode=LORAX_OP_GET_ACCESS_SEED)
        self.assertEqual(len(pkt), 3)
        self.assertEqual(pkt[0], 0x01)
        self.assertEqual(pkt[1], 0x00)
        self.assertEqual(pkt[2], LORAX_OP_GET_ACCESS_SEED)

        # Test sequence wrapping
        pkt_wrapped = pack_lorax_cmd(seq=0x1234, opcode=LORAX_OP_UNLOCK_ACCESS, payload=b"\xaa\xbb")
        self.assertEqual(pkt_wrapped[0], 0x34)
        self.assertEqual(pkt_wrapped[1], 0x12)
        self.assertEqual(pkt_wrapped[2], LORAX_OP_UNLOCK_ACCESS)
        self.assertEqual(pkt_wrapped[3:], b"\xaa\xbb")

    def test_unpack_lorax_reply(self):
        """Verify unpack of reply notification."""
        raw_reply = bytes([0x05, 0x00, 0x00, 0xDE, 0xAD, 0xBE, 0xEF])
        seq, status, payload = unpack_lorax_reply(raw_reply)

        self.assertEqual(seq, 5)
        self.assertEqual(status, 0)
        self.assertEqual(payload, b"\xDE\xAD\xBE\xEF")

    def test_pack_read_and_write_short(self):
        """Verify packing of short VFS paths."""
        read_payload = pack_lorax_read_short("/p/app/htr/temp", max_len=64)
        self.assertTrue(read_payload.endswith(b"/p/app/htr/temp"))

        write_payload = pack_lorax_write_short("/p/app/mc", bytes([0x07]))
        self.assertTrue(b"/p/app/mc\x00\x07" in write_payload)


if __name__ == "__main__":
    unittest.main()
