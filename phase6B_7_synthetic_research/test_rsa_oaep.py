"""
Offline Synthetic RSA-OAEP Cryptographic Verification Module
Phase 6.2B.7 - Research Only

Tests:
1. Deterministic synthetic RSA key generation (1024-bit and 2048-bit).
2. PEM serialization/deserialization.
3. RSA-OAEP encryption/decryption matching OpenSSL RSA_PKCS1_OAEP_PADDING.
4. Exact recovery of 56-byte synthetic Blowfish session keys.
5. Strict boundary condition enforcement (OAEP max chunk size: k - 42).
6. Negative validation: mismatched keys, altered ciphertexts, wrong padding, wrong MGF1 digests.
7. Zero use of original game keys or proprietary credentials.
"""

import unittest
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization


class TestSyntheticRSAOAEP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Generate synthetic test keypairs (isolated for testing only)
        # Using public_exponent 65537 (standard OpenSSL default)
        cls.key1024 = rsa.generate_private_key(
            public_exponent=65537,
            key_size=1024
        )
        cls.pub1024 = cls.key1024.public_key()

        cls.key2048 = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        cls.pub2048 = cls.key2048.public_key()

        # Generate an unrelated wrong keypair for negative tests
        cls.wrong_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=1024
        )

    def test_01_synthetic_key_serialization(self):
        """Verify public key serializes to SubjectPublicKeyInfo PEM format."""
        pem_pub = self.pub1024.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.assertTrue(pem_pub.startswith(b"-----BEGIN PUBLIC KEY-----"))
        self.assertTrue(pem_pub.strip().endswith(b"-----END PUBLIC KEY-----"))

        # Reload key from PEM
        reloaded_pub = serialization.load_pem_public_key(pem_pub)
        self.assertEqual(reloaded_pub.key_size, 1024)

    def test_02_oaep_56_byte_session_key_roundtrip_1024(self):
        """Verify encryption and decryption of 56-byte synthetic Blowfish session key (1024-bit RSA)."""
        synthetic_blowfish_key = b"SYNTHETIC_BLOWFISH_SESSION_KEY_56_BYTES_TEST_PAYLOAD!123"
        self.assertEqual(len(synthetic_blowfish_key), 56)

        # Encrypt with RSA_PKCS1_OAEP_PADDING (SHA-1, MGF1(SHA-1), label=None)
        ciphertext = self.pub1024.encrypt(
            synthetic_blowfish_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        self.assertEqual(len(ciphertext), 128)  # 1024 bits = 128 bytes

        # Decrypt with matching private key
        plaintext = self.key1024.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        self.assertEqual(plaintext, synthetic_blowfish_key)

    def test_03_oaep_56_byte_session_key_roundtrip_2048(self):
        """Verify encryption and decryption of 56-byte synthetic Blowfish session key (2048-bit RSA)."""
        synthetic_blowfish_key = b"SYNTHETIC_BLOWFISH_SESSION_KEY_56_BYTES_TEST_PAYLOAD!123"
        self.assertEqual(len(synthetic_blowfish_key), 56)
        ciphertext = self.pub2048.encrypt(
            synthetic_blowfish_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        self.assertEqual(len(ciphertext), 256)  # 2048 bits = 256 bytes

        plaintext = self.key2048.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        self.assertEqual(plaintext, synthetic_blowfish_key)

    def test_04_boundary_conditions_1024(self):
        """Test OAEP maximum capacity boundaries for 1024-bit key (k - 42 = 86 bytes)."""
        max_capacity = 128 - 42  # 86 bytes
        payload_85 = b"A" * (max_capacity - 1)
        payload_86 = b"B" * max_capacity
        payload_87 = b"C" * (max_capacity + 1)

        # 85 bytes: Success
        ct85 = self.pub1024.encrypt(
            payload_85,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        self.assertEqual(len(ct85), 128)
        self.assertEqual(self.key1024.decrypt(
            ct85,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        ), payload_85)

        # 86 bytes: Success (exact maximum)
        ct86 = self.pub1024.encrypt(
            payload_86,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        self.assertEqual(len(ct86), 128)
        self.assertEqual(self.key1024.decrypt(
            ct86,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        ), payload_86)

        # 87 bytes: Must raise ValueError (exceeds OAEP capacity)
        with self.assertRaises(ValueError):
            self.pub1024.encrypt(
                payload_87,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
            )

    def test_05_boundary_conditions_2048(self):
        """Test OAEP maximum capacity boundaries for 2048-bit key (k - 42 = 214 bytes)."""
        max_capacity = 256 - 42  # 214 bytes
        payload_214 = b"X" * max_capacity
        payload_215 = b"Y" * (max_capacity + 1)

        # 214 bytes: Success
        ct214 = self.pub2048.encrypt(
            payload_214,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        self.assertEqual(len(ct214), 256)
        self.assertEqual(self.key2048.decrypt(
            ct214,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        ), payload_214)

        # 215 bytes: Must raise ValueError
        with self.assertRaises(ValueError):
            self.pub2048.encrypt(
                payload_215,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
            )

    def test_06_negative_wrong_private_key(self):
        """Verify decryption fails when using a different private key."""
        synthetic_payload = b"SECRET_SESSION_TOKEN_12345"
        ciphertext = self.pub1024.encrypt(
            synthetic_payload,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        with self.assertRaises(ValueError):
            self.wrong_key.decrypt(
                ciphertext,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
            )

    def test_07_negative_tampered_ciphertext(self):
        """Verify decryption fails if ciphertext bits are flipped."""
        synthetic_payload = b"SECRET_SESSION_TOKEN_12345"
        ciphertext = bytearray(self.pub1024.encrypt(
            synthetic_payload,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        ))
        # Flip bit in ciphertext
        ciphertext[20] ^= 0xFF
        with self.assertRaises(ValueError):
            self.key1024.decrypt(
                bytes(ciphertext),
                padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
            )

    def test_08_negative_padding_mode_mismatch(self):
        """Verify decryption fails if server attempts PKCS#1 v1.5 padding on OAEP ciphertext."""
        synthetic_payload = b"SECRET_SESSION_TOKEN_12345"
        ciphertext = self.pub1024.encrypt(
            synthetic_payload,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        # Attempt PKCS#1 v1.5 decryption: OpenSSL 3 Bleichenbacher mitigation returns empty or corrupted
        pt = self.key1024.decrypt(
            ciphertext,
            padding.PKCS1v15()
        )
        self.assertNotEqual(pt, synthetic_payload)

    def test_09_negative_mgf1_digest_mismatch(self):
        """Verify decryption fails if MGF1 digest does not match (SHA-256 vs SHA-1)."""
        synthetic_payload = b"SECRET_SESSION_TOKEN_12345"
        ciphertext = self.pub1024.encrypt(
            synthetic_payload,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        with self.assertRaises(ValueError):
            self.key1024.decrypt(
                ciphertext,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA1(), label=None)
            )

    def test_10_negative_label_mismatch(self):
        """Verify decryption fails if OAEP label is non-empty when expected empty."""
        synthetic_payload = b"SECRET_SESSION_TOKEN_12345"
        ciphertext = self.pub1024.encrypt(
            synthetic_payload,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        with self.assertRaises(ValueError):
            self.key1024.decrypt(
                ciphertext,
                padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=b"NON_EMPTY_LABEL")
            )


if __name__ == "__main__":
    unittest.main()
