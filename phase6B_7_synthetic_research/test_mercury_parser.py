"""
Offline Synthetic Mercury UDP Reverse-Order Footer Parser Verification Module
Phase 6.2B.7 - Research Only

Implements and tests the exact packet layout disassembled from:
neox::bwclient::Mercury::Nub::processFilteredPacket (VA 0x100922860 - 0x1009231ac):
- Packet Header (Offset 0): 2 bytes (uint16_t little-endian) = Flags (VA 0x100922894)
- Packet Body (Offset 2..Tail): Message bundle payload
- Packet Footers (Tail): Unpacked backwards from end of packet:
  1. Checksum (4 bytes at absolute tail if FLAG_HAS_CHECKSUM = 0x0100)
  2. Piggybacked Bundle (2 bytes length + M bytes data if FLAG_HAS_PIGGYBACKS = 0x0002)
  3. Indexed Channel ID (4 bytes if FLAG_INDEXED_CHANNEL = 0x0080)
  4. Piggybacked ACKs (1 byte count + N*4 bytes if FLAG_HAS_ACKS = 0x0008)
  5. Sequence Number (4 bytes if FLAG_HAS_SEQUENCE_NUMBER = 0x0004)
  6. First Request Offset (2 bytes if FLAG_HAS_REQUESTS = 0x0040)
"""

import struct
import unittest
from typing import Dict, Any, List, Optional


class MercuryPacketFlags:
    FLAG_CREATE_CHANNEL = 0x0001
    FLAG_HAS_PIGGYBACKS = 0x0002
    FLAG_HAS_SEQUENCE_NUMBER = 0x0004
    FLAG_HAS_ACKS = 0x0008
    FLAG_ON_CHANNEL = 0x0020
    FLAG_HAS_REQUESTS = 0x0040
    FLAG_INDEXED_CHANNEL = 0x0080
    FLAG_HAS_CHECKSUM = 0x0100

    ALL_SUPPORTED_MASKS = (
        FLAG_CREATE_CHANNEL | FLAG_HAS_PIGGYBACKS | FLAG_HAS_SEQUENCE_NUMBER |
        FLAG_HAS_ACKS | FLAG_ON_CHANNEL | FLAG_HAS_REQUESTS |
        FLAG_INDEXED_CHANNEL | FLAG_HAS_CHECKSUM
    )


def compute_mercury_checksum(packet_bytes: bytearray) -> int:
    """
    Computes 32-bit XOR checksum disassembled from VA 0x100922bdc - 0x100922c44.
    Checksum is the XOR sum of all 32-bit little-endian dwords across the datagram,
    with the 4-byte checksum field itself zeroed out.
    """
    total_len = len(packet_bytes)
    # Pad to 4-byte boundary for dword processing
    pad = (4 - (total_len % 4)) % 4
    buf = packet_bytes + bytes(pad)

    checksum = 0
    for offset in range(0, len(buf), 4):
        val = struct.unpack_from("<I", buf, offset)[0]
        checksum ^= val
    return checksum


