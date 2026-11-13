"""
Blowfish Encryption Filter for BigWorld Mercury Protocol Handshake.

Remediated in Phase 6.2B.13.2 based on native iOS Mach-O disassembly:
- Disassembly Citations:
    * EncryptionFilter::send (encrypt) at VA 0x10091c7f0 - 0x10091c834
    * EncryptionFilter::decrypt at VA 0x10091ca8c - 0x10091cb80
    * LoginHandler address decryption at VA 0x1008a85f0 - 0x1008a862c
- BigWorld Technology 2.0.1 Reference:
    * encryption_filter.cpp: "We XOR each block after the first with the previous one, prior to encryption."

Algorithm: BigWorld Plaintext-Chained Blowfish
----------------------------------------------
Key Length: Exactly 56 bytes (448 bits).
Block Size: Exactly 8 bytes (64 bits).
Input Length: Strictly positive multiple of 8 bytes (rejects unaligned lengths; no implicit PKCS#7).

Encryption:
    C_0 = E_K(P_0)
    C_i = E_K(P_i ^ P_{i-1})   for i >= 1

Decryption:
    P_0 = D_K(C_0)
    P_i = D_K(C_i) ^ P_{i-1}   for i >= 1

Note on 24-Byte Mercury::Address Representation:
    Mercury::Address is 20 bytes: 4B IP (network order) + 2B Port (network order) + 14B padding.
    Padded with 4 zero bytes to 24 bytes (3 x 8-byte blocks) for Blowfish alignment:
    - P_0 = [IP (4B), Port (2B), 0x00, 0x00]
    - P_1 = [0x00 * 8]
    - P_2 = [0x00 * 8]
    When encrypted:
    - C_0 = E_K(P_0)
    - C_1 = E_K(P_1 ^ P_0) = E_K(0 ^ P_0) = E_K(P_0) = C_0
    - C_2 = E_K(P_2 ^ P_1) = E_K(0 ^ 0) = E_K(0)
    When decrypted:
    - P_0 = D_K(C_0)
    - P_1 = D_K(C_1) ^ P_0 = P_0 ^ P_0 = [0x00 * 8]
    - P_2 = D_K(C_2) ^ P_1 = 0 ^ 0 = [0x00 * 8]
    Yielding exactly the 20-byte native Mercury::Address struct with 4 trailing zeroes.
"""

from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class BlowfishFilterError(Exception):
    """Raised when Blowfish encryption, decryption, or block validation fails."""
    pass


class BlowfishAddressFilter:
    """
    Implements BigWorld Plaintext-Chained Blowfish encryption and decryption.
    Compatible with native ROS Legacy iOS client binary and BigWorld 2.0.1 Mercury protocol.
    """

    KEY_SIZE = 56  # 448 bits
    BLOCK_SIZE = 8  # 64 bits

    def __init__(self, session_key: bytes):
        """Initializes instance filter with a validated 56-byte key."""
        if not isinstance(session_key, (bytes, bytearray)):
            raise BlowfishFilterError("Session key must be bytes.")
        if len(session_key) != self.KEY_SIZE:
            raise BlowfishFilterError(
                f"Session key must be exactly {self.KEY_SIZE} bytes (448 bits), got {len(session_key)}."
            )
        self.session_key = bytes(session_key)
        self._cipher = Cipher(algorithms.Blowfish(self.session_key), modes.ECB(), backend=default_backend())

    @classmethod
    def encrypt(cls, plaintext: bytes, session_key: bytes) -> bytes:
        """
        Encrypts multi-block plaintext using BigWorld Plaintext-Chaining.
        Plaintext length must be a strictly positive multiple of 8 bytes.
        """
        instance = cls(session_key)
        return instance.encrypt_data(plaintext)

    @classmethod
    def decrypt(cls, ciphertext: bytes, session_key: bytes) -> bytes:
        """
        Decrypts multi-block ciphertext using BigWorld Plaintext-Chaining.
        Ciphertext length must be a strictly positive multiple of 8 bytes.
        """
        instance = cls(session_key)
        return instance.decrypt_data(ciphertext)

    def encrypt_data(self, plaintext: bytes) -> bytes:
        """Instance encryption method implementing C_i = E_K(P_i ^ P_{i-1})."""
        if not isinstance(plaintext, (bytes, bytearray)):
            raise BlowfishFilterError("Plaintext must be bytes.")
        length = len(plaintext)
        if length == 0:
            raise BlowfishFilterError("Plaintext cannot be empty.")
        if length % self.BLOCK_SIZE != 0:
            raise BlowfishFilterError(
                f"Input length ({length}) is not a multiple of block size ({self.BLOCK_SIZE}). "
                "Implicit padding is strictly forbidden."
            )

        encryptor = self._cipher.encryptor()
        out = bytearray(length)
        prev_p: Optional[bytes] = None

        for offset in range(0, length, self.BLOCK_SIZE):
            curr_block = bytes(plaintext[offset:offset + self.BLOCK_SIZE])
            if prev_p is None:
                # First block (i=0): C_0 = E_K(P_0)
                xored_block = curr_block
            else:
                # Subsequent blocks (i>=1): C_i = E_K(P_i ^ P_{i-1})
                xored_block = bytes(a ^ b for a, b in zip(curr_block, prev_p))

            # Blowfish block encryption
            out[offset:offset + self.BLOCK_SIZE] = encryptor.update(xored_block)
            # Update previous plaintext block pointer (points to current plaintext)
            prev_p = curr_block

        return bytes(out)

    def decrypt_data(self, ciphertext: bytes) -> bytes:
        """Instance decryption method implementing P_i = D_K(C_i) ^ P_{i-1}."""
        if not isinstance(ciphertext, (bytes, bytearray)):
            raise BlowfishFilterError("Ciphertext must be bytes.")
        length = len(ciphertext)
        if length == 0:
            raise BlowfishFilterError("Ciphertext cannot be empty.")
        if length % self.BLOCK_SIZE != 0:
            raise BlowfishFilterError(
                f"Input stream size ({length}) is not a multiple of block size ({self.BLOCK_SIZE})."
            )

        decryptor = self._cipher.decryptor()
        out = bytearray(length)
        prev_p: Optional[bytes] = None

        for offset in range(0, length, self.BLOCK_SIZE):
            cipher_block = bytes(ciphertext[offset:offset + self.BLOCK_SIZE])
            decrypted_block = decryptor.update(cipher_block)

            if prev_p is None:
                # First block (i=0): P_0 = D_K(C_0)
                plain_block = decrypted_block
            else:
                # Subsequent blocks (i>=1): P_i = D_K(C_i) ^ P_{i-1}
                plain_block = bytes(a ^ b for a, b in zip(decrypted_block, prev_p))

            out[offset:offset + self.BLOCK_SIZE] = plain_block
            # Update previous plaintext block pointer (points to current decrypted plaintext)
            prev_p = plain_block

        return bytes(out)
