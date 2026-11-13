"""
Mercury reliable UDP datagram framing and serialization.
Replicates the wire format verified from neox::bwclient::Mercury::Nub::processFilteredPacket.
"""

import struct
import zlib
from typing import List, Optional, Tuple

from mercury.constants import (
    FLAG_RELIABLE,
    FLAG_HAS_PIGGYBACKS,
    FLAG_HAS_ACKS,
    FLAG_ONCE_OFF,
    FLAG_HAS_REQUESTS,
    FLAG_IS_FRAGMENT,
    FLAG_HAS_SEQUENCE_NUMBER,
    FLAG_INDEXED_CHANNEL,
    FLAG_HAS_CHECKSUM,
    FLAG_CREATE_CHANNEL,
    MAX_VALID_FLAGS,
    MIN_PACKET_SIZE,
)


class MalformedPacketError(Exception):
    """Raised when an incoming packet violates the Mercury protocol specification."""
    pass


class MercuryPacket:
    """
    Represents a verified BigWorld / NeoX Mercury UDP packet.
    
    Wire layout:
    +-----------------------------------------------------------+
    | Flags (uint16_t, little-endian)                           |
    +-----------------------------------------------------------+
    | Body: Message 1, Message 2, ...                           |
    +-----------------------------------------------------------+
    | [Footer] Sequence Number (uint32_t)                       |
    | [Footer] ACKs (uint32_t acks[count] + uint8_t count)      |
    | [Footer] Indexed Channel ID (uint32_t)                    |
    | [Footer] Checksum (uint32_t)                              |
    +-----------------------------------------------------------+
    Footers are packed from the back of the datagram.
    """

    def __init__(
        self,
        flags: int = 0,
        seq_num: Optional[int] = None,
        acks: Optional[List[int]] = None,
        indexed_channel_id: Optional[int] = None,
        body: bytes = b"",
        enable_checksum: bool = False
    ):
        self.flags = flags
        self.seq_num = seq_num
        self.acks = acks or []
        self.indexed_channel_id = indexed_channel_id
        self.body = body
        self.enable_checksum = enable_checksum

        # Automatically adjust flags based on supplied fields
        if self.seq_num is not None:
            self.flags |= FLAG_HAS_SEQUENCE_NUMBER
        if self.acks:
            self.flags |= FLAG_HAS_ACKS
        if self.indexed_channel_id is not None:
            self.flags |= FLAG_INDEXED_CHANNEL
        if self.enable_checksum:
            self.flags |= FLAG_HAS_CHECKSUM

    def is_reliable(self) -> bool:
        return bool(self.flags & FLAG_RELIABLE)

    def is_channel_create(self) -> bool:
        return bool(self.flags & FLAG_CREATE_CHANNEL)

    def encode(self) -> bytes:
        """Serialize into raw datagram bytes with header and ordered footers."""
        if self.flags > MAX_VALID_FLAGS:
            raise MalformedPacketError(f"Flags 0x{self.flags:04x} exceed MAX_VALID_FLAGS 0x{MAX_VALID_FLAGS:04x}")

        header = struct.pack("<H", self.flags)
        footers = bytearray()

        # Footer 1: Sequence Number (if present)
        if self.flags & FLAG_HAS_SEQUENCE_NUMBER:
            if self.seq_num is None:
                raise MalformedPacketError("FLAG_HAS_SEQUENCE_NUMBER set but seq_num is None")
            footers.extend(struct.pack("<I", self.seq_num))

        # Footer 2: ACKs (array of uint32 sequence numbers followed by 1 byte count)
        if self.flags & FLAG_HAS_ACKS:
            if not self.acks:
                raise MalformedPacketError("FLAG_HAS_ACKS set but no ACKs provided")
            if len(self.acks) > 255:
                raise MalformedPacketError(f"Cannot pack {len(self.acks)} ACKs (maximum 255 per packet)")
            for ack in self.acks:
                footers.extend(struct.pack("<I", ack))
            footers.append(len(self.acks))

        # Footer 3: Indexed Channel ID
        if self.flags & FLAG_INDEXED_CHANNEL:
            if self.indexed_channel_id is None:
                raise MalformedPacketError("FLAG_INDEXED_CHANNEL set but indexed_channel_id is None")
            footers.extend(struct.pack("<I", self.indexed_channel_id))

        packet_bytes = header + self.body + bytes(footers)

        # Footer 4: Checksum (appended at the very end if enabled)
        if self.flags & FLAG_HAS_CHECKSUM:
            csum = zlib.crc32(packet_bytes) & 0xFFFFFFFF
            packet_bytes += struct.pack("<I", csum)

        return packet_bytes

    @classmethod
    def decode(cls, data: bytes) -> 'MercuryPacket':
        """
        Deserialize raw datagram bytes into a MercuryPacket instance.
        Matches the exact verification and error conditions in processFilteredPacket.
        """
        if len(data) < MIN_PACKET_SIZE:
            raise MalformedPacketError(f"received undersize packet ({len(data)} bytes)")

        flags = struct.unpack_from("<H", data, 0)[0]
        if flags > MAX_VALID_FLAGS:
            raise MalformedPacketError(f"received packet with bad flags 0x{flags:x}")

        tail = len(data)
        checksum_val: Optional[int] = None

        # Checksum footer check
        if flags & FLAG_HAS_CHECKSUM:
            if tail < 6:  # 2 flags + 4 checksum
                raise MalformedPacketError(f"Packet too short ({tail} bytes) for checksum!")
            tail -= 4
            checksum_val = struct.unpack_from("<I", data, tail)[0]
            calculated_csum = zlib.crc32(data[:tail]) & 0xFFFFFFFF
            if calculated_csum != checksum_val:
                raise MalformedPacketError(
                    f"Packet (flags 0x{flags:x}, size {len(data)}) failed checksum "
                    f"(wanted 0x{checksum_val:08x}, got 0x{calculated_csum:08x})"
                )

        # Indexed Channel footer check
        indexed_channel_id: Optional[int] = None
        if flags & FLAG_INDEXED_CHANNEL:
            if tail - 2 < 4:
                raise MalformedPacketError(f"Not enough data for indexed channel footer ({tail - 2} bytes left)")
            tail -= 4
            indexed_channel_id = struct.unpack_from("<I", data, tail)[0]

        # ACKs footer check
        acks: List[int] = []
        if flags & FLAG_HAS_ACKS:
            if tail - 2 < 1:
                raise MalformedPacketError(f"Not enough data for ack count footer ({tail - 2} bytes left)")
            tail -= 1
            ack_count = data[tail]
            if ack_count == 0:
                raise MalformedPacketError("Packet with FLAG_HAS_ACKS had 0 acks")
            
            bytes_needed = ack_count * 4
            if tail - 2 < bytes_needed:
                raise MalformedPacketError(
                    f"Not enough footers for {ack_count} acks "
                    f"(have {tail - 2} bytes but need {bytes_needed})"
                )
            
            tail -= bytes_needed
            for i in range(ack_count):
                ack_seq = struct.unpack_from("<I", data, tail + (i * 4))[0]
                acks.append(ack_seq)

        # Sequence Number footer check
        seq_num: Optional[int] = None
        if flags & FLAG_HAS_SEQUENCE_NUMBER:
            if tail - 2 < 4:
                raise MalformedPacketError(f"Not enough data for sequence number footer ({tail - 2} bytes left)")
            tail -= 4
            seq_num = struct.unpack_from("<I", data, tail)[0]

        # Remaining bytes between header (offset 2) and tail belong to body
        if tail < 2:
            raise MalformedPacketError("Corrupted packet length during footer parsing")

        body = data[2:tail]

        return cls(
            flags=flags,
            seq_num=seq_num,
            acks=acks,
            indexed_channel_id=indexed_channel_id,
            body=body,
            enable_checksum=bool(flags & FLAG_HAS_CHECKSUM)
        )