class MercuryPacketParser:
    MAX_PACKET_SIZE = 2048
    MIN_PACKET_SIZE = 2  # Must at least contain 16-bit flags word at offset 0

    @classmethod
    def pack(
        cls,
        payload: bytes,
        flags: int = 0,
        seq_num: Optional[int] = None,
        channel_id: Optional[int] = None,
        acks: Optional[List[int]] = None,
        piggyback: Optional[bytes] = None,
        first_request_offset: Optional[int] = None,
        with_checksum: bool = False
    ) -> bytes:
        """
        Synthesizes a Mercury packet matching client binary layout:
        [Header: 2-byte flags] [Payload] [Footers: RequestOffset, SeqNum, ACKs, ChannelID, Piggyback, Checksum]
        """
        footers = bytearray()

        # Footers are appended in forward order so they appear in reverse order when read backwards:
        # 1. Request / Fragment offset (if FLAG_HAS_REQUESTS)
        if first_request_offset is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_REQUESTS
            footers.extend(struct.pack("<H", first_request_offset))

        # 2. Sequence number (if FLAG_HAS_SEQUENCE_NUMBER)
        if seq_num is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER
            footers.extend(struct.pack("<I", seq_num))

        # 3. Piggybacked ACKs (if FLAG_HAS_ACKS)
        if acks is not None and len(acks) > 0:
            flags |= MercuryPacketFlags.FLAG_HAS_ACKS
            ack_count = len(acks)
            if ack_count > 255:
                raise ValueError("ACK count exceeds 255")
            for ack in acks:
                footers.extend(struct.pack("<I", ack))
            footers.append(ack_count)

        # 4. Indexed Channel ID (if FLAG_INDEXED_CHANNEL)
        if channel_id is not None:
            flags |= MercuryPacketFlags.FLAG_INDEXED_CHANNEL
            footers.extend(struct.pack("<I", channel_id))

        # 5. Piggybacked Bundle (if FLAG_HAS_PIGGYBACKS)
        if piggyback is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_PIGGYBACKS
            p_len = len(piggyback)
            if p_len > 65535:
                raise ValueError("Piggyback length exceeds 65535")
            footers.extend(piggyback)
            footers.extend(struct.pack("<H", p_len))

        if with_checksum:
            flags |= MercuryPacketFlags.FLAG_HAS_CHECKSUM

        # Header: 16-bit flags word at offset 0
        buf = bytearray(struct.pack("<H", flags))
        buf.extend(payload)
        buf.extend(footers)

        # 6. Checksum (if FLAG_HAS_CHECKSUM)
        if with_checksum:
            buf.extend(b"\x00\x00\x00\x00")
            csum = compute_mercury_checksum(buf)
            struct.pack_into("<I", buf, len(buf) - 4, csum)

        if len(buf) > cls.MAX_PACKET_SIZE:
            raise ValueError(f"Packet size {len(buf)} exceeds MAX_PACKET_SIZE {cls.MAX_PACKET_SIZE}")

        return bytes(buf)

    @classmethod
    def unpack(cls, raw: bytes) -> Dict[str, Any]:
        """
        Parses a Mercury packet matching Nub::processFilteredPacket:
        Reads flags at offset 0, then unpacks footers backwards from tail.
        """
        total_len = len(raw)
        if total_len > cls.MAX_PACKET_SIZE:
            raise ValueError(f"Packet too large ({total_len} > {cls.MAX_PACKET_SIZE})")
        if total_len < cls.MIN_PACKET_SIZE:
            raise ValueError(f"Packet undersized ({total_len} < {cls.MIN_PACKET_SIZE})")

        # 1. Read Packet Flags Word at Offset 0 (VA 0x100922894: ldrh w8, [x28, #0x60])
        flags = struct.unpack_from("<H", raw, 0)[0]
        if flags >= 0x0400:  # VA 0x100922898: cmp w8, #0x400
            raise ValueError(f"Nub::processFilteredPacket: received packet with bad flags 0x{flags:04x}")

        unknown_flags = flags & ~MercuryPacketFlags.ALL_SUPPORTED_MASKS
        if unknown_flags != 0:
            raise ValueError(f"Packet contains unknown flag bits: 0x{unknown_flags:04x}")

        head = 2  # Payload starts after 2-byte header
        tail = total_len

        # 2. Check for Checksum Footer (Bit 8 = 0x0100)
        has_checksum = False
        if flags & MercuryPacketFlags.FLAG_HAS_CHECKSUM:
            has_checksum = True
            if tail - head < 4:
                raise ValueError("Packet too short for checksum!")
            tail -= 4
            expected_csum = struct.unpack_from("<I", raw, tail)[0]
            verify_buf = bytearray(raw)
            struct.pack_into("<I", verify_buf, tail, 0)
            calculated_csum = compute_mercury_checksum(verify_buf)
            if calculated_csum != expected_csum:
                raise ValueError(
                    f"Packet (flags 0x{flags:04x}, size {total_len}) failed checksum "
                    f"(wanted 0x{expected_csum:08x}, got 0x{calculated_csum:08x})"
                )

        piggyback_bundle = None
        channel_id = None
        acks = []
        seq_num = None
        first_request_offset = None

        # 3. Piggybacked Bundle (FLAG_HAS_PIGGYBACKS = 0x0002)
        if flags & MercuryPacketFlags.FLAG_HAS_PIGGYBACKS:
            if tail - head < 2:
                raise ValueError("Not enough data for piggyback length footer")
            tail -= 2
            p_len = struct.unpack_from("<H", raw, tail)[0]
            if tail - head < p_len:
                raise ValueError(f"Not enough data for piggyback payload (need {p_len}, have {tail - head})")
            tail -= p_len
            piggyback_bundle = raw[tail : tail + p_len]

        # 4. Indexed Channel ID (FLAG_INDEXED_CHANNEL = 0x0080)
        if flags & MercuryPacketFlags.FLAG_INDEXED_CHANNEL:
            if tail - head < 4:
                raise ValueError("Not enough data for indexed channel ID footer")
            tail -= 4
            channel_id = struct.unpack_from("<I", raw, tail)[0]

        # 5. Piggybacked ACKs (FLAG_HAS_ACKS = 0x0008)
        if flags & MercuryPacketFlags.FLAG_HAS_ACKS:
            if tail - head < 1:
                raise ValueError("Not enough data for ACK count footer")
            tail -= 1
            ack_count = raw[tail]
            if ack_count == 0:
                raise ValueError("Packet with FLAG_HAS_ACKS had 0 acks")
            needed_bytes = ack_count * 4
            if tail - head < needed_bytes:
                raise ValueError(f"Not enough data for {ack_count} ACKs (need {needed_bytes}, have {tail - head})")
            tail -= needed_bytes
            for i in range(ack_count):
                ack_seq = struct.unpack_from("<I", raw, tail + i * 4)[0]
                acks.append(ack_seq)

        # 6. Sequence Number (FLAG_HAS_SEQUENCE_NUMBER = 0x0004)
        if flags & MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER:
            if tail - head < 4:
                raise ValueError("Not enough data for sequence number footer")
            tail -= 4
            seq_num = struct.unpack_from("<I", raw, tail)[0]

        # 7. Request Offset / Fragment Spec (FLAG_HAS_REQUESTS = 0x0040)
        if flags & MercuryPacketFlags.FLAG_HAS_REQUESTS:
            if tail - head < 2:
                raise ValueError("Not enough data for first request offset footer")
            tail -= 2
            first_request_offset = struct.unpack_from("<H", raw, tail)[0]

        # Remaining bytes between head and tail represent the payload
        payload = raw[head:tail]

        return {
            "payload": payload,
            "flags": flags,
            "seq_num": seq_num,
            "channel_id": channel_id,
            "acks": acks,
            "piggyback": piggyback_bundle,
            "first_request_offset": first_request_offset,
            "has_checksum": has_checksum
        }


