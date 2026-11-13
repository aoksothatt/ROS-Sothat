"""
Blowfish Plaintext Block Chaining (PBC) Reference Implementation
Phase 6.2B.7.2 - Research & Verification

Derived from native NetEase Rules of Survival (iOS Mach-O ARM64) disassembly:
- neox::bwclient::Mercury::EncryptionFilter::initKey (VA 0x10091c300 - 0x10091c424)
- neox::bwclient::Mercury::EncryptionFilter::send    (VA 0x10091c6cc - 0x10091c840)
- neox::bwclient::Mercury::EncryptionFilter::recv    (VA 0x10091c8e8 - 0x10091ca30)

Mathematical Model:
- Block Size: 8 bytes (64 bits)
- Key Size: 4 to 56 bytes (32 to 448 bits)
- IV: Zero IV per datagram (stateless across packets)
- Chaining Transformation:
    Encryption:
        C_0 = E_K(P_0 ^ IV) = E_K(P_0)           (where IV = 0)
        C_i = E_K(P_i ^ P_(i-1))   for i >= 1     (XOR with PREVIOUS PLAINTEXT block)
    Decryption:
        P_0 = D_K(C_0)
        P_i = D_K(C_i) ^ P_(i-1)   for i >= 1     (XOR with PREVIOUS PLAINTEXT block)

Contrast with Standard CBC:
    In CBC:  C_i = E_K(P_i ^ C_(i-1))  (XOR with PREVIOUS CIPHERTEXT block)
             P_i = D_K(C_i) ^ C_(i-1)
"""

import struct
from typing import Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish


