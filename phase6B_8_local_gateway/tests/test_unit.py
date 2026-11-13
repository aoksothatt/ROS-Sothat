"""
Unit Tests for Local Mercury Gateway Prototype
Phase 6.2B.8 - Research & Prototype Only

Tests pure algorithmic units with independent golden vectors:
- Blowfish PBC Golden Vectors (1 to 4 blocks)
- Login Datagram Golden Vector & 32-bit XOR Checksum (0x7b76ba9e)
- Single-Byte Trailer Padding & Slack Invariance
- Bad Flags Detection (flags >= 0x0400)
- Framing Bounds & Malformed Packet Rejection
"""

import unittest
import struct
import sys
from pathlib import Path

# Add gateway package and phase6B_7_2 to sys.path
_PKG_DIR = str(Path(__file__).resolve().parent.parent)
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent.parent / "phase6B_7_2_synthetic_research")
for d in [_PKG_DIR, _PHASE6B_7_2_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config import GatewayConfig
from packet_parser import MercuryPacketFlags, MercuryPacketParser, PacketFramingError
from protocol_engine import (
    MercuryProtocolEngine,
    PacketDecryptionError,
    PaddingError,
    ChecksumError
)
from pbc_cipher import BlowfishPBC
from padding import SingleByteTrailerPadding
from checksum import MercuryChecksum


class TestMercuryUnitAlgorithms(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master_key = GatewayConfig.SYNTHETIC_MASTER_KEY
        cls.engine = MercuryProtocolEngine(cls.master_key)

    def test_01_independent_golden_pbc_single_block(self):
        """Verify Block 0 matches independent golden vector: ff734520b537c26c."""
        cipher = BlowfishPBC(self.master_key)
        pt = b"BLOCK_01"  # 8 bytes
        ct = cipher.encrypt(pt)
        self.assertEqual(ct.hex(), "ff734520b537c26c")
        self.assertEqual(cipher.decrypt(ct), pt)

    def test_02_independent_golden_pbc_multi_block(self):
        """Verify 2, 3, and 4 block PBC matches independent golden vectors."""
        cipher = BlowfishPBC(self.master_key)
        
        # 2 blocks
        pt2 = b"BLOCK_01BLOCK_02"
        ct2 = cipher.encrypt(pt2)
        expected_ct2 = "ff734520b537c26c22a8345f5fc8835c"
        self.assertEqual(ct2.hex(), expected_ct2)
        self.assertEqual(cipher.decrypt(ct2), pt2)

        # 3 blocks
        pt3 = b"BLOCK_01BLOCK_02BLOCK_03"
        ct3 = cipher.encrypt(pt3)
        expected_ct3 = "ff734520b537c26c22a8345f5fc8835c2564a0ba77df9656"
        self.assertEqual(ct3.hex(), expected_ct3)
        self.assertEqual(cipher.decrypt(ct3), pt3)

        # 4 blocks
        pt4 = b"BLOCK_01BLOCK_02BLOCK_03BLOCK_04"
        ct4 = cipher.encrypt(pt4)
        expected_ct4 = "ff734520b537c26c22a8345f5fc8835c2564a0ba77df9656fb1d277c80afcd87"
        self.assertEqual(ct4.hex(), expected_ct4)
        self.assertEqual(cipher.decrypt(ct4), pt4)

    def test_03_independent_golden_login_datagram_and_checksum(self):
        """Verify Login Request datagram golden checksum 0x7b76bada and ciphertext with corrected flags (0x01C0)."""
        payload = b'{"account":"test_user","token":"syn_token_123"}'  # 47 bytes
        flags = (
            MercuryPacketFlags.FLAG_HAS_CHECKSUM |
            MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
            MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER
        )
        self.assertEqual(flags, 0x01C0)

        # Assemble plaintext packet
        raw = MercuryPacketParser.pack(
            payload=payload,
            flags=flags,
            seq_num=1001,
            channel_id=1,
            with_checksum=True
        )
        self.assertEqual(len(raw), 61)

        # Compute checksum
        csum = MercuryChecksum.calculate(bytes(raw))
        self.assertEqual(csum, 0x7b76bada)
        MercuryChecksum.inject(raw)

        # Pad to multiple of 8 (64 bytes, 3 bytes padding ending in 0x03)
        padded = SingleByteTrailerPadding.pad(bytes(raw), slack_mode="zero")
        self.assertEqual(len(padded), 64)
        self.assertEqual(padded[-1], 0x03)

        # Encrypt with Blowfish PBC
        cipher = BlowfishPBC(self.master_key)
        ct = cipher.encrypt(padded)
        expected_hex = (
            "b7036a2c2f2da84561b21f7f1c52e9f6d145579be893d283d5cad5d289475c08"
            "ed1c1caaa342ecce31155d44b60ba67bc8519d3fbcf2c7df57d9371d16c659e8"
        )
        self.assertEqual(ct.hex(), expected_hex)

        # Decrypt through protocol engine
        unpacked = self.engine.receive_packet(ct)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["seq_num"], 1001)
        self.assertEqual(unpacked["channel_id"], 1)
        self.assertTrue(unpacked["checksum_verified"])
        self.assertEqual(unpacked["stored_checksum"], 0x7b76bada)

    def test_04_single_byte_trailer_padding_boundaries(self):
        """Verify pad length is always in [1, 8] and exact-block appends 8 bytes."""
        for length in range(0, 33):
            data = bytes([0x41] * length)
            padded = SingleByteTrailerPadding.pad(data, slack_mode="zero")
            self.assertEqual(len(padded) % 8, 0)
            pad_len = 8 - (length % 8)
            self.assertEqual(padded[-1], pad_len)
            unpadded = SingleByteTrailerPadding.unpad(padded)
            self.assertEqual(unpadded, data)

    def test_05_single_byte_trailer_slack_independence(self):
        """Verify receiver checks only trailer byte, ignoring slack bytes."""
        data = b"PAYLOAD_123"  # 11 bytes -> 5 bytes pad (4 slack + 1 trailer 0x05)
        zero_padded = SingleByteTrailerPadding.pad(data, slack_mode="zero")
        random_padded = SingleByteTrailerPadding.pad(data, slack_mode="random")
        pkcs7_padded = SingleByteTrailerPadding.pad(data, slack_mode="pkcs7")

        self.assertEqual(SingleByteTrailerPadding.unpad(zero_padded), data)
        self.assertEqual(SingleByteTrailerPadding.unpad(random_padded), data)
        self.assertEqual(SingleByteTrailerPadding.unpad(pkcs7_padded), data)

    def test_06_bad_flags_rejection(self):
        """Verify flags >= 0x0400 are strictly rejected as per native cmp w8, #0x400."""
        payload = b"TEST"
        for bad_flag in [0x0400, 0x0800, 0x1000, 0x4000, 0x8000, 0xFFFF]:
            bad_pkt = bytearray(struct.pack("<H", bad_flag)) + payload
            with self.assertRaises(PacketFramingError):
                MercuryPacketParser.unpack_footers(bad_pkt)

    def test_07_tampered_ciphertext_rejection(self):
        """Verify single bit flip in ciphertext causes decryption/checksum error."""
        datagram = self.engine.send_packet(b"TEST_MESSAGE", flags=0, enable_checksum=True)
        # Flip a bit in ciphertext
        tampered = bytearray(datagram)
        tampered[10] ^= 0x01
        with self.assertRaises((ChecksumError, PaddingError, PacketDecryptionError)):
            self.engine.receive_packet(bytes(tampered))

    def test_08_wrong_key_rejection(self):
        """Verify decrypting with a mismatched synthetic key fails."""
        datagram = self.engine.send_packet(b"CONFIDENTIAL_PAYLOAD", flags=0, enable_checksum=True)
        wrong_key = b"WRONG_SYNTHETIC_BLOWFISH_SESSION_KEY_0000000000000000000"
        self.assertEqual(len(wrong_key), 56)
        wrong_engine = MercuryProtocolEngine(wrong_key)
        with self.assertRaises((ChecksumError, PaddingError, PacketDecryptionError)):
            wrong_engine.receive_packet(datagram)

    def test_09_all_ten_individual_flags_isolation(self):
        """Verify each of the 10 native flags independently unpacks correctly."""
        # Bit 0: FLAG_HAS_REQUESTS = 0x0001
        p0 = MercuryPacketParser.pack(b"REQ", first_request_offset=42)
        u0 = MercuryPacketParser.unpack_footers(p0)
        self.assertEqual(u0["flags"], 0x0001)
        self.assertEqual(u0["first_request_offset"], 42)
        self.assertEqual(u0["payload"], b"REQ")

        # Bit 1: FLAG_HAS_PIGGYBACKS = 0x0002
        p1 = MercuryPacketParser.pack(b"PAY", piggyback=b"PIGGY")
        u1 = MercuryPacketParser.unpack_footers(p1)
        self.assertEqual(u1["flags"], 0x0002)
        self.assertEqual(u1["piggyback"], b"PIGGY")

        # Bit 2: FLAG_HAS_ACKS = 0x0004
        p2 = MercuryPacketParser.pack(b"PAY", acks=[100, 101])
        u2 = MercuryPacketParser.unpack_footers(p2)
        self.assertEqual(u2["flags"], 0x0004)
        self.assertEqual(u2["acks"], [100, 101])

        # Bit 3: FLAG_ON_CHANNEL = 0x0008
        p3 = MercuryPacketParser.pack(b"PAY", is_on_channel=True)
        u3 = MercuryPacketParser.unpack_footers(p3)
        self.assertEqual(u3["flags"], 0x0008)
        self.assertTrue(u3["is_on_channel"])

        # Bit 4: FLAG_IS_RELIABLE = 0x0010 (requires seq_num)
        p4 = MercuryPacketParser.pack(b"PAY", is_reliable=True, seq_num=500)
        u4 = MercuryPacketParser.unpack_footers(p4)
        self.assertEqual(u4["flags"], 0x0010 | 0x0040)
        self.assertTrue(u4["is_reliable"])
        self.assertEqual(u4["seq_num"], 500)

        # Bit 5: FLAG_HAS_FRAGMENTS = 0x0020
        p5 = MercuryPacketParser.pack(b"PAY", fragments=(0, 3))
        u5 = MercuryPacketParser.unpack_footers(p5)
        self.assertEqual(u5["flags"], 0x0020)
        self.assertEqual(u5["fragments"], (0, 3))

        # Bit 6: FLAG_HAS_SEQUENCE_NUMBER = 0x0040
        p6 = MercuryPacketParser.pack(b"PAY", seq_num=777)
        u6 = MercuryPacketParser.unpack_footers(p6)
        self.assertEqual(u6["flags"], 0x0040)
        self.assertEqual(u6["seq_num"], 777)

        # Bit 7: FLAG_INDEXED_CHANNEL = 0x0080
        p7 = MercuryPacketParser.pack(b"PAY", channel_id=99)
        u7 = MercuryPacketParser.unpack_footers(p7)
        self.assertEqual(u7["flags"], 0x0080)
        self.assertEqual(u7["channel_id"], 99)

        # Bit 8: FLAG_HAS_CHECKSUM = 0x0100
        p8 = MercuryPacketParser.pack(b"PAY", with_checksum=True)
        u8 = MercuryPacketParser.unpack_footers(p8)
        self.assertEqual(u8["flags"], 0x0100)
        self.assertTrue(u8["has_checksum"])

        # Bit 9: FLAG_CREATE_CHANNEL = 0x0200
        p9 = MercuryPacketParser.pack(b"PAY", is_create_channel=True)
        u9 = MercuryPacketParser.unpack_footers(p9)
        self.assertEqual(u9["flags"], 0x0200)
        self.assertTrue(u9["is_create_channel"])

    def test_10_reliable_flag_without_sequence_rejection(self):
        """Verify FLAG_IS_RELIABLE (0x0010) without seq_num is rejected per native 0x100923098."""
        bad_pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_IS_RELIABLE)) + b"PAYLOAD"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(bad_pkt)

    def test_11_fragment_range_validation(self):
        """Verify fragEnd < fragBegin raises PacketFramingError."""
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.pack(b"PAY", fragments=(5, 2))

        # Test malformed buffer with inverted range
        raw = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_FRAGMENTS)) + b"PAY"
        raw.extend(struct.pack("<II", 10, 5)) # begin=10, end=5
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(raw)

    def test_12_valid_flag_combinations_matrix(self):
        """Verify valid combinations seen in native disassembly."""
        combos = [
            (0x0100, {"with_checksum": True}),
            (0x0102, {"with_checksum": True, "piggyback": b"P"}),
            (0x0180, {"with_checksum": True, "channel_id": 1}),
            (0x03C0, {"is_create_channel": True, "channel_id": 1, "seq_num": 1, "with_checksum": True}),
            (0x0158, {"is_on_channel": True, "seq_num": 1, "is_reliable": True, "with_checksum": True}),
            (0x01D0, {"channel_id": 1, "seq_num": 1, "is_reliable": True, "with_checksum": True}),
            (0x01C4, {"channel_id": 1, "seq_num": 1, "acks": [10], "with_checksum": True}),
            (0x01CC, {"is_on_channel": True, "channel_id": 1, "seq_num": 1, "acks": [10], "with_checksum": True}),
            (0x01E0, {"channel_id": 1, "seq_num": 1, "fragments": (0, 2), "with_checksum": True}),
        ]
        for expected_flag, kwargs in combos:
            pkt = MercuryPacketParser.pack(b"TEST_PAYLOAD", **kwargs)
            unpacked = MercuryPacketParser.unpack_footers(pkt)
            self.assertEqual(unpacked["flags"], expected_flag, f"Failed for combo 0x{expected_flag:04x}")
            self.assertEqual(unpacked["payload"], b"TEST_PAYLOAD")

    def test_13_truncated_footers_rejection(self):
        """Verify truncated footers for all types raise PacketFramingError."""
        # 1. Truncated checksum (< 4 bytes)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM)) + b"P"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)

        # 2. Truncated piggyback (< 2 bytes length)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_PIGGYBACKS)) + b"P"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)

        # 3. Truncated channel_id (< 4 bytes)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_INDEXED_CHANNEL)) + b"P"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)

        # 4. Truncated acks count (< 1 byte)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_ACKS)) + b"P"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)

        # 5. ACK count 0 (forbidden)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_ACKS)) + b"P" + b"\x00"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)

        # 6. Truncated seq_num (< 4 bytes)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER)) + b"P"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)

        # 7. Truncated fragments (< 8 bytes)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_FRAGMENTS)) + b"P" + b"\x00\x00\x00\x00"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)

        # 8. Truncated request offset (< 2 bytes)
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_REQUESTS)) + b"P"
        with self.assertRaises(PacketFramingError):
            MercuryPacketParser.unpack_footers(pkt)


if __name__ == "__main__":
    unittest.main()
