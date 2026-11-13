"""
Independent Verification and Audit Closure Test Suite
Phase 6.2B.8.5 - Controlled Implementation & Verification

CRITICAL AUDIT ASSURANCE:
- This module implements independent reconstruction of Blowfish PBC, Single-Byte Trailer Padding,
  and 32-bit SIMD XOR Checksum using pure Python struct and raw cryptography Blowfish ECB.
- It verifies Vectors A, B, C, D against static, independently calculated golden hex values.
- It verifies complete bit-for-bit agreement between independent calculations and gateway modules.
- It does NOT rely on gateway implementation internals for golden truth derivation.
"""

import unittest
import struct
import sys
from pathlib import Path

# Pure independent cryptographic primitive via standard library and cryptography package
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish

# Add gateway package to sys.path for cross-verification
_PKG_DIR = str(Path(__file__).resolve().parent.parent)
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent.parent / "phase6B_7_2_synthetic_research")
for d in [_PKG_DIR, _PHASE6B_7_2_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config import GatewayConfig
from protocol_engine import MercuryProtocolEngine
from packet_parser import MercuryPacketFlags, MercuryPacketParser


# ==============================================================================
# Independent Reference Implementations (Decoupled from Gateway Modules)
# ==============================================================================

def independent_pbc_encrypt(key: bytes, plaintext: bytes) -> bytes:
    """
    Independent reference implementation of Blowfish Plaintext Block Chaining:
    C_0 = E(P_0 ^ 0)
    C_i = E(P_i ^ P_{i-1})
    """
    assert len(plaintext) % 8 == 0
    cipher = Cipher(Blowfish(key), modes.ECB())
    encryptor = cipher.encryptor()
    ciphertext = bytearray()
    prev_pt = None
    for offset in range(0, len(plaintext), 8):
        block = plaintext[offset : offset + 8]
        xored = block if prev_pt is None else bytes(a ^ b for a, b in zip(block, prev_pt))
        c_block = encryptor.update(xored)
        ciphertext.extend(c_block)
        prev_pt = block
    return bytes(ciphertext)


def independent_pbc_decrypt(key: bytes, ciphertext: bytes) -> bytes:
    """
    Independent reference implementation of Blowfish PBC Decryption:
    P_0 = D(C_0) ^ 0
    P_i = D(C_i) ^ P_{i-1}
    """
    assert len(ciphertext) % 8 == 0
    cipher = Cipher(Blowfish(key), modes.ECB())
    decryptor = cipher.decryptor()
    plaintext = bytearray()
    prev_pt = None
    for offset in range(0, len(ciphertext), 8):
        c_block = ciphertext[offset : offset + 8]
        raw_dec = decryptor.update(c_block)
        pt_block = raw_dec if prev_pt is None else bytes(a ^ b for a, b in zip(raw_dec, prev_pt))
        plaintext.extend(pt_block)
        prev_pt = pt_block
    return bytes(plaintext)


def independent_xor_checksum(raw_packet: bytes, csum_offset: int) -> int:
    """
    Independent reference implementation of 32-bit SIMD XOR Checksum:
    Zeroes 4-byte checksum field in-place, pads to 4-byte boundary, computes XOR reduction.
    """
    buf = bytearray(raw_packet)
    struct.pack_into("<I", buf, csum_offset, 0)
    pad = (4 - (len(buf) % 4)) % 4
    buf.extend(bytes(pad))
    csum = 0
    for offset in range(0, len(buf), 4):
        dword = struct.unpack_from("<I", buf, offset)[0]
        csum ^= dword
    return csum & 0xFFFFFFFF


def independent_pad(raw_bytes: bytes) -> bytes:
    """
    Independent reference implementation of Single-Byte Trailer Wastage Padding:
    Trailer byte L = 8 - (len & 7) placed at buf[-1], zero slack bytes.
    """
    rem = len(raw_bytes) % 8
    pad_len = 8 - rem
    return raw_bytes + bytes(pad_len - 1) + bytes([pad_len])


def independent_unpad(padded: bytes) -> bytes:
    assert len(padded) % 8 == 0
    pad_len = padded[-1]
    assert 1 <= pad_len <= 8
    return padded[:-pad_len]


# ==============================================================================
# Independent Verification Suite
# ==============================================================================

class TestIndependentVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.master_key = GatewayConfig.SYNTHETIC_MASTER_KEY
        cls.engine = MercuryProtocolEngine(cls.master_key)

    def test_01_vector_a_independent_verification(self):
        """
        Verify Vector A (Login Request):
        - Flags: 0x01C0 (FLAG_HAS_CHECKSUM | FLAG_INDEXED_CHANNEL | FLAG_HAS_SEQUENCE_NUMBER)
        - Payload: b'{"account":"test_user","token":"syn_token_123"}' (47 bytes)
        - SeqNum: 1001, ChannelID: 1
        """
        payload = b'{"account":"test_user","token":"syn_token_123"}'
        flags = 0x01C0
        seq_num = 1001
        channel_id = 1

        # 1. Independent Assembly (Forward order: SeqNum 4B, ChannelID 4B, Checksum 4B)
        footers = bytearray()
        footers.extend(struct.pack("<I", seq_num))
        footers.extend(struct.pack("<I", channel_id))
        footers.extend(b"\x00\x00\x00\x00") # checksum placeholder

        raw = bytearray(struct.pack("<H", flags)) + payload + footers
        self.assertEqual(len(raw), 61)

        # 2. Independent Checksum
        csum = independent_xor_checksum(bytes(raw), len(raw) - 4)
        self.assertEqual(csum, 0x7b76bada)
        struct.pack_into("<I", raw, len(raw) - 4, csum)

        # 3. Independent Padding
        padded = independent_pad(bytes(raw))
        self.assertEqual(len(padded), 64)
        self.assertEqual(padded[-1], 0x03)

        # 4. Independent Encryption
        ct = independent_pbc_encrypt(self.master_key, padded)
        expected_ct_hex = (
            "b7036a2c2f2da84561b21f7f1c52e9f6d145579be893d283d5cad5d289475c08"
            "ed1c1caaa342ecce31155d44b60ba67bc8519d3fbcf2c7df57d9371d16c659e8"
        )
        self.assertEqual(ct.hex(), expected_ct_hex)

        # 5. Cross-verification with Gateway Engine
        engine_unpacked = self.engine.receive_packet(ct)
        self.assertEqual(engine_unpacked["flags"], 0x01C0)
        self.assertEqual(engine_unpacked["payload"], payload)
        self.assertEqual(engine_unpacked["seq_num"], 1001)
        self.assertEqual(engine_unpacked["channel_id"], 1)
        self.assertEqual(engine_unpacked["stored_checksum"], 0x7b76bada)
        self.assertTrue(engine_unpacked["checksum_verified"])

    def test_02_vector_b_independent_verification(self):
        """
        Verify Vector B (Channel Initialization Request):
        - Flags: 0x03C0 (FLAG_CREATE_CHANNEL | FLAG_INDEXED_CHANNEL | FLAG_HAS_SEQUENCE_NUMBER | FLAG_HAS_CHECKSUM)
        - Payload: b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}' (51 bytes)
        - SeqNum: 1, ChannelID: 1
        """
        payload = b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}'
        flags = 0x03C0
        seq_num = 1
        channel_id = 1

        footers = bytearray()
        footers.extend(struct.pack("<I", seq_num))
        footers.extend(struct.pack("<I", channel_id))
        footers.extend(b"\x00\x00\x00\x00")

        raw = bytearray(struct.pack("<H", flags)) + payload + footers
        self.assertEqual(len(raw), 65)

        csum = independent_xor_checksum(bytes(raw), len(raw) - 4)
        self.assertEqual(csum, 0x034614e4)
        struct.pack_into("<I", raw, len(raw) - 4, csum)

        padded = independent_pad(bytes(raw))
        self.assertEqual(len(padded), 72)
        self.assertEqual(padded[-1], 0x07)

        ct = independent_pbc_encrypt(self.master_key, padded)
        expected_ct_hex = (
            "a4888882203c781be215b8e8e5d216a7b6a458cd99c422edbc26534e6dde6eeb"
            "2993ef333f5a7096f9287dca9ed23679b5829c275d42143efd0ae49515cb7336"
            "c915ca5b5fbc2e38"
        )
        self.assertEqual(ct.hex(), expected_ct_hex)

        engine_unpacked = self.engine.receive_packet(ct)
        self.assertEqual(engine_unpacked["flags"], 0x03C0)
        self.assertTrue(engine_unpacked["is_create_channel"])
        self.assertEqual(engine_unpacked["seq_num"], 1)
        self.assertEqual(engine_unpacked["channel_id"], 1)
        self.assertEqual(engine_unpacked["stored_checksum"], 0x034614e4)

    def test_03_vector_c_independent_verification(self):
        """
        Verify Vector C (Application Message):
        - Flags: 0x01C8 (FLAG_ON_CHANNEL | FLAG_INDEXED_CHANNEL | FLAG_HAS_SEQUENCE_NUMBER | FLAG_HAS_CHECKSUM)
        - Payload: b"PING_MESSAGE_ON_CHANNEL_1" (25 bytes)
        - SeqNum: 2, ChannelID: 1
        """
        payload = b"PING_MESSAGE_ON_CHANNEL_1"
        flags = 0x01C8
        seq_num = 2
        channel_id = 1

        footers = bytearray()
        footers.extend(struct.pack("<I", seq_num))
        footers.extend(struct.pack("<I", channel_id))
        footers.extend(b"\x00\x00\x00\x00")

        raw = bytearray(struct.pack("<H", flags)) + payload + footers
        self.assertEqual(len(raw), 39)

        csum = independent_xor_checksum(bytes(raw), len(raw) - 4)
        self.assertEqual(csum, 0x043f1ec7)
        struct.pack_into("<I", raw, len(raw) - 4, csum)

        padded = independent_pad(bytes(raw))
        self.assertEqual(len(padded), 40)
        self.assertEqual(padded[-1], 0x01)

        ct = independent_pbc_encrypt(self.master_key, padded)
        expected_ct_hex = (
            "49b5eb66b9bd84a291e6fb8b81d8d485c8a2ad12404d3c2fe833d666c0acb182"
            "bdd4a6fa46a65029"
        )
        self.assertEqual(ct.hex(), expected_ct_hex)

        engine_unpacked = self.engine.receive_packet(ct)
        self.assertEqual(engine_unpacked["flags"], 0x01C8)
        self.assertTrue(engine_unpacked["is_on_channel"])
        self.assertEqual(engine_unpacked["seq_num"], 2)
        self.assertEqual(engine_unpacked["channel_id"], 1)
        self.assertEqual(engine_unpacked["stored_checksum"], 0x043f1ec7)

    def test_04_vector_d_independent_verification(self):
        """
        Verify Vector D (Application Response with Piggybacked ACK):
        - Flags: 0x01CC (FLAG_ON_CHANNEL | FLAG_INDEXED_CHANNEL | FLAG_HAS_SEQUENCE_NUMBER | FLAG_HAS_ACKS | FLAG_HAS_CHECKSUM)
        - Payload: b"ACK_AND_ECHO:PING_MESSAGE_ON_CHANNEL_1" (38 bytes)
        - SeqNum: 1001, ACKs: [2], ChannelID: 1
        """
        payload = b"ACK_AND_ECHO:PING_MESSAGE_ON_CHANNEL_1"
        flags = 0x01CC
        seq_num = 1001
        channel_id = 1
        acks = [2]

        footers = bytearray()
        footers.extend(struct.pack("<I", seq_num))
        for ack in acks:
            footers.extend(struct.pack("<I", ack))
        footers.append(len(acks))
        footers.extend(struct.pack("<I", channel_id))
        footers.extend(b"\x00\x00\x00\x00")

        raw = bytearray(struct.pack("<H", flags)) + payload + footers
        self.assertEqual(len(raw), 57)

        csum = independent_xor_checksum(bytes(raw), len(raw) - 4)
        self.assertEqual(csum, 0x71604366)
        struct.pack_into("<I", raw, len(raw) - 4, csum)

        padded = independent_pad(bytes(raw))
        self.assertEqual(len(padded), 64)
        self.assertEqual(padded[-1], 0x07)

        ct = independent_pbc_encrypt(self.master_key, padded)
        expected_ct_hex = (
            "4a2ecb8a13e4374dfb0d9e35c473f6b4b33c3b2b657dd3d449a88cc671b2ea56"
            "a5d6c1a722ecb444f71e579a3df958a32148fcfff038339256cf717fe681381a"
        )
        self.assertEqual(ct.hex(), expected_ct_hex)

        engine_unpacked = self.engine.receive_packet(ct)
        self.assertEqual(engine_unpacked["flags"], 0x01CC)
        self.assertEqual(engine_unpacked["seq_num"], 1001)
        self.assertEqual(engine_unpacked["acks"], [2])
        self.assertEqual(engine_unpacked["channel_id"], 1)
        self.assertEqual(engine_unpacked["stored_checksum"], 0x71604366)

    def test_05_independent_bidirectional_roundtrip(self):
        """Verify independent encryptor decrypted by gateway, and gateway output decrypted by independent decryptor."""
        # Case A: Independent -> Gateway
        orig_msg = b"ARBITRARY_TEST_MESSAGE_FOR_CROSS_COMPATIBILITY_12345"
        pkt = MercuryPacketParser.pack(
            payload=orig_msg,
            seq_num=42,
            channel_id=1,
            is_on_channel=True,
            with_checksum=True
        )
        csum = independent_xor_checksum(bytes(pkt), len(pkt) - 4)
        struct.pack_into("<I", pkt, len(pkt) - 4, csum)
        ct_indep = independent_pbc_encrypt(self.master_key, independent_pad(bytes(pkt)))

        unpacked_by_gw = self.engine.receive_packet(ct_indep)
        self.assertEqual(unpacked_by_gw["payload"], orig_msg)
        self.assertEqual(unpacked_by_gw["seq_num"], 42)

        # Case B: Gateway -> Independent
        ct_gw = self.engine.send_packet(
            payload=orig_msg,
            seq_num=99,
            channel_id=1,
            is_on_channel=True,
            enable_checksum=True
        )
        pt_dec_indep = independent_pbc_decrypt(self.master_key, ct_gw)
        unpadded_indep = independent_unpad(pt_dec_indep)
        unpacked_indep = MercuryPacketParser.unpack_footers(bytearray(unpadded_indep))
        self.assertEqual(unpacked_indep["payload"], orig_msg)
        self.assertEqual(unpacked_indep["seq_num"], 99)


if __name__ == "__main__":
    unittest.main()
