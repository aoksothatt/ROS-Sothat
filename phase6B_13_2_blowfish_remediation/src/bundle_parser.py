"""
BigWorld RPC Bundle Parser and Serializer.

Implements BigWorld bundle framing:
- Message ID (uint8).
- Variable-length message headers (1B, 2B uint16 LE).
- 4-byte correlation Request ID.
- BigWorld compact string encoding (1-byte or 4-byte prefix).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import io
import struct


# Special BigWorld Reply Message ID
BIGWORLD_REPLY_MSG_ID = 0xFF


class BundleParsingError(Exception):
    """Raised when a BigWorld bundle payload cannot be demuxed."""
    pass


def encode_bw_string(text: str) -> bytes:
    """
    Serializes a string using BigWorld variable-length prefix rules:
    - If len < 255: 1 byte uint8 length followed by UTF-8 bytes.
    - If len >= 255: 0xFF byte, 3 bytes uint24 LE length, followed by UTF-8 bytes.
    """
    encoded = text.encode('utf-8')
    length = len(encoded)
    if length < 0xFF:
        return bytes([length]) + encoded
    else:
        prefix = struct.pack('<B', 0xFF) + struct.pack('<I', length)[:3]
        return prefix + encoded


def decode_bw_string(stream: io.BytesIO) -> str:
    """
    Deserializes a BigWorld variable-length string from a stream.
    """
    prefix = stream.read(1)
    if not prefix:
        raise BundleParsingError("Unexpected EOF while reading BigWorld string length prefix.")

    first_byte = prefix[0]
    if first_byte < 0xFF:
        length = first_byte
    else:
        len_bytes = stream.read(3)
        if len(len_bytes) < 3:
            raise BundleParsingError("Unexpected EOF while reading BigWorld uint24 string length.")
        length = struct.unpack('<I', len_bytes + b'\x00')[0]

    raw_data = stream.read(length)
    if len(raw_data) < length:
        raise BundleParsingError(f"Unexpected EOF: expected {length} bytes, read {len(raw_data)} bytes.")

    return raw_data.decode('utf-8', errors='replace')


@dataclass
class BigWorldMessage:
    """Represents a single BigWorld RPC message unpacked from a bundle."""
    message_id: int
    length: int
    request_id: Optional[int]
    body: bytes


class BundleParser:
    """Parses and serializes BigWorld RPC bundles."""

    @classmethod
    def unpack_login_request(cls, bundle_data: bytes) -> BigWorldMessage:
        """
        Unpacks a LoginInterface::login request message from raw bundle bytes.
        Expected format:
        [MsgID: 1B (0x00)] [Length: 2B LE] [RequestID: 4B LE] [Body: Length - 4 bytes]
        """
        if len(bundle_data) < 7: # 1B + 2B + 4B = 7B minimum header
            raise BundleParsingError(f"Bundle too short ({len(bundle_data)} bytes) for login request.")

        msg_id, declared_len = struct.unpack('<BH', bundle_data[:3])
        if msg_id != 0x00:
            raise BundleParsingError(f"Expected LoginInterface message ID 0x00, got 0x{msg_id:02x}.")

        request_id = struct.unpack('<I', bundle_data[3:7])[0]

        # In BigWorld Mercury, declared_len represents body length including Request ID (4B)
        # Verify packet contains at least the declared length
        expected_total = 3 + declared_len
        if len(bundle_data) < expected_total:
            raise BundleParsingError(
                f"Bundle truncated: declared {declared_len} bytes (total {expected_total}), have {len(bundle_data)}."
            )

        body = bundle_data[7:expected_total]
        return BigWorldMessage(
            message_id=msg_id,
            length=declared_len,
            request_id=request_id,
            body=body
        )

    @classmethod
    def pack_reply(cls, request_id: int, payload: bytes) -> bytes:
        """
        Constructs a BigWorld reply bundle for a correlated Request ID.
        Format:
        [ReplyMsgID: 0xFF] [Length: 2B LE] [RequestID: 4B LE] [Payload]
        """
        total_len = 4 + len(payload) # RequestID (4B) + Payload
        header = struct.pack('<BHI', BIGWORLD_REPLY_MSG_ID, total_len, request_id)
        return header + payload
