"""
Combined Mercury Encryption, Padding & Checksum Pipeline
Phase 6.2B.7.2 - Research & Verification

Implements the verified native sequence:
Sender Side:
  1. Construct Mercury datagram: [Flags (uint16)] [Payload] [Optional Footers]
  2. If FLAG_HAS_CHECKSUM: append 4 zero bytes, compute 32-bit XOR sum, write checksum into tail
  3. Apply Single-Byte Trailer padding (wastage count) to multiple of 8 bytes
  4. Apply Blowfish Plaintext Block Chaining (PBC) with zero IV

Receiver Side (reverses native Nub & EncryptionFilter flow):
  1. Decrypt raw UDP datagram with Blowfish PBC (zero IV per datagram)
  2. Validate single-byte trailer wastage count (1 <= L <= 8) and truncate padding
  3. Pass decrypted plaintext to Mercury packet processor:
     - Read Flags at offset 0
     - If FLAG_HAS_CHECKSUM (0x0100):
         - Read checksum from last 4 bytes
         - Zero checksum field in-place
         - Compute 32-bit XOR sum across entire datagram
         - Compare computed vs stored checksum
         - Truncate 4-byte checksum footer
  4. Unpack reverse footers from tail:
     - Piggybacks (0x0002)
     - Indexed Channel ID (0x0080)
     - Piggybacked ACKs (0x0008)
     - Sequence Number (0x0004)
     - Request / Fragment Offset (0x0040)
  5. Extract recovered message bundle payload
"""

import struct
from typing import Optional, List, Dict, Any, Tuple
from pbc_cipher import BlowfishPBC
from padding import SingleByteTrailerPadding
from checksum import MercuryChecksum


class MercuryPacketFlags:
    FLAG_CREATE_CHANNEL      = 0x0001
    FLAG_HAS_PIGGYBACKS      = 0x0002
    FLAG_HAS_SEQUENCE_NUMBER = 0x0004
    FLAG_HAS_ACKS            = 0x0008
    FLAG_ON_CHANNEL          = 0x0020
    FLAG_HAS_REQUESTS        = 0x0040
    FLAG_INDEXED_CHANNEL     = 0x0080
    FLAG_HAS_CHECKSUM        = 0x0100


