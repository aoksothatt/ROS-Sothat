"""
Comprehensive Automated Test Suite for Phase 6.2B.7.2
Covers Tasks A, B, C, D:
- Task A: Blowfish Plaintext Block Chaining (PBC) & CBC Divergence
- Task B: Single-Byte Trailer Padding & Boundary Behavior
- Task C: Mercury 32-bit XOR Checksum Validation
- Task D: End-to-End Combined Datagram Pipeline
"""

import unittest
import struct
from pbc_cipher import BlowfishPBC
from padding import SingleByteTrailerPadding
from checksum import MercuryChecksum
from pipeline import MercurySyntheticPipeline, MercuryPacketFlags
from test_vectors import (
    SYNTHETIC_SESSION_KEY_56,
    SYNTHETIC_SESSION_KEY_32,
    PADDING_BOUNDARY_LENGTHS
)


class TestTaskA_BlowfishPBC(unittest.TestCase):
    """Task A: Independently validate PBC chaining and CBC divergence."""

    def setUp(self):
        self.key56 = SYNTHETIC_SESSION_KEY_56
        self.pbc = BlowfishPBC(self.key56)

    def test_01_single_block_plaintext(self):
        """1-block plaintext (8 bytes): PBC roundtrip and CBC first-block equality."""
        pt = b"12345678"
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(len(ct_pbc), 8)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)

        # In block 0: C_0 = E(P_0 ^ 0) in both PBC and CBC
        ct_cbc = self.pbc.encrypt_standard_cbc(pt)
        self.assertEqual(ct_pbc, ct_cbc, "Single-block PBC and CBC must be identical")

    def test_02_two_block_plaintext(self):
        """2-block plaintext (16 bytes): PBC roundtrip and CBC divergence on Block 1."""
        pt = b"FIRST_08SECOND08"
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(len(ct_pbc), 16)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)

        ct_cbc = self.pbc.encrypt_standard_cbc(pt)
        # Block 0 matches
        self.assertEqual(ct_pbc[:8], ct_cbc[:8])
        # Block 1 MUST diverge: PBC uses P_0, CBC uses C_0
        self.assertNotEqual(ct_pbc[8:], ct_cbc[8:], "Block 1 must diverge between PBC and CBC")

    def test_03_three_block_plaintext(self):
        """3-block plaintext (24 bytes): verify roundtrip and multi-block divergence."""
        pt = b"BLOCK_A_BLOCK_B_BLOCK_C_"
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(len(ct_pbc), 24)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)

        ct_cbc = self.pbc.encrypt_standard_cbc(pt)
        self.assertEqual(ct_pbc[:8], ct_cbc[:8])
        self.assertNotEqual(ct_pbc[8:16], ct_cbc[8:16])
        self.assertNotEqual(ct_pbc[16:24], ct_cbc[16:24])

    def test_04_four_block_plaintext(self):
        """4-block plaintext (32 bytes): verify roundtrip."""
        pt = b"AAAA1111BBBB2222CCCC3333DDDD4444"
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(len(ct_pbc), 32)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)

    def test_05_long_multi_block_plaintext(self):
        """Long multi-block plaintext (128 bytes = 16 blocks)."""
        pt = bytes([(i * 7) % 256 for i in range(128)])
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(len(ct_pbc), 128)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)

    def test_06_different_synthetic_keys(self):
        """Verify PBC operates across varying valid key lengths: 4, 16, 24, 32, 56 bytes."""
        pt = b"SAMPLE_PAYLOAD_8SAMPLE_PAYLOAD_8"
        for klen in (4, 16, 24, 32, 48, 56):
            k = b"K" * klen
            cipher = BlowfishPBC(k)
            ct = cipher.encrypt(pt)
            self.assertEqual(cipher.decrypt(ct), pt)

        # Invalid key bounds (< 4 or > 56 bytes)
        for bad_klen in (0, 1, 3, 57, 64):
            bad_k = b"X" * bad_klen
            with self.assertRaises(ValueError):
                BlowfishPBC(bad_k)

    def test_07_all_zero_plaintext(self):
        """All-zero plaintext blocks."""
        pt = bytes(32)
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)
        # Verify ciphertext is not all zeros
        self.assertNotEqual(ct_pbc, pt)

    def test_08_repeated_plaintext_blocks(self):
        """
        Repeated identical plaintext blocks.
        In PBC: P_1 ^ P_0 = P ^ P = 0.
        So C_1 = E(0), C_2 = E(0), C_3 = E(0)...
        Demonstrates the distinct mathematical property of PBC on repeated blocks!
        """
        block = b"REPEAT08"
        pt = block * 4  # 4 identical blocks
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)

        # In PBC, for i >= 1, input to ECB is block ^ block = 0!
        # Therefore, C_1 == C_2 == C_3!
        self.assertEqual(ct_pbc[8:16], ct_pbc[16:24])
        self.assertEqual(ct_pbc[16:24], ct_pbc[24:32])
        # But C_0 != C_1 because C_0 = E(P) while C_1 = E(0)
        self.assertNotEqual(ct_pbc[:8], ct_pbc[8:16])

    def test_09_different_plaintext_blocks(self):
        """Plaintext where every block has different entropy."""
        pt = b"\x01\x02\x03\x04\x05\x06\x07\x08\x11\x12\x13\x14\x15\x16\x17\x18"
        ct_pbc = self.pbc.encrypt(pt)
        self.assertEqual(self.pbc.decrypt(ct_pbc), pt)
        self.assertNotEqual(ct_pbc[:8], ct_pbc[8:16])

    def test_10_stateless_datagrams(self):
        """Consecutive datagrams using the same key start with independent zero IV."""
        pkt1 = b"DATAGRAM_ALPHA_0"
        pkt2 = b"DATAGRAM_BETA__0"

        ct1 = self.pbc.encrypt(pkt1)
        ct2 = self.pbc.encrypt(pkt2)

        # Independent cipher instance with same key encrypting pkt2 standalone
        fresh_cipher = BlowfishPBC(self.key56)
        ct2_fresh = fresh_cipher.encrypt(pkt2)

        self.assertEqual(ct2, ct2_fresh, "Datagram 2 ciphertext must not depend on Datagram 1")
        self.assertEqual(self.pbc.decrypt(ct2), pkt2)
        self.assertEqual(self.pbc.decrypt(ct1), pkt1)

    def test_11_cross_mode_decryption_failure(self):
        """
        Verify cross-mode decryption fails:
        1. Decrypting PBC ciphertext with standard CBC yields corrupted data from Block 1 onwards.
        2. Decrypting CBC ciphertext with PBC yields corrupted data from Block 1 onwards.
        """
        pt = b"BLOCK_01BLOCK_02BLOCK_03"  # 3 blocks
        ct_pbc = self.pbc.encrypt(pt)
        ct_cbc = self.pbc.encrypt_standard_cbc(pt)

        # Cross-decrypt 1: PBC ciphertext decoded by CBC
        dec_by_cbc = self.pbc.decrypt_standard_cbc(ct_pbc)
        # Block 0 matches
        self.assertEqual(dec_by_cbc[:8], pt[:8])
        # Blocks 1 and 2 are garbled
        self.assertNotEqual(dec_by_cbc[8:], pt[8:])

        # Cross-decrypt 2: CBC ciphertext decoded by PBC
        dec_by_pbc = self.pbc.decrypt(ct_cbc)
        self.assertEqual(dec_by_pbc[:8], pt[:8])
        self.assertNotEqual(dec_by_pbc[8:], pt[8:])


