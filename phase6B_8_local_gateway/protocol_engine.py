"""
Mercury Protocol Engine Module
Phase 6.2B.8 - Research & Prototype Only

Integrates verified native cryptographic and packet framing pipelines:
- Blowfish Plaintext Block Chaining (PBC, C_i = E(P_i ^ P_{i-1}))
- Single-Byte Trailer Padding (wastage count, zero slack policy)
- Mercury 32-bit XOR Checksum (verified post-decryption)
- Reverse-Order Footer Unpacking

Reuses the audited Phase 6.2B.7.2 reference modules without modification.
"""

import sys
import os
import struct
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Cleanly add phase6B_7_2_synthetic_research to sys.path without modifying its contents
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent / "phase6B_7_2_synthetic_research")
if _PHASE6B_7_2_DIR not in sys.path:
    sys.path.insert(0, _PHASE6B_7_2_DIR)

from pbc_cipher import BlowfishPBC
from padding import SingleByteTrailerPadding
from checksum import MercuryChecksum
from packet_parser import MercuryPacketFlags, MercuryPacketParser, PacketFramingError


class ProtocolError(Exception):
    """Base class for all Mercury protocol errors."""
    pass


class PacketDecryptionError(ProtocolError):
    """Raised when ciphertext length is not block-aligned or decryption fails."""
    pass


class PaddingError(ProtocolError):
    """Raised when single-byte trailer wastage count is invalid (> 8 or 0)."""
    pass


class ChecksumError(ProtocolError):
    """Raised when post-decryption 32-bit XOR checksum fails."""
    pass


class MercuryProtocolEngine:
    """
    Engine executing the verified native cryptographic sequence for Mercury UDP datagrams.
    """
    def __init__(self, session_key: bytes):
        if not (4 <= len(session_key) <= 56):
            raise ValueError(f"Session key length {len(session_key)} invalid (must be 4..56 bytes)")
        self.session_key = session_key
        self.cipher = BlowfishPBC(session_key)

    def send_packet(
        self,
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
        enable_checksum: bool = True,
        slack_mode: str = "zero"
    ) -> bytes:
        """
        Executes verified send pipeline:
        Assembly -> Checksum Calculation & Injection -> Padding -> Blowfish PBC Encryption.
        """
        # 1. Assemble plaintext datagram with reverse footers and checksum placeholder
        raw_pkt = MercuryPacketParser.pack(
            payload=payload,
            flags=flags,
            seq_num=seq_num,
            channel_id=channel_id,
            acks=acks,
            piggyback=piggyback,
            fragments=fragments,
            first_request_offset=first_request_offset,
            is_reliable=is_reliable,
            is_create_channel=is_create_channel,
            is_on_channel=is_on_channel,
            with_checksum=enable_checksum
        )

        # 2. Inject 32-bit XOR checksum if enabled (VA 0x100922860 - 0x100922c84)
        if enable_checksum:
            MercuryChecksum.inject(raw_pkt)

        # 3. Apply Single-Byte Trailer Padding (wastage count) to 8-byte block multiple
        padded = SingleByteTrailerPadding.pad(bytes(raw_pkt), slack_mode=slack_mode)

        # 4. Encrypt with Blowfish PBC (zero IV per datagram)
        ciphertext = self.cipher.encrypt(padded)
        return ciphertext

    def receive_packet(self, datagram: bytes) -> Dict[str, Any]:
        """
        Executes verified receive pipeline:
        Blowfish PBC Decrypt -> Single-Byte Unpad -> Checksum Verify -> Footer Unpack.
        
        Strictly raises typed errors on any corruption and NEVER leaks unverified plaintext.
        """
        if not datagram:
            raise PacketDecryptionError("Received empty UDP datagram")

        if len(datagram) % BlowfishPBC.BLOCK_SIZE != 0:
            raise PacketDecryptionError(
                f"Datagram length ({len(datagram)}) not a multiple of Blowfish block size (8)"
            )

        # 1. Decrypt raw UDP datagram with Blowfish PBC
        try:
            decrypted_padded = self.cipher.decrypt(datagram)
        except Exception as e:
            raise PacketDecryptionError(f"Blowfish PBC decryption failed: {e}") from e

        # 2. Validate and strip single-byte trailer padding (wastage count)
        try:
            plaintext = SingleByteTrailerPadding.unpad(decrypted_padded)
        except Exception as e:
            raise PaddingError(f"Padding removal failed: {e}") from e

        # 3. Validate minimum packet size for Header Flags
        if len(plaintext) < MercuryPacketParser.MIN_HEADER_SIZE:
            raise PacketFramingError(f"Decrypted packet undersized ({len(plaintext)} bytes)")

        # 4. Check Flags for Checksum (FLAG_HAS_CHECKSUM = 0x0100)
        flags = struct.unpack_from("<H", plaintext, 0)[0]
        if flags >= 0x0400:
            raise PacketFramingError(f"Nub::processFilteredPacket: bad flags 0x{flags:04x} >= 0x0400")

        checksum_verified = False
        stored_csum = None
        computed_csum = None

        if flags & MercuryPacketFlags.FLAG_HAS_CHECKSUM:
            if len(plaintext) < MercuryChecksum.MIN_PACKET_WITH_CHECKSUM:
                raise PacketFramingError("Packet too short to contain 4-byte checksum footer")

            is_valid, computed, stored = MercuryChecksum.verify(plaintext)
            stored_csum = stored
            computed_csum = computed
            if not is_valid:
                raise ChecksumError(
                    f"Mercury checksum verification failed! "
                    f"Stored: 0x{stored:08x}, Computed: 0x{computed:08x}"
                )
            checksum_verified = True

        # 5. Unpack footers from plaintext
        unpacked = MercuryPacketParser.unpack_footers(bytearray(plaintext))
        unpacked["checksum_verified"] = checksum_verified
        unpacked["computed_checksum"] = computed_csum
        unpacked["stored_checksum"] = stored_csum
        unpacked["raw_plaintext_length"] = len(plaintext)

        return unpacked
