"""
Cryptographic Utilities for RSA-OAEP SHA-1.

Implements verified asymmetric decryption matching native client:
- Algorithm: RSA with OAEP padding.
- MGF1 Algorithm: SHA-1.
- Hash Algorithm: SHA-1.
- OpenSSL constant: RSA_PKCS1_OAEP_PADDING (4).
"""

from typing import Union
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization


class RsaDecryptionError(Exception):
    """Raised when RSA-OAEP decryption fails due to corrupted ciphertext or bad keys."""
    pass


class RsaOaepEngine:
    """Handles RSA-OAEP encryption and decryption using SHA-1."""

    def __init__(self, private_key: rsa.RSAPrivateKey):
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def from_pem_file(cls, pem_path: str) -> "RsaOaepEngine":
        """Loads an RSA private key from a PEM-encoded file."""
        with open(pem_path, 'rb') as f:
            key_data = f.read()
        private_key = serialization.load_pem_private_key(key_data, password=None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise TypeError("Loaded key is not an RSA private key.")
        return cls(private_key)

    @classmethod
    def from_pem_bytes(cls, pem_bytes: bytes) -> "RsaOaepEngine":
        """Loads an RSA private key from PEM bytes."""
        private_key = serialization.load_pem_private_key(pem_bytes, password=None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise TypeError("Loaded key is not an RSA private key.")
        return cls(private_key)

    @property
    def public_key(self) -> rsa.RSAPublicKey:
        return self._public_key

    def decrypt(self, ciphertext: bytes) -> bytes:
        """
        Decrypts an RSA-OAEP ciphertext using SHA-1 and MGF1-SHA1.
        Raises RsaDecryptionError on corrupted or improperly padded data.
        """
        try:
            plaintext = self._private_key.decrypt(
                ciphertext,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            )
            return plaintext
        except Exception as e:
            raise RsaDecryptionError(f"RSA-OAEP decryption failed: {e}") from e

    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypts plaintext using the public key with OAEP SHA-1.
        Used by synthetic clients to generate native-compatible envelopes.
        """
        return self._public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