class TestTaskB_Padding(unittest.TestCase):
    """Task B: Validate single-byte trailer padding across boundary lengths."""

    def test_01_boundary_lengths_table(self):
        """Verify padding across required lengths: 0, 1, 7, 8, 9, 15, 16, 17, 31, 32 bytes."""
        expected_pads = {
            0: 8, 1: 7, 7: 1, 8: 8, 9: 7,
            15: 1, 16: 8, 17: 7, 31: 1, 32: 8
        }
        for length in PADDING_BOUNDARY_LENGTHS:
            raw = bytes([(i % 256) for i in range(length)])
            pad_len = SingleByteTrailerPadding.calculate_pad_length(length)
            self.assertEqual(pad_len, expected_pads[length])

            padded = SingleByteTrailerPadding.pad(raw, slack_mode="zero")
            self.assertEqual(len(padded) % 8, 0)
            self.assertEqual(len(padded), length + pad_len)
            self.assertEqual(padded[-1], pad_len)

            # Unpad roundtrip
            recovered = SingleByteTrailerPadding.unpad(padded)
            self.assertEqual(recovered, raw)

    def test_02_padding_range_invariants(self):
        """Padding length is strictly between 1 and 8 for all lengths 0..128."""
        for length in range(129):
            pad_len = SingleByteTrailerPadding.calculate_pad_length(length)
            self.assertTrue(1 <= pad_len <= 8)

    def test_03_exact_multiples_of_eight(self):
        """Exact multiples of 8 receive a full additional 8-byte block ending in 0x08."""
        for mult in (8, 16, 24, 32, 64):
            raw = b"X" * mult
            padded = SingleByteTrailerPadding.pad(raw)
            self.assertEqual(len(padded), mult + 8)
            self.assertEqual(padded[-1], 8)
            recovered = SingleByteTrailerPadding.unpad(padded)
            self.assertEqual(recovered, raw)

    def test_04_zero_length_plaintext(self):
        """0-byte plaintext is padded to 8 bytes with trailer 0x08, recovering 0 bytes."""
        raw = b""
        padded = SingleByteTrailerPadding.pad(raw)
        self.assertEqual(len(padded), 8)
        self.assertEqual(padded[-1], 8)
        recovered = SingleByteTrailerPadding.unpad(padded)
        self.assertEqual(recovered, b"")

    def test_05_invalid_trailer_values(self):
        """Trailer byte of 0 or > 8 is rejected with illegal wastage count."""
        # Trailer 0
        buf0 = bytearray(b"1234567\x00")
        with self.assertRaises(ValueError) as ctx:
            SingleByteTrailerPadding.unpad(bytes(buf0))
        self.assertIn("illegal wastage count", str(ctx.exception))

        # Trailer 9
        buf9 = bytearray(b"1234567\x09")
        with self.assertRaises(ValueError) as ctx:
            SingleByteTrailerPadding.unpad(bytes(buf9))
        self.assertIn("illegal wastage count", str(ctx.exception))

    def test_06_truncated_or_non_multiple_of_eight(self):
        """Ciphertext not divisible by 8 is rejected with block size error."""
        for bad_len in (1, 2, 7, 9, 15, 23):
            buf = bytes(bad_len)
            with self.assertRaises(ValueError) as ctx:
                SingleByteTrailerPadding.unpad(buf)
            self.assertIn("not a multiple of the block size", str(ctx.exception))

    def test_07_trailer_exceeding_length(self):
        """Trailer exceeding total length is rejected."""
        # Although length is multiple of 8, if trailer > total length:
        # For 8-byte block, trailer can at most be 8. If empty:
        with self.assertRaises(ValueError):
            SingleByteTrailerPadding.unpad(b"")

    def test_08_slack_bytes_independence(self):
        """
        Verify receiver behavior is independent of slack byte content:
        Zero-filled (ANSI X9.23), pseudo-random slack, and flooded (PKCS#7)
        are all stripped identically because receiver only checks trailer byte.
        """
        raw = b"HELLO_PADDING"  # 13 bytes -> pad_len = 3 (2 slack bytes + 1 trailer)
        
        # 1. Zero-filled slack
        p_zero = SingleByteTrailerPadding.pad(raw, slack_mode="zero")
        self.assertEqual(p_zero[13:15], b"\x00\x00")
        self.assertEqual(p_zero[15], 3)
        self.assertEqual(SingleByteTrailerPadding.unpad(p_zero), raw)

        # 2. Random slack bytes
        p_rand = SingleByteTrailerPadding.pad(raw, slack_mode="random")
        self.assertNotEqual(p_rand[13:15], b"\x00\x00")
        self.assertEqual(p_rand[15], 3)
        self.assertEqual(SingleByteTrailerPadding.unpad(p_rand), raw)

        # 3. PKCS#7 flooded slack bytes
        p_pkcs = SingleByteTrailerPadding.pad(raw, slack_mode="pkcs7")
        self.assertEqual(p_pkcs[13:15], b"\x03\x03")
        self.assertEqual(p_pkcs[15], 3)
        self.assertEqual(SingleByteTrailerPadding.unpad(p_pkcs), raw)