class BlowfishPBC:
    """
    Independent reference implementation of BigWorld Mercury's native
    Plaintext Block Chaining (PBC) Blowfish cipher.
    """
    BLOCK_SIZE = 8
    MIN_KEY_LEN = 4
    MAX_KEY_LEN = 56

    def __init__(self, key: bytes):
        if not (self.MIN_KEY_LEN <= len(key) <= self.MAX_KEY_LEN):
            raise ValueError(
                f"EncryptionFilter::initKey: Invalid key length {len(key)}. "
                f"Must be between {self.MIN_KEY_LEN} and {self.MAX_KEY_LEN} bytes."
            )
        self.key = key
        # ECB cipher primitive for individual 64-bit block transformations
        self._cipher = Cipher(Blowfish(self.key), modes.ECB())

    def encrypt_block(self, block: bytes) -> bytes:
        """Transforms a single 8-byte block using Blowfish ECB encryption."""
        if len(block) != self.BLOCK_SIZE:
            raise ValueError(f"Block size must be {self.BLOCK_SIZE} bytes")
        encryptor = self._cipher.encryptor()
        return encryptor.update(block)

    def decrypt_block(self, block: bytes) -> bytes:
        """Transforms a single 8-byte block using Blowfish ECB decryption."""
        if len(block) != self.BLOCK_SIZE:
            raise ValueError(f"Block size must be {self.BLOCK_SIZE} bytes")
        decryptor = self._cipher.decryptor()
        return decryptor.update(block)

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypts padded plaintext using Plaintext Block Chaining (PBC) with zero IV.
        Input length MUST be a multiple of BLOCK_SIZE (8 bytes).

        Follows native assembly at VA 0x10091c7f0 - 0x10091c834:
        - x25: block offset (0, 8, 16, ...)
        - x8:  pointer to previous plaintext block (NULL for block 0)
        - x27: pointer to current plaintext block
        - Line 0x10091c82c: mov x8, x27 (sets previous block to current plaintext block!)
        """
        total_len = len(plaintext)
        if total_len % self.BLOCK_SIZE != 0:
            raise ValueError(
                f"EncryptionFilter::encrypt: Input length ({total_len}) "
                f"is not a multiple of block size ({self.BLOCK_SIZE})"
            )
        if total_len == 0:
            return b""

        ciphertext = bytearray(total_len)
        prev_plaintext = None  # Implicit zero IV for block 0 (VA 0x10091c7f4)

        for offset in range(0, total_len, self.BLOCK_SIZE):
            p_block = plaintext[offset:offset + self.BLOCK_SIZE]
            
            if prev_plaintext is None:
                # Block 0: P_0 ^ IV where IV = 0 -> P_0
                xored = p_block
            else:
                # Block i >= 1: P_i ^ P_(i-1) (XOR with previous PLAINTEXT)
                xored = bytes(a ^ b for a, b in zip(p_block, prev_plaintext))

            # Blowfish ECB encrypt in-place
            c_block = self.encrypt_block(xored)
            ciphertext[offset:offset + self.BLOCK_SIZE] = c_block

            # Native instruction 0x10091c82c: mov x8, x27
            # Updates previous block reference to the input plaintext block!
            prev_plaintext = p_block

        return bytes(ciphertext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypts ciphertext using Plaintext Block Chaining (PBC) with zero IV.
        Input length MUST be a multiple of BLOCK_SIZE (8 bytes).

        Follows native assembly at VA 0x10091c95c - 0x10091c9c4:
        - x24: block offset (0, 8, 16, ...)
        - x26: pointer to previously decrypted plaintext block (NULL for block 0)
        - In-place decryption:
            Block 0: P_0 = D_K(C_0)
            Block i >= 1: P_i = D_K(C_i) ^ P_(i-1)
        """
        total_len = len(ciphertext)
        if total_len % self.BLOCK_SIZE != 0:
            raise ValueError(
                f"EncryptionFilter::decrypt: Input stream size ({total_len}) "
                f"is not a multiple of the block size ({self.BLOCK_SIZE})"
            )
        if total_len == 0:
            return b""

        plaintext = bytearray(total_len)
        prev_plaintext = None

        for offset in range(0, total_len, self.BLOCK_SIZE):
            c_block = ciphertext[offset:offset + self.BLOCK_SIZE]
            
            # 1. Blowfish ECB decrypt block in place
            raw_decrypted = self.decrypt_block(c_block)

            # 2. XOR with previous decrypted plaintext block if i >= 1
            if prev_plaintext is None:
                # Block 0: raw decrypted is P_0
                p_block = raw_decrypted
            else:
                # Block i >= 1: P_i = D(C_i) ^ P_(i-1)
                p_block = bytes(a ^ b for a, b in zip(raw_decrypted, prev_plaintext))

            plaintext[offset:offset + self.BLOCK_SIZE] = p_block
            prev_plaintext = p_block

        return bytes(plaintext)

    def encrypt_standard_cbc(self, plaintext: bytes) -> bytes:
        """
        Standard Cipher Block Chaining (CBC) with zero IV.
        Provided strictly for mathematical comparison against PBC.
        C_i = E_K(P_i ^ C_(i-1))
        """
        total_len = len(plaintext)
        if total_len % self.BLOCK_SIZE != 0:
            raise ValueError("Input length must be a multiple of 8")
        if total_len == 0:
            return b""
        
        cipher_cbc = Cipher(Blowfish(self.key), modes.CBC(bytes(self.BLOCK_SIZE)))
        enc = cipher_cbc.encryptor()
        return enc.update(plaintext) + enc.finalize()

    def decrypt_standard_cbc(self, ciphertext: bytes) -> bytes:
        """
        Standard Cipher Block Chaining (CBC) decryption with zero IV.
        P_i = D_K(C_i) ^ C_(i-1)
        """
        total_len = len(ciphertext)
        if total_len % self.BLOCK_SIZE != 0:
            raise ValueError("Input length must be a multiple of 8")
        if total_len == 0:
            return b""
            
        cipher_cbc = Cipher(Blowfish(self.key), modes.CBC(bytes(self.BLOCK_SIZE)))
        dec = cipher_cbc.decryptor()
        return dec.update(ciphertext) + dec.finalize()