class TestSyntheticMercuryParser(unittest.TestCase):
    def test_01_empty_optional_footers(self):
        """Verify parsing a packet with only header flags and payload."""
        payload = b"LOGIN_REQUEST_MESSAGE_BODY"
        pkt = MercuryPacketParser.pack(payload, flags=0)
        self.assertEqual(len(pkt), len(payload) + 2)

        unpacked = MercuryPacketParser.unpack(pkt)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["flags"], 0)
        self.assertIsNone(unpacked["seq_num"])
        self.assertIsNone(unpacked["channel_id"])
        self.assertEqual(unpacked["acks"], [])
        self.assertIsNone(unpacked["piggyback"])

    def test_02_individual_footer_sequence_number(self):
        """Verify parsing packet with only Sequence Number footer."""
        payload = b"PING_PACKET"
        seq = 1042
        pkt = MercuryPacketParser.pack(payload, seq_num=seq)
        unpacked = MercuryPacketParser.unpack(pkt)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["seq_num"], seq)
        self.assertTrue(unpacked["flags"] & MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER)

    def test_03_individual_footer_channel_id(self):
        """Verify parsing packet with only Indexed Channel ID footer."""
        payload = b"BASEAPP_RPC_DATA"
        chan = 0x12345678
        pkt = MercuryPacketParser.pack(payload, channel_id=chan)
        unpacked = MercuryPacketParser.unpack(pkt)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["channel_id"], chan)
        self.assertTrue(unpacked["flags"] & MercuryPacketFlags.FLAG_INDEXED_CHANNEL)

    def test_04_individual_footer_acks(self):
        """Verify parsing packet with Piggybacked ACKs."""
        payload = b"ACK_CONFIRMATION"
        acks = [101, 102, 103, 105]
        pkt = MercuryPacketParser.pack(payload, acks=acks)
        unpacked = MercuryPacketParser.unpack(pkt)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["acks"], acks)
        self.assertTrue(unpacked["flags"] & MercuryPacketFlags.FLAG_HAS_ACKS)

    def test_05_individual_footer_piggyback(self):
        """Verify parsing packet with Piggybacked bundle."""
        payload = b"PRIMARY_PAYLOAD"
        piggy = b"PIGGYBACKED_SUB_BUNDLE"
        pkt = MercuryPacketParser.pack(payload, piggyback=piggy)
        unpacked = MercuryPacketParser.unpack(pkt)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["piggyback"], piggy)
        self.assertTrue(unpacked["flags"] & MercuryPacketFlags.FLAG_HAS_PIGGYBACKS)

    def test_06_all_footers_combined(self):
        """Verify parsing packet with ALL supported footers combined simultaneously."""
        payload = b"FULL_COMPLEX_MERCURY_DATAGRAM"
        seq = 9999
        chan = 0xCAFEBABE
        acks = [12, 13, 14]
        piggy = b"SUB_PACKET_99"
        req_offset = 64

        pkt = MercuryPacketParser.pack(
            payload=payload,
            seq_num=seq,
            channel_id=chan,
            acks=acks,
            piggyback=piggy,
            first_request_offset=req_offset,
            with_checksum=True
        )

        unpacked = MercuryPacketParser.unpack(pkt)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["seq_num"], seq)
        self.assertEqual(unpacked["channel_id"], chan)
        self.assertEqual(unpacked["acks"], acks)
        self.assertEqual(unpacked["piggyback"], piggy)
        self.assertEqual(unpacked["first_request_offset"], req_offset)
        self.assertTrue(unpacked["has_checksum"])

    def test_07_checksum_verification_and_tamper_detection(self):
        """Verify 32-bit XOR checksum passes on valid packet and fails on tampered packet."""
        payload = b"INTEGRITY_CHECK_TEST_PAYLOAD"
        pkt = bytearray(MercuryPacketParser.pack(payload, seq_num=500, with_checksum=True))

        # Valid checksum unpack
        unpacked = MercuryPacketParser.unpack(bytes(pkt))
        self.assertEqual(unpacked["payload"], payload)
        self.assertTrue(unpacked["has_checksum"])

        # Tamper 1 byte in payload (byte 4)
        pkt[4] ^= 0x01
        with self.assertRaises(ValueError) as ctx:
            MercuryPacketParser.unpack(bytes(pkt))
        self.assertIn("failed checksum", str(ctx.exception))

    def test_08_truncated_packet_handling(self):
        """Verify truncated packets raise clear errors without crashes."""
        # 1 byte packet (cannot even hold flags word)
        with self.assertRaises(ValueError) as ctx:
            MercuryPacketParser.unpack(b"\x01")
        self.assertIn("undersized", str(ctx.exception))

        # Packet header flags claims FLAG_HAS_SEQUENCE_NUMBER but is missing the 4 bytes
        corrupted = struct.pack("<H", MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER)
        with self.assertRaises(ValueError) as ctx:
            MercuryPacketParser.unpack(corrupted)
        self.assertIn("Not enough data for sequence number", str(ctx.exception))

    def test_09_invalid_ack_count(self):
        """Verify invalid ACK count raises an error."""
        # Packet with FLAG_HAS_ACKS but count=0 at tail
        flags = MercuryPacketFlags.FLAG_HAS_ACKS
        corrupted = struct.pack("<H", flags) + b"\x00"  # ack_count = 0
        with self.assertRaises(ValueError) as ctx:
            MercuryPacketParser.unpack(corrupted)
        self.assertIn("had 0 acks", str(ctx.exception))

    def test_10_bad_flags_rejection(self):
        """Verify flags >= 0x0400 are rejected matching cmp w8, #0x400."""
        flags = 0x0400  # Bad flags threshold
        corrupted = struct.pack("<H", flags)
        with self.assertRaises(ValueError) as ctx:
            MercuryPacketParser.unpack(corrupted)
        self.assertIn("bad flags", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