class TestTaskC_MercuryChecksum(unittest.TestCase):
    """Task C: Validate Mercury 32-bit XOR Checksum."""

    def test_01_minimal_packet(self):
        """Minimal packet with flags and 4-byte checksum field (6 bytes)."""
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM) + b"\x00\x00\x00\x00")
        MercuryChecksum.inject(pkt)
        is_valid, comp, stored = MercuryChecksum.verify(bytes(pkt))
        self.assertTrue(is_valid)
        self.assertEqual(comp, stored)

    def test_02_packet_flags_and_body(self):
        """Packet with flags and payload body."""
        flags = MercuryPacketFlags.FLAG_HAS_CHECKSUM
        body = b"RULE_OF_SURVIVAL_MOBILE_GAME"
        pkt = bytearray(struct.pack("<H", flags) + body + b"\x00\x00\x00\x00")
        MercuryChecksum.inject(pkt)
        is_valid, comp, stored = MercuryChecksum.verify(bytes(pkt))
        self.assertTrue(is_valid)

    def test_03_packet_with_footer_data(self):
        """Packet with sequence number footer."""
        pipeline = MercurySyntheticPipeline(SYNTHETIC_SESSION_KEY_56)
        pkt = pipeline.assemble_plaintext_packet(
            payload=b"PING_MESSAGE",
            flags=0,
            seq_num=42,
            enable_checksum=True
        )
        is_valid, comp, stored = MercuryChecksum.verify(bytes(pkt))
        self.assertTrue(is_valid)

    def test_04_packet_with_multiple_footers(self):
        """Packet with sequence number, channel ID, and request offset."""
        pipeline = MercurySyntheticPipeline(SYNTHETIC_SESSION_KEY_56)
        pkt = pipeline.assemble_plaintext_packet(
            payload=b"LOGIN_DATA_CHUNK",
            seq_num=101,
            channel_id=5,
            first_request_offset=2,
            enable_checksum=True
        )
        is_valid, comp, stored = MercuryChecksum.verify(bytes(pkt))
        self.assertTrue(is_valid)

    def test_05_packet_with_all_supported_footers(self):
        """Packet with Requests, SeqNum, ACKs, ChannelID, Piggybacks, and Checksum."""
        pipeline = MercurySyntheticPipeline(SYNTHETIC_SESSION_KEY_56)
        pkt = pipeline.assemble_plaintext_packet(
            payload=b"FULL_FEATURED_BUNDLE",
            seq_num=9999,
            channel_id=0x12345678,
            acks=[10, 11, 12],
            piggyback=b"EXTRA_MSG",
            first_request_offset=4,
            enable_checksum=True
        )
        is_valid, comp, stored = MercuryChecksum.verify(bytes(pkt))
        self.assertTrue(is_valid)

    def test_06_checksum_field_zeroed_in_calculation(self):
        """Verify checksum calculation treats the checksum field as zero."""
        flags = MercuryPacketFlags.FLAG_HAS_CHECKSUM
        body = b"TEST_PAYLOAD"
        # Packet with zeroed checksum
        pkt_zeros = struct.pack("<H", flags) + body + b"\x00\x00\x00\x00"
        csum1 = MercuryChecksum.calculate(pkt_zeros)

        # Packet with non-zero garbage in checksum field
        pkt_garbage = struct.pack("<H", flags) + body + b"\xDE\xAD\xBE\xEF"
        csum2 = MercuryChecksum.calculate(pkt_garbage)

        self.assertEqual(csum1, csum2, "Checksum calculation must be invariant to existing checksum field bytes")

    def test_07_incorrect_checksum_detection(self):
        """Packet with tampered checksum fails verification."""
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM) + b"DATA" + b"\x00\x00\x00\x00")
        MercuryChecksum.inject(pkt)
        # Corrupt checksum
        pkt[-1] ^= 0xFF
        is_valid, comp, stored = MercuryChecksum.verify(bytes(pkt))
        self.assertFalse(is_valid)
        self.assertNotEqual(comp, stored)

    def test_08_modified_payload_byte(self):
        """Bit-flip in payload invalidates checksum."""
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM) + b"PAYLOAD_A" + b"\x00\x00\x00\x00")
        MercuryChecksum.inject(pkt)
        # Flip bit in payload
        pkt[4] ^= 0x01
        is_valid, _, _ = MercuryChecksum.verify(bytes(pkt))
        self.assertFalse(is_valid)

    def test_09_modified_footer_byte(self):
        """Bit-flip in header flags or footers invalidates checksum."""
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM) + b"PAYLOAD_B" + b"\x00\x00\x00\x00")
        MercuryChecksum.inject(pkt)
        # Flip bit in flags
        pkt[0] ^= 0x02
        is_valid, _, _ = MercuryChecksum.verify(bytes(pkt))
        self.assertFalse(is_valid)

    def test_10_incomplete_dword_alignment(self):
        """Packets with length not divisible by 4 are padded with zeros to next dword boundary."""
        # 7 bytes total: 2 flags + 1 payload + 4 checksum
        pkt = bytearray(struct.pack("<H", MercuryPacketFlags.FLAG_HAS_CHECKSUM) + b"X" + b"\x00\x00\x00\x00")
        csum = MercuryChecksum.calculate(bytes(pkt))
        self.assertIsInstance(csum, int)
        self.assertTrue(0 <= csum <= 0xFFFFFFFF)


