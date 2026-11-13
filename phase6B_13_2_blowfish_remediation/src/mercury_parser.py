"""
Mercury Transport Protocol Framing and Footer Parser.

Implements the verified native Mercury UDP datagram framing:
- 2-byte header flags (Little-Endian uint16).
- Verified flag values: HAS_REQUESTS (0x0001), HAS_SEQUENCE_NUMBER (0x0040), HAS_ACKS (0x0004).
- 28-bit sequence number unpacking from datagram footers.
- Reverse footer parsing consistent with ARM64 native disassembly.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import struct


# Native Mercury Flag Constants (Verified in Phase 6.2B.8.3 - 6.2B.8.5)
FLAG_HAS_REQUESTS = 0x0001
FLAG_HAS_PIGGYBACKS = 0x0002
FLAG_HAS_ACKS = 0x0004
FLAG_ON_CHANNEL = 0x0008
FLAG_IS_RELIABLE = 0x0010
FLAG_HAS_FRAGMENTS = 0x0020
FLAG_HAS_SEQUENCE_NUMBER = 0x0040
FLAG_INDEXED_CHANNEL = 0x0080


class MercuryFramingError(Exception):
    """Raised when a Mercury datagram violates framing or footer specifications."""
    pass


@dataclass
class MercuryFrame:
    """Represents a parsed Mercury transport datagram."""
    flags: int
    payload: bytes
    seq_num: Optional[int] = None
    sub_seq: Optional[int] = None
    request_count: int = 0
    acks: List[int] = None

    def __post_init__(self):
        if self.acks is None:
            self.acks = []


class MercuryParser:
    """Encapsulates Mercury transport packing and unpacking routines."""

    @classmethod
    def unpack(cls, datagram: bytes) -> MercuryFrame:
        """
        Unpacks a raw Mercury UDP datagram into its header flags, bundle payload, and footers.
        """
        if len(datagram) < 2:
            raise MercuryFramingError(f"Datagram too short ({len(datagram)} bytes) for Mercury header.")

        flags = struct.unpack('<H', datagram[:2])[0]
        cursor = len(datagram)

        seq_num = None
        sub_seq = None
        request_count = 0
        acks: List[int] = []

        # Parse footers from tail forward based on active flags

        # 1. Request count (if HAS_REQUESTS is set)
        if flags & FLAG_HAS_REQUESTS:
            if cursor < 3: # 2B header + 1B request count
                raise MercuryFramingError("Datagram truncated: missing request count footer.")
            cursor -= 1
            request_count = datagram[cursor]

        # 2. Sequence number (if HAS_SEQUENCE_NUMBER is set)
        if flags & FLAG_HAS_SEQUENCE_NUMBER:
            if cursor < 6: # Need 4 bytes for sequence footer
                raise MercuryFramingError("Datagram truncated: missing sequence number footer.")
            cursor -= 4
            raw_seq = struct.unpack('<I', datagram[cursor:cursor + 4])[0]
            # 28-bit sequence number (upper 28 bits), 4-bit sub-seq (lower 4 bits)
            seq_num = (raw_seq >> 4) & 0x0FFFFFFF
            sub_seq = raw_seq & 0x0F

        # 3. ACKs (if HAS_ACKS is set)
        if flags & FLAG_HAS_ACKS:
            if cursor < 3:
                raise MercuryFramingError("Datagram truncated: missing ACK count footer.")
            cursor -= 1
            ack_count = datagram[cursor]
            needed = ack_count * 4
            if cursor < 2 + needed:
                raise MercuryFramingError(f"Datagram truncated: missing {ack_count} ACK integers.")
            cursor -= needed
            for i in range(ack_count):
                ack_val = struct.unpack('<I', datagram[cursor + i * 4:cursor + (i + 1) * 4])[0]
                acks.append((ack_val >> 4) & 0x0FFFFFFF)

        if cursor < 2:
            raise MercuryFramingError("Footers overlap Mercury header.")

        payload = datagram[2:cursor]
        return MercuryFrame(
            flags=flags,
            payload=payload,
            seq_num=seq_num,
            sub_seq=sub_seq,
            request_count=request_count,
            acks=acks
        )

    @classmethod
    def pack(
        cls,
        payload: bytes,
        flags: int = 0,
        seq_num: Optional[int] = None,
        sub_seq: int = 0,
        request_count: int = 0,
        acks: Optional[List[int]] = None
    ) -> bytes:
        """
        Packs payload bytes into a complete Mercury UDP datagram with appropriate header and footers.
        """
        active_flags = flags
        footers = bytearray()

        # Build footers in reverse order (to be unpacked backwards)
        if acks:
            active_flags |= FLAG_HAS_ACKS
            ack_bytes = bytearray()
            for ack in acks:
                raw_ack = ((ack & 0x0FFFFFFF) << 4)
                ack_bytes.extend(struct.pack('<I', raw_ack))
            ack_bytes.append(len(acks))
            footers.extend(ack_bytes)

        if seq_num is not None:
            active_flags |= FLAG_HAS_SEQUENCE_NUMBER
            raw_seq = ((seq_num & 0x0FFFFFFF) << 4) | (sub_seq & 0x0F)
            footers.extend(struct.pack('<I', raw_seq))

        if request_count > 0:
            active_flags |= FLAG_HAS_REQUESTS
            footers.append(request_count & 0xFF)

        header = struct.pack('<H', active_flags)
        return header + payload + bytes(footers)
