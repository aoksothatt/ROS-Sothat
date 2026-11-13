"""
Independent Reference Implementation of BigWorld Plaintext-Chained Blowfish.

STRICT INDEPENDENCE DECLARATION:
This module is isolated from the production prototype ('src/'). It does NOT import
BlowfishAddressFilter, loginapp_core, or any production source code.

It provides two independent reference engines:
1. OpenSSL C API Oracle (invoking BF_set_key and BF_ecb_encrypt in libcrypto directly).
2. Pure Independent Reference Class (IndependentBigWorldBlowfish).

Both implement the BigWorld Technology 2.0.1 chaining algorithm:
    C_0 = E_K(P_0)
    C_i = E_K(P_i ^ P_{i-1})
    P_0 = D_K(C_0)
    P_i = D_K(C_i) ^ P_{i-1}
"""

from typing import Optional
import ctypes
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class IndependentBlowfishError(Exception):
    """Raised when independent Blowfish processing fails."""
    pass


# OpenSSL C API structures and functions
class BF_KEY(ctypes.Structure):
    _fields_ = [('P', ctypes.c_uint32 * 18), ('S', ctypes.c_uint32 * 1024)]


def _load_libcrypto():
    for p in [r'C:\msys64\ucrt64\bin', r'C:\msys64\mingw64\bin', r'C:\Program Files\Git\usr\bin']:
        if os.path.isdir(p):
            try:
                os.add_dll_directory(p)
            except Exception:
                pass
            dll_path = os.path.join(p, 'libcrypto-3-x64.dll')
            if os.path.exists(dll_path):
                lib = ctypes.CDLL(dll_path)
                lib.BF_set_key.argtypes = [ctypes.POINTER(BF_KEY), ctypes.c_int, ctypes.c_char_p]
                lib.BF_set_key.restype = None
                lib.BF_ecb_encrypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(BF_KEY), ctypes.c_int]
                lib.BF_ecb_encrypt.restype = None
                return lib
    return None


_libcrypto = _load_libcrypto()


class OpenSSLCryptoOracle:
    """External cryptographic oracle invoking libcrypto.dll C functions directly."""

    @classmethod
    def is_available(cls) -> bool:
        return _libcrypto is not None

    @classmethod
    def encrypt_block(cls, block: bytes, key: bytes) -> bytes:
        assert len(block) == 8
        assert len(key) == 56
        if not _libcrypto:
            raise RuntimeError("libcrypto not available")
        bf_key = BF_KEY()
        _libcrypto.BF_set_key(ctypes.byref(bf_key), 56, key)
        out = ctypes.create_string_buffer(8)
        _libcrypto.BF_ecb_encrypt(block, out, ctypes.byref(bf_key), 1)  # 1 = BF_ENCRYPT
        return out.raw

    @classmethod
    def decrypt_block(cls, block: bytes, key: bytes) -> bytes:
        assert len(block) == 8
        assert len(key) == 56
        if not _libcrypto:
            raise RuntimeError("libcrypto not available")
        bf_key = BF_KEY()
        _libcrypto.BF_set_key(ctypes.byref(bf_key), 56, key)
        out = ctypes.create_string_buffer(8)
        _libcrypto.BF_ecb_encrypt(block, out, ctypes.byref(bf_key), 0)  # 0 = BF_DECRYPT
        return out.raw

    @classmethod
    def bigworld_encrypt(cls, plaintext: bytes, key: bytes) -> bytes:
        assert len(plaintext) % 8 == 0 and len(plaintext) > 0
        assert len(key) == 56
        out = bytearray(len(plaintext))
        prev_p = None
        for i in range(0, len(plaintext), 8):
            curr_p = plaintext[i:i+8]
            xored = curr_p if prev_p is None else bytes(a ^ b for a, b in zip(curr_p, prev_p))
            out[i:i+8] = cls.encrypt_block(xored, key)
            prev_p = curr_p
        return bytes(out)

    @classmethod
    def bigworld_decrypt(cls, ciphertext: bytes, key: bytes) -> bytes:
        assert len(ciphertext) % 8 == 0 and len(ciphertext) > 0
        assert len(key) == 56
        out = bytearray(len(ciphertext))
        prev_p = None
        for i in range(0, len(ciphertext), 8):
            curr_c = ciphertext[i:i+8]
            decrypted = cls.decrypt_block(curr_c, key)
            plain = decrypted if prev_p is None else bytes(a ^ b for a, b in zip(decrypted, prev_p))
            out[i:i+8] = plain
            prev_p = plain
        return bytes(out)


class IndependentBigWorldBlowfish:
    """
    Independent reference implementation using standard cryptography library.
    Zero imports from production src/.
    """

    KEY_SIZE = 56
    BLOCK_SIZE = 8

    def __init__(self, key: bytes):
        if len(key) != self.KEY_SIZE:
            raise IndependentBlowfishError(f"Key length must be {self.KEY_SIZE}, got {len(key)}")
        self.key = bytes(key)
        self._cipher = Cipher(algorithms.Blowfish(self.key), modes.ECB(), backend=default_backend())

    def encrypt(self, plaintext: bytes) -> bytes:
        if len(plaintext) == 0:
            raise IndependentBlowfishError("Plaintext cannot be empty.")
        if len(plaintext) % self.BLOCK_SIZE != 0:
            raise IndependentBlowfishError(f"Plaintext length ({len(plaintext)}) not multiple of {self.BLOCK_SIZE}")

        enc = self._cipher.encryptor()
        ciphertext = bytearray(len(plaintext))
        prev_plain: Optional[bytes] = None

        for i in range(0, len(plaintext), self.BLOCK_SIZE):
            curr_plain = plaintext[i:i + self.BLOCK_SIZE]
            if prev_plain is None:
                xored = curr_plain
            else:
                xored = bytes(a ^ b for a, b in zip(curr_plain, prev_plain))
            ciphertext[i:i + self.BLOCK_SIZE] = enc.update(xored)
            prev_plain = curr_plain

        return bytes(ciphertext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        if len(ciphertext) == 0:
            raise IndependentBlowfishError("Ciphertext cannot be empty.")
        if len(ciphertext) % self.BLOCK_SIZE != 0:
            raise IndependentBlowfishError(f"Ciphertext length ({len(ciphertext)}) not multiple of {self.BLOCK_SIZE}")

        dec = self._cipher.decryptor()
        plaintext = bytearray(len(ciphertext))
        prev_plain: Optional[bytes] = None

        for i in range(0, len(ciphertext), self.BLOCK_SIZE):
            curr_cipher = ciphertext[i:i + self.BLOCK_SIZE]
            decrypted = dec.update(curr_cipher)
            if prev_plain is None:
                plain_block = decrypted
            else:
                plain_block = bytes(a ^ b for a, b in zip(decrypted, prev_plain))
            plaintext[i:i + self.BLOCK_SIZE] = plain_block
            prev_plain = plain_block

        return bytes(plaintext)