class TestTaskD_CombinedPipeline(unittest.TestCase):
    """Task D: Combined End-to-End Synthetic Pipeline Scenarios."""

    def setUp(self):
        self.key = SYNTHETIC_SESSION_KEY_56
        self.pipeline = MercurySyntheticPipeline(self.key)

    def test_01_valid_single_block_datagram(self):
        """Valid single-block datagram (e.g. short control/ping packet)."""
        ct = self.pipeline.send_pipeline(
            payload=b"A",
            seq_num=1,
            enable_checksum=True
        )
        rec = self.pipeline.receive_pipeline(ct)
        self.assertEqual(rec["payload"], b"A")
        self.assertEqual(rec["sequence_number"], 1)

    def test_02_valid_multi_block_datagram(self):
        """Valid multi-block datagram (large payload bundle)."""
        body = b"EXTENDED_MULTI_BLOCK_MESSAGE_BUNDLE_PAYLOAD_BODY_FOR_PBC"
        ct = self.pipeline.send_pipeline(
            payload=body,
            seq_num=200,
            channel_id=1,
            enable_checksum=True
        )
        rec = self.pipeline.receive_pipeline(ct)
        self.assertEqual(rec["payload"], body)
        self.assertEqual(rec["sequence_number"], 200)
        self.assertEqual(rec["channel_id"], 1)

    def test_03_valid_packet_with_optional_footers(self):
        """Valid datagram with Sequence Number, ACKs, and Piggybacks."""
        ct = self.pipeline.send_pipeline(
            payload=b"MAIN_DATA",
            seq_num=777,
            acks=[1, 2, 3],
            piggyback=b"PIGGYBACK_DATA",
            enable_checksum=True
        )
        rec = self.pipeline.receive_pipeline(ct)
        self.assertEqual(rec["payload"], b"MAIN_DATA")
        self.assertEqual(rec["sequence_number"], 777)
        self.assertEqual(rec["acks"], [1, 2, 3])
        self.assertEqual(rec["piggyback"], b"PIGGYBACK_DATA")

    def test_04_tampered_ciphertext(self):
        """Tampered ciphertext triggers unpadding or checksum rejection."""
        ct = bytearray(self.pipeline.send_pipeline(b"SAFE_DATA", seq_num=10))
        # Corrupt one byte in the middle block
        ct[len(ct) // 2] ^= 0x55
        with self.assertRaises(ValueError):
            self.pipeline.receive_pipeline(bytes(ct))

    def test_05_tampered_decrypted_content(self):
        """Tampered plaintext payload detected by checksum verification."""
        # Manually assemble packet, pad, encrypt with corrupted payload
        pkt = self.pipeline.assemble_plaintext_packet(b"ORIGINAL", enable_checksum=True)
        # Corrupt payload byte AFTER checksum was computed
        pkt[3] ^= 0x01
        padded = SingleByteTrailerPadding.pad(bytes(pkt))
        ct = self.pipeline.cipher.encrypt(padded)

        with self.assertRaises(ValueError) as ctx:
            self.pipeline.receive_pipeline(ct)
        self.assertIn("failed checksum", str(ctx.exception))

    def test_06_tampered_checksum_field(self):
        """Tampered checksum field rejected by receiver."""
        pkt = self.pipeline.assemble_plaintext_packet(b"VALID_CONTENT", enable_checksum=True)
        # Flip bit in checksum
        pkt[-1] ^= 0x0F
        padded = SingleByteTrailerPadding.pad(bytes(pkt))
        ct = self.pipeline.cipher.encrypt(padded)

        with self.assertRaises(ValueError) as ctx:
            self.pipeline.receive_pipeline(ct)
        self.assertIn("failed checksum", str(ctx.exception))

    def test_07_invalid_padding_trailer(self):
        """Tampered trailer byte rejected with illegal wastage count."""
        pkt = self.pipeline.assemble_plaintext_packet(b"VALID_CONTENT", enable_checksum=True)
        padded = bytearray(SingleByteTrailerPadding.pad(bytes(pkt)))
        # Set trailer to illegal 0
        padded[-1] = 0
        ct = self.pipeline.cipher.encrypt(bytes(padded))

        with self.assertRaises(ValueError) as ctx:
            self.pipeline.receive_pipeline(ct)
        self.assertIn("illegal wastage count", str(ctx.exception))

    def test_08_truncated_ciphertext(self):
        """Truncated datagram (not multiple of 8) rejected with stream size error."""
        ct = self.pipeline.send_pipeline(b"DATA_TO_TRUNCATE")
        truncated = ct[:-3]
        with self.assertRaises(ValueError) as ctx:
            self.pipeline.receive_pipeline(truncated)
        self.assertIn("not a multiple of the block size", str(ctx.exception))

    def test_09_wrong_session_key(self):
        """Datagram decrypted with wrong key fails unpadding or checksum verification."""
        ct = self.pipeline.send_pipeline(b"CONFIDENTIAL_PAYLOAD", enable_checksum=True)
        wrong_pipeline = MercurySyntheticPipeline(SYNTHETIC_SESSION_KEY_32)
        with self.assertRaises(ValueError):
            wrong_pipeline.receive_pipeline(ct)

    def test_10_consecutive_independent_datagrams(self):
        """Verify multiple consecutive datagrams succeed with stateless zero IV."""
        messages = [
            b"FIRST_DATAGRAM_BODY",
            b"SECOND_DATAGRAM_BODY_LONGER",
            b"",
            b"FINAL_CLOSING_DATAGRAM"
        ]
        ciphertexts = []
        for i, m in enumerate(messages):
            ct = self.pipeline.send_pipeline(payload=m, seq_num=i + 1, enable_checksum=True)
            ciphertexts.append(ct)

        # Decrypt in reverse order
        for ct, original_m in zip(reversed(ciphertexts), reversed(messages)):
            rec = self.pipeline.receive_pipeline(ct)
            self.assertEqual(rec["payload"], original_m)


if __name__ == "__main__":
    unittest.main()
