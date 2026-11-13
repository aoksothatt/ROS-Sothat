"""
LogOnParams Serialization and Deserialization Specification.

Implements the verified native layout of LogOnParams:
1. LogOnType (uint8, 1B = 0x01)
2. Username (BigWorld string)
3. Password (BigWorld string, client salted with 'aec05336' and shifted by -1)
4. SessionKey (BigWorld string, length 56 + 56-byte key)
5. ClientNonce (16-byte raw block)
6. ClientFlags (uint32 LE, 4B)
"""

from dataclasses import dataclass
from typing import Tuple
import io
import struct

from .bundle_parser import encode_bw_string, decode_bw_string


PASSWORD_SALT_PREFIX = "aec05336"


class LogOnParamsError(Exception):
    """Raised when LogOnParams binary serialization or validation fails."""
    pass


def salt_password(plain_password: str) -> str:
    """
    Simulates the native client password preprocessing:
    Appends the user password to 'aec05336' with each character decremented by 1.
    """
    shifted = "".join(chr((ord(c) - 1) & 0xFFFF) for c in plain_password)
    return PASSWORD_SALT_PREFIX + shifted


def desalt_password(salted_password: str) -> str:
    """
    Reverses native client password preprocessing:
    Strips the 'aec05336' prefix and shifts each character back by +1.
    """
    if not salted_password.startswith(PASSWORD_SALT_PREFIX):
        # If client did not apply salt prefix, return as-is
        return salted_password

    body = salted_password[len(PASSWORD_SALT_PREFIX):]
    plain = "".join(chr((ord(c) + 1) & 0xFFFF) for c in body)
    return plain


@dataclass
class LogOnParams:
    """Represents deserialized authentication parameters from the client."""
    logon_type: int
    username: str
    password: str
    session_key: bytes
    client_nonce: bytes
    client_flags: int

    def serialize(self, apply_client_salt: bool = True) -> bytes:
        """
        Serializes LogOnParams into raw binary matching native client addToStream.
        """
        if len(self.session_key) != 56:
            raise LogOnParamsError(f"Session key must be exactly 56 bytes, got {len(self.session_key)}.")

        if len(self.client_nonce) != 16:
            raise LogOnParamsError(f"Client nonce must be exactly 16 bytes, got {len(self.client_nonce)}.")

        stream = io.BytesIO()

        # 1. LogOnType (1 byte uint8)
        stream.write(struct.pack('<B', self.logon_type & 0xFF))

        # 2. Username (BigWorld string)
        stream.write(encode_bw_string(self.username))

        # 3. Password (BigWorld string)
        wire_password = salt_password(self.password) if apply_client_salt else self.password
        stream.write(encode_bw_string(wire_password))

        # 4. SessionKey (BigWorld string: 1-byte length 56 + 56 raw bytes)
        stream.write(bytes([56]) + self.session_key)

        # 5. ClientNonce (16 bytes)
        stream.write(self.client_nonce)

        # 6. ClientFlags (uint32 LE, 4 bytes)
        stream.write(struct.pack('<I', self.client_flags))

        return stream.getvalue()

    @classmethod
    def deserialize(cls, data: bytes, reverse_client_salt: bool = True) -> "LogOnParams":
        """
        Deserializes binary data into LogOnParams, validating field constraints.
        """
        stream = io.BytesIO(data)

        # 1. LogOnType
        type_byte = stream.read(1)
        if not type_byte:
            raise LogOnParamsError("LogOnParams truncated: missing LogOnType byte.")
        logon_type = type_byte[0]

        # 2. Username
        username = decode_bw_string(stream)

        # 3. Password
        wire_password = decode_bw_string(stream)
        plain_password = desalt_password(wire_password) if reverse_client_salt else wire_password

        # 4. SessionKey
        len_byte = stream.read(1)
        if not len_byte:
            raise LogOnParamsError("LogOnParams truncated: missing SessionKey length.")
        key_len = len_byte[0]
        if key_len != 56:
            raise LogOnParamsError(f"Invalid Blowfish session key length: {key_len} (expected 56 bytes).")

        session_key = stream.read(key_len)
        if len(session_key) < key_len:
            raise LogOnParamsError(f"Truncated session key: expected {key_len} bytes, got {len(session_key)}.")

        # 5. ClientNonce
        client_nonce = stream.read(16)
        if len(client_nonce) < 16:
            raise LogOnParamsError(f"Truncated client nonce: expected 16 bytes, got {len(client_nonce)}.")

        # 6. ClientFlags
        flag_bytes = stream.read(4)
        if len(flag_bytes) < 4:
            raise LogOnParamsError(f"Truncated client flags: expected 4 bytes, got {len(flag_bytes)}.")
        client_flags = struct.unpack('<I', flag_bytes)[0]

        return cls(
            logon_type=logon_type,
            username=username,
            password=plain_password,
            session_key=session_key,
            client_nonce=client_nonce,
            client_flags=client_flags
        )
