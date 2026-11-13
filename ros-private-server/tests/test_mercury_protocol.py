"""
Unit tests for Mercury UDP packet framing, footers, and message decoding.
Validates:
1. Header encoding and decoding with flags.
2. Footer ordering and reverse-order unpacking.
3. Checksum verification.
4. ACK count and sequence unpacking.
5. Rejection of undersized, corrupted, and invalid packets.
6. Bundled message framing (fixed and variable length).
"""

import struct
import zlib
import pytest

from mercury.constants import (
    FLAG_RELIABLE,
    FLAG_HAS_ACKS,
    FLAG_HAS_SEQUENCE_NUMBER,
    FLAG_INDEXED_CHANNEL,
    FLAG_HAS_CHECKSUM,
    FLAG_CREATE_CHANNEL,
    MAX_VALID_FLAGS,
    LENGTH_FIXED,
    LENGTH_VARIABLE_1,
)
from mercury.packet import MalformedPacketError, MercuryPacket
from mercury.message import MercuryMessage


class TestMercuryPacketFraming:
    """Tests for raw packet serialization and parsing."""

    def test_encode_decode_basic_packet(self):
        packet = MercuryPacket(
            flags=0,
            body=b"Hello Mercury"
        )
        data = packet.encode()
        assert len(data) == 2 + len(b"Hello Mercury")
        # Check flags (first 2 bytes)
        flags = struct.unpack_from("<H", data, 0)[0]
        assert flags == 0

        decoded = MercuryPacket.decode(data)
        assert decoded.flags == 0
        assert decoded.body == b"Hello Mercury"
        assert decoded.seq_num is None
        assert decoded.acks == []

    def test_encode_decode_sequenced_packet(self):
        packet = MercuryPacket(
            flags=FLAG_RELIABLE,
            seq_num=42,
            body=b"SequencedData"
        )
        data = packet.encode()
        decoded = MercuryPacket.decode(data)
        assert decoded.is_reliable()
        assert decoded.flags & FLAG_HAS_SEQUENCE_NUMBER
        assert decoded.seq_num == 42
        assert decoded.body == b"SequencedData"

    def test_encode_decode_with_acks(self):
        packet = MercuryPacket(
            flags=0,
            acks=[10, 11, 12],
            body=b"AckPayload"
        )
        data = packet.encode()
        decoded = MercuryPacket.decode(data)
        assert decoded.flags & FLAG_HAS_ACKS
        assert decoded.acks == [10, 11, 12]
        assert decoded.body == b"AckPayload"

    def test_encode_decode_with_indexed_channel(self):
        packet = MercuryPacket(
            flags=0,
            indexed_channel_id=999,
            body=b"ChannelData"
        )
        data = packet.encode()
        decoded = MercuryPacket.decode(data)
        assert decoded.flags & FLAG_INDEXED_CHANNEL
        assert decoded.indexed_channel_id == 999
        assert decoded.body == b"ChannelData"

    def test_encode_decode_with_checksum(self):
        packet = MercuryPacket(
            flags=FLAG_RELIABLE,
            seq_num=100,
            body=b"ChecksumProtectedPayload",
            enable_checksum=True
        )
        data = packet.encode()
        decoded = MercuryPacket.decode(data)
        assert decoded.flags & FLAG_HAS_CHECKSUM
        assert decoded.seq_num == 100
        assert decoded.body == b"ChecksumProtectedPayload"

    def test_full_packet_with_all_footers(self):
        packet = MercuryPacket(
            flags=FLAG_RELIABLE | FLAG_CREATE_CHANNEL,
            seq_num=501,
            acks=[100, 101],
            indexed_channel_id=77,
            body=b"ComplexPacketBody",
            enable_checksum=True
        )
        data = packet.encode()
        decoded = MercuryPacket.decode(data)
        assert decoded.is_reliable()
        assert decoded.is_channel_create()
        assert decoded.seq_num == 501
        assert decoded.acks == [100, 101]
        assert decoded.indexed_channel_id == 77
        assert decoded.body == b"ComplexPacketBody"


