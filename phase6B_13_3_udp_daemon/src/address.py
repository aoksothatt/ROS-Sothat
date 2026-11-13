"""
Mercury Address Struct Representation and Binary Serialization.

Implements the verified 20-byte Mercury::Address structure:
- IPv4 Address: 4 bytes uint32 (Network byte order / Big-Endian).
- UDP Port: 2 bytes uint16 (Network byte order / Big-Endian).
- Internal Padding: 14 bytes (struct alignment).
- Blowfish Block Alignment: Padded to 24 bytes (3 x 8-byte blocks).
"""

from dataclasses import dataclass
import socket
import struct


@dataclass
class MercuryAddress:
    """Represents a network endpoint address for BaseApp."""
    ip: str
    port: int

    def pack_20b(self) -> bytes:
        """Serializes endpoint into raw 20-byte Mercury::Address struct."""
        ip_bytes = socket.inet_aton(self.ip) # 4 bytes in network byte order
        port_bytes = struct.pack('!H', self.port) # 2 bytes in network byte order
        padding = b'\x00' * 14 # 14 bytes struct alignment
        return ip_bytes + port_bytes + padding

    def pack_24b(self) -> bytes:
        """
        Serializes endpoint into 24 bytes (padded to multiple of 8 for Blowfish).
        """
        raw_20 = self.pack_20b()
        return raw_20 + (b'\x00' * 4) # 4 bytes zero padding to reach 24 bytes

    @classmethod
    def unpack(cls, data: bytes) -> "MercuryAddress":
        """
        Deserializes a 20-byte or 24-byte block into a MercuryAddress instance.
        """
        if len(data) < 6:
            raise ValueError(f"Address data too short: {len(data)} bytes (minimum 6).")

        ip = socket.inet_ntoa(data[:4])
        port = struct.unpack('!H', data[4:6])[0]
        return cls(ip=ip, port=port)
