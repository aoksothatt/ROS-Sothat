"""
Single-Byte Trailer Padding Reference Module ("Wastage Count")
Phase 6.2B.7.2 - Research & Verification

Derived from native NetEase Rules of Survival (iOS Mach-O ARM64) disassembly:
- neox::bwclient::Mercury::EncryptionFilter::send (VA 0x10091c7ac - 0x10091c7c4):
    0x10091c7ac: and  w8, w24, #7          ; raw_len % 8
    0x10091c7b0: mov  w9, #8
    0x10091c7b4: sub  w8, w9, w8           ; pad_len = 8 - (raw_len % 8) [1..8]
    0x10091c7b8: add  x24, x8, x24         ; padded_len = raw_len + pad_len
    0x10091c7c0: add  x9, x24, x23         ; buffer + padded_len
    0x10091c7c4: sturb w8, [x9, #-1]       ; store pad_len ONLY to last byte!
- neox::bwclient::Mercury::EncryptionFilter::recv (VA 0x10091c9dc - 0x10091ca2c):
    0x10091c9dc: ldrb w21, [x10, #0x5f]    ; load last byte as pad_len
    0x10091c9e0: cmp  w21, #8              ; pad_len <= 8
    0x10091c9e4: ccmp w9, w21, #0, ls      ; total_len >= pad_len
    0x10091c9e8: b.hs #0x10091ca24         ; success branch -> packet_len -= pad_len
    ; else error: "EncryptionFilter::recv: Dropping packet from %s due to illegal wastage count (%d)"

Properties:
- Padding length is always in [1, 8].
- An exact multiple of 8 receives a full additional 8-byte block ending in 0x08.
- Preceding slack bytes are NOT checked by the receiver.
"""

import os
from typing import Optional


class SingleByteTrailerPadding:
    BLOCK_SIZE = 8

    @classmethod
    def calculate_pad_length(cls, raw_len: int) -> int:
        """Computes native padding length: 8 - (raw_len % 8). Result is always 1 to 8."""
        return cls.BLOCK_SIZE - (raw_len % cls.BLOCK_SIZE)

    @classmethod
    def pad(cls, data: bytes, slack_mode: str = "zero", custom_slack: Optional[bytes] = None) -> bytes:
        """
        Pads plaintext to a multiple of 8 bytes with a single-byte trailer.
        
        Args:
            data: raw plaintext bytes
            slack_mode:
                "zero": slack bytes are filled with 0x00 (matches ANSI X9.23 format)
                "random": slack bytes are pseudo-random (models uninitialized pool memory)
                "pkcs7": slack bytes are flooded with pad_len (matches PKCS#7 format)
                "custom": slack bytes supplied via custom_slack
            custom_slack: optional bytes to use for slack when slack_mode == "custom"
        """
        raw_len = len(data)
        pad_len = cls.calculate_pad_length(raw_len)
        slack_len = pad_len - 1

        if slack_mode == "zero":
            slack_bytes = bytes(slack_len)
        elif slack_mode == "random":
            # Deterministic non-zero pattern for repeatable testing
            slack_bytes = bytes([(0xAA + i) & 0xFF for i in range(slack_len)])
        elif slack_mode == "pkcs7":
            slack_bytes = bytes([pad_len] * slack_len)
        elif slack_mode == "custom":
            if custom_slack is None or len(custom_slack) != slack_len:
                raise ValueError(f"custom_slack must be exactly {slack_len} bytes")
            slack_bytes = custom_slack
        else:
            raise ValueError(f"Unknown slack_mode: {slack_mode}")

        trailer_byte = bytes([pad_len])
        padded = data + slack_bytes + trailer_byte
        assert len(padded) % cls.BLOCK_SIZE == 0
        return padded

    @classmethod
    def unpad(cls, data: bytes) -> bytes:
        """
        Validates and removes single-byte trailer padding.
        Input length MUST be a positive multiple of BLOCK_SIZE (8 bytes).

        Follows native assembly checks at VA 0x10091c920 and 0x10091c9dc:
        1. Length % 8 == 0
        2. Read last byte as pad_len
        3. 1 <= pad_len <= 8
        4. total_len >= pad_len
        """
        total_len = len(data)
        if total_len % cls.BLOCK_SIZE != 0:
            raise ValueError(
                f"EncryptionFilter::decrypt: Input stream size ({total_len}) "
                f"is not a multiple of the block size ({cls.BLOCK_SIZE})"
            )
        if total_len == 0:
            raise ValueError(
                "EncryptionFilter::recv: Dropping packet due to empty ciphertext stream"
            )

        trailer = data[-1]
        
        # Native check: cmp w21, #8; ccmp w9, w21, #0, ls
        # In native code, wastage count 0 or > 8 is illegal.
        if trailer == 0 or trailer > cls.BLOCK_SIZE or total_len < trailer:
            raise ValueError(
                f"EncryptionFilter::recv: Dropping packet due to illegal wastage count ({trailer})"
            )

        return data[:-trailer]
