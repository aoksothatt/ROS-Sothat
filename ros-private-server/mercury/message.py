"""
Mercury high-level message framing within bundle bodies.
Implements message ID extraction and variable/fixed length decoding.
"""

import struct
from typing import List, Optional, Tuple

from mercury.constants import (
    LENGTH_FIXED,
    LENGTH_VARIABLE_1,
    LENGTH_VARIABLE_2,
    LENGTH_VARIABLE_4,
)


class MercuryMessage:
    """Represents a single multiplexed message inside a Mercury bundle body."""

    def __init__(self, message_id: int, payload: bytes = b"", length_format: int = LENGTH_VARIABLE_1):
        if not (0 <= message_id <= 255):
            raise ValueError(f"message_id must be 0-255, got {message_id}")
        self.message_id = message_id
        self.payload = payload
        self.length_format = length_format

    def encode(self) -> bytes:
        """Serialize message ID, length prefix, and payload."""
        out = bytearray()
        out.append(self.message_id)

        if self.length_format == LENGTH_FIXED:
            pass  # Predefined length, no prefix
        elif self.length_format == LENGTH_VARIABLE_1:
            if len(self.payload) > 255:
                raise ValueError(f"Payload length {len(self.payload)} exceeds 1-byte prefix max (255)")
            out.append(len(self.payload))
        elif self.length_format == LENGTH_VARIABLE_2:
            if len(self.payload) > 65535:
                raise ValueError(f"Payload length {len(self.payload)} exceeds 2-byte prefix max (65535)")
            out.extend(struct.pack("<H", len(self.payload)))
        elif self.length_format == LENGTH_VARIABLE_4:
            out.extend(struct.pack("<I", len(self.payload)))
        else:
            raise ValueError(f"Unrecognized length_format: {self.length_format}")

        out.extend(self.payload)
        return bytes(out)

    @classmethod
    def decode_stream(
        cls,
        data: bytes,
        fixed_lengths: Optional[dict] = None
    ) -> List['MercuryMessage']:
        """
        Unpack bundled messages from datagram body bytes.
        fixed_lengths is an optional dict mapping message_id -> expected byte length.
        Defaults to LENGTH_VARIABLE_1 if not in fixed_lengths.
        """
        messages = []
        offset = 0
        fixed_map = fixed_lengths or {}

        while offset < len(data):
            msg_id = data[offset]
            offset += 1

            if msg_id in fixed_map:
                payload_len = fixed_map[msg_id]
                fmt = LENGTH_FIXED
            else:
                # Variable length (1-byte default)
                if offset >= len(data):
                    break
                payload_len = data[offset]
                offset += 1
                fmt = LENGTH_VARIABLE_1

            if offset + payload_len > len(data):
                # Truncated message in bundle
                break

            payload = data[offset:offset + payload_len]
            offset += payload_len
            messages.append(cls(message_id=msg_id, payload=payload, length_format=fmt))

        return messages