class TestMercuryMalformedPacketRejection:
    """Tests that malformed packets are strictly rejected matching processFilteredPacket rules."""

    def test_reject_undersized_packet(self):
        # Packets must be >= 3 bytes
        with pytest.raises(MalformedPacketError, match="received undersize packet"):
            MercuryPacket.decode(b"")

        with pytest.raises(MalformedPacketError, match="received undersize packet"):
            MercuryPacket.decode(b"\x00")

        with pytest.raises(MalformedPacketError, match="received undersize packet"):
            MercuryPacket.decode(b"\x00\x00")

    def test_reject_bad_flags(self):
        # Flags >= 0x0400 are illegal
        bad_flags_data = struct.pack("<H", 0x0400) + b"Data"
        with pytest.raises(MalformedPacketError, match="received packet with bad flags"):
            MercuryPacket.decode(bad_flags_data)

        bad_flags_data2 = struct.pack("<H", 0xFFFF) + b"Data"
        with pytest.raises(MalformedPacketError, match="received packet with bad flags"):
            MercuryPacket.decode(bad_flags_data2)

    def test_reject_checksum_failure(self):
        # Construct valid checksummed packet, then corrupt payload
        packet = MercuryPacket(seq_num=1, body=b"OriginalData", enable_checksum=True)
        raw = bytearray(packet.encode())
        # Corrupt one byte of the body
        raw[2] ^= 0xFF
        with pytest.raises(MalformedPacketError, match="failed checksum"):
            MercuryPacket.decode(bytes(raw))

    def test_reject_packet_too_short_for_checksum(self):
        # FLAG_HAS_CHECKSUM set but length < 6 bytes
        corrupted = struct.pack("<H", FLAG_HAS_CHECKSUM) + b"12"  # total length 4
        with pytest.raises(MalformedPacketError, match="Packet too short"):
            MercuryPacket.decode(corrupted)

    def test_reject_flag_has_acks_with_zero_count(self):
        # FLAG_HAS_ACKS set, but ack count byte is 0
        corrupted = struct.pack("<H", FLAG_HAS_ACKS) + b"body" + b"\x00"
        with pytest.raises(MalformedPacketError, match="had 0 acks"):
            MercuryPacket.decode(corrupted)

    def test_reject_truncated_acks(self):
        # FLAG_HAS_ACKS claims 2 acks (needs 8 bytes), but only 4 bytes provided
        corrupted = struct.pack("<H", FLAG_HAS_ACKS) + struct.pack("<I", 100) + b"\x02"
        with pytest.raises(MalformedPacketError, match="Not enough footers for 2 acks"):
            MercuryPacket.decode(corrupted)

    def test_reject_truncated_sequence_number(self):
        # FLAG_HAS_SEQUENCE_NUMBER claims uint32 seq num, but only 2 bytes left in footer
        corrupted = struct.pack("<H", FLAG_HAS_SEQUENCE_NUMBER) + b"\x01\x02"
        with pytest.raises(MalformedPacketError, match="Not enough data for sequence number footer"):
            MercuryPacket.decode(corrupted)


class TestMercuryMessageFraming:
    """Tests for message serialization within bundle body."""

    def test_variable_length_message(self):
        msg = MercuryMessage(message_id=15, payload=b"AuthenticatePayload")
        data = msg.encode()
        assert data[0] == 15
        assert data[1] == len(b"AuthenticatePayload")
        assert data[2:] == b"AuthenticatePayload"

        decoded = MercuryMessage.decode_stream(data)
        assert len(decoded) == 1
        assert decoded[0].message_id == 15
        assert decoded[0].payload == b"AuthenticatePayload"

    def test_multiple_bundled_messages(self):
        msg1 = MercuryMessage(message_id=1, payload=b"Msg1")
        msg2 = MercuryMessage(message_id=2, payload=b"MsgTwo")
        msg3 = MercuryMessage(message_id=3, payload=b"MessageThree")

        bundle_body = msg1.encode() + msg2.encode() + msg3.encode()
        messages = MercuryMessage.decode_stream(bundle_body)
        assert len(messages) == 3
        assert messages[0].message_id == 1
        assert messages[0].payload == b"Msg1"
        assert messages[1].message_id == 2
        assert messages[1].payload == b"MsgTwo"
        assert messages[2].message_id == 3
        assert messages[2].payload == b"MessageThree"

    def test_fixed_length_message(self):
        msg = MercuryMessage(message_id=10, payload=b"1234", length_format=LENGTH_FIXED)
        data = msg.encode()
        assert len(data) == 5  # 1 byte ID + 4 bytes payload, no length prefix
        messages = MercuryMessage.decode_stream(data, fixed_lengths={10: 4})
        assert len(messages) == 1
        assert messages[0].message_id == 10
        assert messages[0].payload == b"1234"
