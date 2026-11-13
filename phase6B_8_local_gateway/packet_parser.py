"""
Mercury Packet Framing & Parser Module
Phase 6.2B.8 - Research & Prototype Only

Directly models native NetEase BigWorld Mercury packet framing disassembled from:
neox::bwclient::Mercury::Nub::processFilteredPacket (VA 0x100922860 - 0x1009231ac)

Packet Layout:
[Header: 2-byte Flags Word (Offset 0)] [Payload Bundle Body] [Footers in Reverse Order]

Footers Unpacking Order (from Packet Tail backwards):
1. Checksum (4 bytes uint32 little-endian if FLAG_HAS_CHECKSUM = 0x0100)
2. Piggyback Bundle (2 bytes int16 length + M bytes data if FLAG_HAS_PIGGYBACKS = 0x0002)
3. Indexed Channel ID (4 bytes uint32 little-endian if FLAG_INDEXED_CHANNEL = 0x0080)
4. Piggybacked ACKs (1 byte count + N*4 bytes uint32 if FLAG_HAS_ACKS = 0x0008)
5. Sequence Number (4 bytes uint32 little-endian if FLAG_HAS_SEQUENCE_NUMBER = 0x0004)
6. First Request Offset (2 bytes uint16 little-endian if FLAG_HAS_REQUESTS = 0x0040)
"""

import struct
from typing import Dict, Any, List, Optional, Tuple


class MercuryPacketFlags:
    FLAG_HAS_REQUESTS        = 0x0001  # Bit 0: First request offset (2 bytes uint16 <H)
    FLAG_HAS_PIGGYBACKS      = 0x0002  # Bit 1: Piggybacked bundle (2 bytes len <h + M bytes)
    FLAG_HAS_ACKS            = 0x0004  # Bit 2: Piggybacked ACKs (1 byte count + N*4 bytes <I)
    FLAG_ON_CHANNEL          = 0x0008  # Bit 3: Addressed on channel (no footer, lookup by IP:Port)
    FLAG_IS_RELIABLE         = 0x0010  # Bit 4: Reliable message packet (requires seq_num)
    FLAG_HAS_FRAGMENTS       = 0x0020  # Bit 5: Bundle fragments (8 bytes: fragBegin 4B + fragEnd 4B)
    FLAG_HAS_SEQUENCE_NUMBER = 0x0040  # Bit 6: Packet sequence number (4 bytes uint32 <I)
    FLAG_INDEXED_CHANNEL     = 0x0080  # Bit 7: Indexed channel ID (4 bytes uint32 <I)
    FLAG_HAS_CHECKSUM        = 0x0100  # Bit 8: 32-bit XOR checksum (4 bytes uint32 <I)
    FLAG_CREATE_CHANNEL      = 0x0200  # Bit 9: Channel creation handshake

    ALL_SUPPORTED_MASKS = (
        FLAG_HAS_REQUESTS | FLAG_HAS_PIGGYBACKS | FLAG_HAS_ACKS |
        FLAG_ON_CHANNEL | FLAG_IS_RELIABLE | FLAG_HAS_FRAGMENTS |
        FLAG_HAS_SEQUENCE_NUMBER | FLAG_INDEXED_CHANNEL |
        FLAG_HAS_CHECKSUM | FLAG_CREATE_CHANNEL
    )


class PacketFramingError(ValueError):
    """Raised when incoming packet framing is invalid or malformed."""
    pass


