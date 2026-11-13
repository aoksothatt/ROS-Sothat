"""
Mercury 32-bit XOR Checksum Reference Module
Phase 6.2B.7.2 - Research & Verification

Derived from native NetEase Rules of Survival (iOS Mach-O ARM64) disassembly:
- neox::bwclient::Mercury::Nub::processFilteredPacket (VA 0x100922860 - 0x100922c84):
    0x100922970: tbnz  w8, #8, #0x1009229d0    ; FLAG_HAS_CHECKSUM = 0x0100
    0x1009229d0: cmp   w9, #5                  ; Minimum length check (>= 6 bytes)
    0x100922a38: sub   w9, w9, #4              ; Remaining length -= 4
    0x100922a4c: ldr   w11, [x10, #0x60]!      ; w11 = stored checksum from tail
    0x100922a54: str   wzr, [x10]              ; *** ZERO CHECKSUM FIELD IN-PLACE ***
    ; SIMD NEON Loop (VA 0x100922bfc - 0x100922c28):
    ;   ldp q2, q3 -> eor v0.16b, v2.16b -> horizontal fold -> w22
    ; Scalar Fallback Loop (VA 0x100922c34 - 0x100922c40):
    ;   0x100922c34: ldr w13, [x12], #4
    ;   0x100922c38: eor w22, w13, w22
    0x100922c44: str   w11, [x10]              ; *** RESTORE STORED CHECKSUM ***
    0x100922c48: cmp   w22, w11                ; Compare computed sum vs stored
    ; Error branch if != : "Packet (flags %hx, size %d) failed checksum (wanted %08x, got %08x)"

Properties:
- Algorithm: 32-bit bitwise XOR summation over all dwords.
- Width: 32 bits (uint32_t).
- Endianness: Little-endian (<I).
- Range: Offset 0 (Flags word) through entire packet body and all preceding footers.
- In-place Zeroing: The 4-byte checksum field is zeroed during calculation so X ^ 0 = X.
- Timing: Verified AFTER Blowfish decryption in Nub::processFilteredPacket.
"""

import struct
from typing import Tuple, Optional


class MercuryChecksum:
    CHECKSUM_SIZE = 4
    MIN_PACKET_WITH_CHECKSUM = 6  # 2 bytes header flags + 4 bytes checksum

    @classmethod
    def calculate(cls, packet: bytes, checksum_offset: Optional[int] = None) -> int:
        """
        Calculates the 32-bit XOR checksum over the packet bytes.
        The 4-byte checksum field (at checksum_offset or at packet tail) is zeroed.
        
        Args:
            packet: raw packet bytes
            checksum_offset: byte offset of the 4-byte checksum field (defaults to len - 4)
        """
        pkt_len = len(packet)
        if pkt_len < cls.MIN_PACKET_WITH_CHECKSUM:
            raise ValueError(
                f"Packet too short ({pkt_len} bytes) for checksum! "
                f"Minimum required is {cls.MIN_PACKET_WITH_CHECKSUM} bytes."
            )

        if checksum_offset is None:
            checksum_offset = pkt_len - cls.CHECKSUM_SIZE
            
        if not (0 <= checksum_offset <= pkt_len - cls.CHECKSUM_SIZE):
            raise ValueError(f"Invalid checksum offset: {checksum_offset}")

        # Create mutable copy to zero out checksum field in-place
        buf = bytearray(packet)
        struct.pack_into("<I", buf, checksum_offset, 0)

        # Handle incomplete dwords:
        # In native code, packets are dword-aligned. If length is not a multiple of 4,
        # zero-padding to the next 4-byte boundary models the zeroed slack.
        pad_remainder = len(buf) % 4
        if pad_remainder != 0:
            buf.extend(bytes(4 - pad_remainder))

        checksum = 0
        for offset in range(0, len(buf), 4):
            dword = struct.unpack_from("<I", buf, offset)[0]
            checksum ^= dword

        return checksum & 0xFFFFFFFF

    @classmethod
    def inject(cls, packet: bytearray, checksum_offset: Optional[int] = None) -> bytearray:
        """
        Calculates the checksum with the checksum field zeroed, then writes
        the computed 32-bit little-endian checksum into the packet.
        """
        if checksum_offset is None:
            checksum_offset = len(packet) - cls.CHECKSUM_SIZE
            
        csum = cls.calculate(bytes(packet), checksum_offset=checksum_offset)
        struct.pack_into("<I", packet, checksum_offset, csum)
        return packet

    @classmethod
    def verify(cls, packet: bytes, checksum_offset: Optional[int] = None) -> Tuple[bool, int, int]:
        """
        Verifies checksum on an incoming decrypted packet.
        Returns (is_valid, computed_checksum, stored_checksum).
        """
        pkt_len = len(packet)
        if pkt_len < cls.MIN_PACKET_WITH_CHECKSUM:
            return False, 0, 0

        if checksum_offset is None:
            checksum_offset = pkt_len - cls.CHECKSUM_SIZE

        stored_checksum = struct.unpack_from("<I", packet, checksum_offset)[0]
        computed_checksum = cls.calculate(packet, checksum_offset=checksum_offset)

        is_valid = (computed_checksum == stored_checksum)
        return is_valid, computed_checksum, stored_checksum
