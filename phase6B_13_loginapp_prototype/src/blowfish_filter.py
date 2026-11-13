"""
Blowfish Encryption Filter for BaseApp Address Handshake.

Implements Blowfish encryption/decryption for the LoginReply payload:
- Key Length: 56 bytes (448 bits).
- Block Size: 8 bytes (64 bits).
- Verifies input is an exact multiple of 8 bytes (matching native client tst w19, #7 assertion).
"""

from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class BlowfishFilterError(Exception):
    """Raised when Blowfish encryption or block validation fails."""
    pass


class BlowfishAddressFilter:
    """Handles symmetric Blowfish encryption and decryption for address payloads."""

    @classmethod
    def encrypt(cls, plaintext: bytes, session_key: bytes) -> bytes:
        """
        Encrypts an address block using the negotiated 56-byte session key.
        The plaintext must be an exact multiple of 8 bytes.
        """
        if len(session_key) != 56:
            raise BlowfishFilterError(f"Session key must be 56 bytes, got {len(session_key)}.")

        if len(plaintext) % 8 != 0:
            raise BlowfishFilterError(f"Plaintext length ({len(plaintext)}) is not a multiple of 8.")

        cipher = Cipher(algorithms.Blowfish(session_key), modes.ECB())
        encryptor = cipher.encryptor()
        return encryptor.update(plaintext) + encryptor.finalize()

    @classmethod
    def decrypt(cls, ciphertext: bytes, session_key: bytes) -> bytes:
        """
        Decrypts an encrypted address block using the 56-byte session key.
        The ciphertext must be an exact multiple of 8 bytes.
        """
        if len(session_key) != 56:
            raise BlowfishFilterError(f"Session key must be 56 bytes, got {len(session_key)}.")

        if len(ciphertext) % 8 != 0:
            raise BlowfishFilterError(f"Ciphertext length ({len(ciphertext)}) is not a multiple of 8.")

        cipher = Cipher(algorithms.Blowfish(session_key), modes.ECB())
        decryptor = cipher.decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize()