class MercuryPacketParser:
    MIN_HEADER_SIZE = 2
    MAX_PACKET_SIZE = 2048

    @classmethod
    def pack(
        cls,
        payload: bytes,
        flags: int = 0,
        seq_num: Optional[int] = None,
        channel_id: Optional[int] = None,
        acks: Optional[List[int]] = None,
        piggyback: Optional[bytes] = None,
        fragments: Optional[Tuple[int, int]] = None,
        first_request_offset: Optional[int] = None,
        is_reliable: bool = False,
        is_create_channel: bool = False,
        is_on_channel: bool = False,
        with_checksum: bool = False
    ) -> bytearray:
        """
        Synthesizes a Mercury plaintext packet with footers assembled in forward order
        so they are parsed in reverse order from the tail.
        Forward Assembly Order:
        1. Request Offset (2B uint16 if FLAG_HAS_REQUESTS = 0x0001)
        2. Fragments (8B 2x uint32 if FLAG_HAS_FRAGMENTS = 0x0020)
        3. Sequence Number (4B uint32 if FLAG_HAS_SEQUENCE_NUMBER = 0x0040)
        4. Piggybacked ACKs (N*4B uint32 + 1B count if FLAG_HAS_ACKS = 0x0004)
        5. Indexed Channel ID (4B uint32 if FLAG_INDEXED_CHANNEL = 0x0080)
        6. Piggyback Bundle (M bytes data + 2B int16 len if FLAG_HAS_PIGGYBACKS = 0x0002)
        7. Checksum (4B placeholder if FLAG_HAS_CHECKSUM = 0x0100)
        """
        footers = bytearray()

        if is_reliable:
            flags |= MercuryPacketFlags.FLAG_IS_RELIABLE
        if is_create_channel:
            flags |= MercuryPacketFlags.FLAG_CREATE_CHANNEL
        if is_on_channel:
            flags |= MercuryPacketFlags.FLAG_ON_CHANNEL

        # 1. Request Offset (FLAG_HAS_REQUESTS = 0x0001)
        if first_request_offset is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_REQUESTS
            footers.extend(struct.pack("<H", first_request_offset))

        # 2. Bundle Fragments (FLAG_HAS_FRAGMENTS = 0x0020)
        if fragments is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_FRAGMENTS
            frag_begin, frag_end = fragments
            if frag_end < frag_begin:
                raise PacketFramingError(f"Illegal fragment range: fragEnd ({frag_end}) < fragBegin ({frag_begin})")
            footers.extend(struct.pack("<II", frag_begin, frag_end))

        # 3. Sequence Number (FLAG_HAS_SEQUENCE_NUMBER = 0x0040)
        if seq_num is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER
            footers.extend(struct.pack("<I", seq_num))

        # 4. Piggybacked ACKs (FLAG_HAS_ACKS = 0x0004)
        if acks is not None and len(acks) > 0:
            flags |= MercuryPacketFlags.FLAG_HAS_ACKS
            if len(acks) > 255:
                raise PacketFramingError("ACK count cannot exceed 255")
            for ack in acks:
                footers.extend(struct.pack("<I", ack))
            footers.append(len(acks))

        # 5. Indexed Channel ID (FLAG_INDEXED_CHANNEL = 0x0080)
        if channel_id is not None:
            flags |= MercuryPacketFlags.FLAG_INDEXED_CHANNEL
            footers.extend(struct.pack("<I", channel_id))

        # 6. Piggyback Bundle (FLAG_HAS_PIGGYBACKS = 0x0002)
        if piggyback is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_PIGGYBACKS
            p_len = len(piggyback)
            if p_len > 0x7FFF:
                raise PacketFramingError("Piggyback length exceeds maximum 32767 bytes")
            footers.extend(piggyback)
            footers.extend(struct.pack("<h", p_len))

        # 7. Checksum Placeholder (FLAG_HAS_CHECKSUM = 0x0100)
        if with_checksum:
            flags |= MercuryPacketFlags.FLAG_HAS_CHECKSUM
            footers.extend(b"\x00\x00\x00\x00")

        # Assemble: [Header: 2-byte Flags] [Payload] [Footers]
        buf = bytearray()
        buf.extend(struct.pack("<H", flags))
        buf.extend(payload)
        buf.extend(footers)

        if len(buf) > cls.MAX_PACKET_SIZE:
            raise PacketFramingError(f"Assembled packet size ({len(buf)}) exceeds max ({cls.MAX_PACKET_SIZE})")

        return buf

    @classmethod
    def unpack_footers(cls, plaintext_pkt: bytearray) -> Dict[str, Any]:
        """
        Parses Header Flags and unpacks footers backwards from tail.
        Note: If checksum is present, it must be verified and stripped BEFORE calling this,
        or checked as the first step of tail unwinding.
        """
        total_len = len(plaintext_pkt)
        if total_len < cls.MIN_HEADER_SIZE:
            raise PacketFramingError(f"Packet undersized: {total_len} bytes < {cls.MIN_HEADER_SIZE}")
        if total_len > cls.MAX_PACKET_SIZE:
            raise PacketFramingError(f"Packet oversized: {total_len} bytes > {cls.MAX_PACKET_SIZE}")

        # 1. Header Flags Word at Offset 0 (VA 0x100922894)
        flags = struct.unpack_from("<H", plaintext_pkt, 0)[0]
        if flags >= 0x0400:
            raise PacketFramingError(f"Nub::processFilteredPacket: bad flags 0x{flags:04x} >= 0x0400")

        unknown_flags = flags & ~MercuryPacketFlags.ALL_SUPPORTED_MASKS
        if unknown_flags != 0:
            raise PacketFramingError(f"Packet contains unsupported flag bits: 0x{unknown_flags:04x}")

        tail = total_len
        head = 2  # Payload starts at Offset 2

        # 2. Checksum (FLAG_HAS_CHECKSUM = 0x0100)
        has_checksum = bool(flags & MercuryPacketFlags.FLAG_HAS_CHECKSUM)
        checksum_val = None
        if has_checksum:
            if tail - head < 4:
                raise PacketFramingError("Not enough data for 4-byte checksum footer")
            tail -= 4
            checksum_val = struct.unpack_from("<I", plaintext_pkt, tail)[0]

        # 3. Piggybacked Bundle (FLAG_HAS_PIGGYBACKS = 0x0002)
        piggyback_bundle = None
        if flags & MercuryPacketFlags.FLAG_HAS_PIGGYBACKS:
            if tail - head < 2:
                raise PacketFramingError("Not enough data for piggyback length footer")
            tail -= 2
            p_len = struct.unpack_from("<h", plaintext_pkt, tail)[0]
            if p_len < 0:
                p_len = -p_len
            if tail - head < p_len:
                raise PacketFramingError(f"Not enough data for piggyback payload ({p_len}B)")
            tail -= p_len
            piggyback_bundle = bytes(plaintext_pkt[tail : tail + p_len])

        # 4. Indexed Channel ID (FLAG_INDEXED_CHANNEL = 0x0080)
        channel_id = None
        if flags & MercuryPacketFlags.FLAG_INDEXED_CHANNEL:
            if tail - head < 4:
                raise PacketFramingError("Not enough data for 4-byte channel ID footer")
            tail -= 4
            channel_id = struct.unpack_from("<I", plaintext_pkt, tail)[0]

        # 5. Piggybacked ACKs (FLAG_HAS_ACKS = 0x0004)
        acks = []
        if flags & MercuryPacketFlags.FLAG_HAS_ACKS:
            if tail - head < 1:
                raise PacketFramingError("Not enough data for ACK count footer")
            tail -= 1
            ack_count = plaintext_pkt[tail]
            if ack_count == 0:
                raise PacketFramingError("Packet with FLAG_HAS_ACKS had 0 acks")
            needed_bytes = ack_count * 4
            if tail - head < needed_bytes:
                raise PacketFramingError(f"Not enough data for {ack_count} ACKs ({needed_bytes}B)")
            tail -= needed_bytes
            for i in range(ack_count):
                ack_seq = struct.unpack_from("<I", plaintext_pkt, tail + i * 4)[0]
                acks.append(ack_seq)

        # 6. Sequence Number (FLAG_HAS_SEQUENCE_NUMBER = 0x0040)
        seq_num = None
        if flags & MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER:
            if tail - head < 4:
                raise PacketFramingError("Not enough data for sequence number footer")
            tail -= 4
            seq_num = struct.unpack_from("<I", plaintext_pkt, tail)[0]

        # 7. Reliability Check (FLAG_IS_RELIABLE = 0x0010)
        if flags & MercuryPacketFlags.FLAG_IS_RELIABLE:
            if seq_num is None:
                raise PacketFramingError("Nub::processFilteredPacket: illegal request for reliability without sequence number")

        # 8. Bundle Fragments (FLAG_HAS_FRAGMENTS = 0x0020)
        fragments = None
        if flags & MercuryPacketFlags.FLAG_HAS_FRAGMENTS:
            if tail - head < 8:
                raise PacketFramingError("Not enough data for 8-byte fragment footer")
            tail -= 8
            frag_begin, frag_end = struct.unpack_from("<II", plaintext_pkt, tail)
            if frag_end < frag_begin:
                raise PacketFramingError(f"Illegal fragment range: fragEnd ({frag_end}) < fragBegin ({frag_begin})")
            fragments = (frag_begin, frag_end)

        # 9. First Request Offset (FLAG_HAS_REQUESTS = 0x0001)
        first_request_offset = None
        if flags & MercuryPacketFlags.FLAG_HAS_REQUESTS:
            if tail - head < 2:
                raise PacketFramingError("Not enough data for request offset footer")
            tail -= 2
            first_request_offset = struct.unpack_from("<H", plaintext_pkt, tail)[0]

        # 10. Remaining bytes: Message Payload Bundle
        if tail < head:
            raise PacketFramingError("Corrupted packet: footers overlap header offset")
        payload = bytes(plaintext_pkt[head:tail])

        return {
            "flags": flags,
            "payload": payload,
            "has_checksum": has_checksum,
            "checksum": checksum_val,
            "seq_num": seq_num,
            "channel_id": channel_id,
            "acks": acks,
            "piggyback": piggyback_bundle,
            "fragments": fragments,
            "first_request_offset": first_request_offset,
            "is_reliable": bool(flags & MercuryPacketFlags.FLAG_IS_RELIABLE),
            "is_create_channel": bool(flags & MercuryPacketFlags.FLAG_CREATE_CHANNEL),
            "is_on_channel": bool(flags & MercuryPacketFlags.FLAG_ON_CHANNEL),
            "payload_length": len(payload)
        }