class MercurySyntheticPipeline:
    """
    Simulates the verified end-to-end cryptographic and framing pipeline
    between the NetEase client and our private server gateway.
    """
    def __init__(self, session_key: bytes):
        self.session_key = session_key
        self.cipher = BlowfishPBC(session_key)

    def assemble_plaintext_packet(
        self,
        payload: bytes,
        flags: int = 0,
        seq_num: Optional[int] = None,
        channel_id: Optional[int] = None,
        acks: Optional[List[int]] = None,
        piggyback: Optional[bytes] = None,
        first_request_offset: Optional[int] = None,
        enable_checksum: bool = True
    ) -> bytearray:
        """
        Constructs a complete plaintext Mercury packet with reverse footers
        and optional 32-bit XOR checksum.
        """
        footers = bytearray()

        # Footers are unpacked in reverse order:
        # Request offset -> SeqNum -> ACKs -> Channel ID -> Piggyback -> Checksum
        # Therefore, they are appended in forward order:
        if first_request_offset is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_REQUESTS
            footers.extend(struct.pack("<H", first_request_offset))

        if seq_num is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER
            footers.extend(struct.pack("<I", seq_num))

        if acks is not None and len(acks) > 0:
            flags |= MercuryPacketFlags.FLAG_HAS_ACKS
            if len(acks) > 255:
                raise ValueError("ACK count cannot exceed 255")
            for ack in acks:
                footers.extend(struct.pack("<I", ack))
            footers.append(len(acks))

        if channel_id is not None:
            flags |= MercuryPacketFlags.FLAG_INDEXED_CHANNEL
            footers.extend(struct.pack("<I", channel_id))

        if piggyback is not None:
            flags |= MercuryPacketFlags.FLAG_HAS_PIGGYBACKS
            p_len = len(piggyback)
            if p_len > 0x7FFF:
                raise ValueError("Piggyback length too large")
            # In BigWorld, positive length indicates piggyback length
            footers.extend(piggyback)
            footers.extend(struct.pack("<h", p_len))

        # Checksum field is the absolute outermost footer at the tail
        if enable_checksum:
            flags |= MercuryPacketFlags.FLAG_HAS_CHECKSUM
            # Append 4 zero bytes as placeholder for checksum
            footers.extend(b"\x00\x00\x00\x00")

        # Assemble: [Flags 16-bit] [Payload Body] [Footers]
        packet = bytearray()
        packet.extend(struct.pack("<H", flags))
        packet.extend(payload)
        packet.extend(footers)

        # Calculate and inject checksum if enabled
        if enable_checksum:
            MercuryChecksum.inject(packet)

        return packet

    def send_pipeline(
        self,
        payload: bytes,
        flags: int = 0,
        seq_num: Optional[int] = None,
        channel_id: Optional[int] = None,
        acks: Optional[List[int]] = None,
        piggyback: Optional[bytes] = None,
        first_request_offset: Optional[int] = None,
        enable_checksum: bool = True,
        slack_mode: str = "zero"
    ) -> bytes:
        """
        Executes the full sending pipeline:
        Assembly -> Checksum -> Single-Byte Padding -> Blowfish PBC Encryption.
        """
        # 1. Assemble plaintext packet with checksum
        plaintext_pkt = self.assemble_plaintext_packet(
            payload=payload,
            flags=flags,
            seq_num=seq_num,
            channel_id=channel_id,
            acks=acks,
            piggyback=piggyback,
            first_request_offset=first_request_offset,
            enable_checksum=enable_checksum
        )

        # 2. Pad to multiple of 8 with single-byte trailer
        padded_pkt = SingleByteTrailerPadding.pad(bytes(plaintext_pkt), slack_mode=slack_mode)

        # 3. Encrypt with Blowfish PBC (zero IV per datagram)
        ciphertext = self.cipher.encrypt(padded_pkt)
        return ciphertext

    def receive_pipeline(self, datagram: bytes) -> Dict[str, Any]:
        """
        Executes the full receiving pipeline:
        Blowfish PBC Decryption -> Single-Byte Unpadding -> Checksum Verification -> Reverse Footer Unpacking.
        """
        # 1. Decrypt raw UDP datagram using Blowfish PBC
        decrypted_padded = self.cipher.decrypt(datagram)

        # 2. Validate and remove single-byte trailer padding
        plaintext_pkt = bytearray(SingleByteTrailerPadding.unpad(decrypted_padded))

        # 3. Validate minimum packet size for flags word
        if len(plaintext_pkt) < 2:
            raise ValueError("Nub::processFilteredPacket: received undersize packet")

        # 4. Read Header Flags at Offset 0
        flags = struct.unpack_from("<H", plaintext_pkt, 0)[0]
        if flags >= 0x0400:
            raise ValueError(f"Nub::processFilteredPacket: received packet with bad flags 0x{flags:x}")

        # 5. Checksum verification (if FLAG_HAS_CHECKSUM = 0x0100)
        has_checksum = bool(flags & MercuryPacketFlags.FLAG_HAS_CHECKSUM)
        checksum_val = None
        if has_checksum:
            if len(plaintext_pkt) < 6:
                raise ValueError("Nub::processFilteredPacket: Packet too short for checksum!")
            is_valid, computed, stored = MercuryChecksum.verify(bytes(plaintext_pkt))
            if not is_valid:
                raise ValueError(
                    f"Nub::processFilteredPacket: Packet (flags 0x{flags:x}, size {len(plaintext_pkt)}) "
                    f"failed checksum (wanted 0x{stored:08x}, got 0x{computed:08x})"
                )
            checksum_val = stored
            # Truncate 4-byte checksum footer from tail
            plaintext_pkt = plaintext_pkt[:-4]

        # 6. Unpack reverse footers from tail
        tail = len(plaintext_pkt)
        piggyback_data = None
        channel_id = None
        acks_list = None
        seq_num = None
        first_req_offset = None

        # 6a. Piggybacks (FLAG_HAS_PIGGYBACKS = 0x0002)
        if flags & MercuryPacketFlags.FLAG_HAS_PIGGYBACKS:
            if tail < 4:
                raise ValueError("Nub::processFilteredPacket: Not enough data for piggyback length")
            p_len = struct.unpack_from("<h", plaintext_pkt, tail - 2)[0]
            tail -= 2
            if p_len < 0:
                p_len = -p_len
            if tail - 2 < p_len:
                raise ValueError("Nub::processFilteredPacket: Packet too small to contain piggyback message")
            piggyback_data = bytes(plaintext_pkt[tail - p_len : tail])
            tail -= p_len

        # 6b. Indexed Channel ID (FLAG_INDEXED_CHANNEL = 0x0080)
        if flags & MercuryPacketFlags.FLAG_INDEXED_CHANNEL:
            if tail < 6:
                raise ValueError("Nub::processFilteredPacket: Not enough data for indexed channel footer")
            channel_id = struct.unpack_from("<I", plaintext_pkt, tail - 4)[0]
            tail -= 4

        # 6c. Piggybacked ACKs (FLAG_HAS_ACKS = 0x0008)
        if flags & MercuryPacketFlags.FLAG_HAS_ACKS:
            if tail < 3:
                raise ValueError("Nub::processFilteredPacket: Not enough data for ack count footer")
            ack_count = plaintext_pkt[tail - 1]
            tail -= 1
            if ack_count == 0:
                raise ValueError("Nub::processFilteredPacket: Packet with FLAG_HAS_ACKS had 0 acks")
            needed_bytes = ack_count * 4
            if tail - 2 < needed_bytes:
                raise ValueError("Nub::processFilteredPacket: Not enough footers for acks")
            acks_list = []
            for i in range(ack_count):
                ack_val = struct.unpack_from("<I", plaintext_pkt, tail - (ack_count - i) * 4)[0]
                acks_list.append(ack_val)
            tail -= needed_bytes

        # 6d. Sequence Number (FLAG_HAS_SEQUENCE_NUMBER = 0x0004)
        if flags & MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER:
            if tail < 6:
                raise ValueError("Nub::processFilteredPacket: Not enough data for sequence number footer")
            seq_num = struct.unpack_from("<I", plaintext_pkt, tail - 4)[0]
            tail -= 4

        # 6e. First Request Offset (FLAG_HAS_REQUESTS = 0x0040)
        if flags & MercuryPacketFlags.FLAG_HAS_REQUESTS:
            if tail < 4:
                raise ValueError("Nub::processFilteredPacket: Not enough data for request offset footer")
            first_req_offset = struct.unpack_from("<H", plaintext_pkt, tail - 2)[0]
            tail -= 2

        # 7. Remaining bytes between Offset 2 and tail constitute the bundle payload
        if tail < 2:
            raise ValueError("Nub::processFilteredPacket: Corrupted bundle header offset")
        payload = bytes(plaintext_pkt[2:tail])

        return {
            "flags": flags,
            "payload": payload,
            "checksum": checksum_val,
            "sequence_number": seq_num,
            "channel_id": channel_id,
            "acks": acks_list,
            "piggyback": piggyback_data,
            "first_request_offset": first_req_offset,
            "raw_recovered_len": len(plaintext_pkt)
        }
