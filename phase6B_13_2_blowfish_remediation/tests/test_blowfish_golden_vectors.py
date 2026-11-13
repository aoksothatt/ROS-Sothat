"""
Independent Golden-Vector Test Suite for Remediated Blowfish Cipher.

STRICT INDEPENDENCE TEST:
Tests BlowfishAddressFilter in src/ against pre-calculated golden vectors
verified by OpenSSL C API and an independent reference implementation.
"""

import json
import os
import sys
import pytest

# Ensure prototype root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from src.blowfish_filter import BlowfishAddressFilter, BlowfishFilterError
from independent_reference.independent_blowfish import (
    IndependentBigWorldBlowfish, OpenSSLCryptoOracle
)


@pytest.fixture(scope="module")
def golden_vectors():
    path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "golden_vectors.json")
    with open(path, "r") as f:
        data = json.load(f)
    return {v["id"]: v for v in data["golden_vectors"]}


class TestBlowfishGoldenVectors:
    """Verifies BlowfishAddressFilter against independent golden vectors."""

    def test_gv01_one_block(self, golden_vectors):
        v = golden_vectors["GV01_ONE_BLOCK"]
        key = bytes.fromhex(v["key_hex"])
        plain = bytes.fromhex(v["plaintext_hex"])
        expected_cipher = bytes.fromhex(v["ciphertext_hex"])

        actual_cipher = BlowfishAddressFilter.encrypt(plain, key)
        assert actual_cipher == expected_cipher
        actual_plain = BlowfishAddressFilter.decrypt(actual_cipher, key)
        assert actual_plain == plain

    def test_gv02_two_block(self, golden_vectors):
        v = golden_vectors["GV02_TWO_BLOCK"]
        key = bytes.fromhex(v["key_hex"])
        plain = bytes.fromhex(v["plaintext_hex"])
        expected_cipher = bytes.fromhex(v["ciphertext_hex"])

        actual_cipher = BlowfishAddressFilter.encrypt(plain, key)
        assert actual_cipher == expected_cipher
        actual_plain = BlowfishAddressFilter.decrypt(actual_cipher, key)
        assert actual_plain == plain

    def test_gv03_three_block(self, golden_vectors):
        v = golden_vectors["GV03_THREE_BLOCK"]
        key = bytes.fromhex(v["key_hex"])
        plain = bytes.fromhex(v["plaintext_hex"])
        expected_cipher = bytes.fromhex(v["ciphertext_hex"])

        actual_cipher = BlowfishAddressFilter.encrypt(plain, key)
        assert actual_cipher == expected_cipher
        actual_plain = BlowfishAddressFilter.decrypt(actual_cipher, key)
        assert actual_plain == plain

    def test_gv04_mercury_address_127_0_0_1(self, golden_vectors):
        v = golden_vectors["GV04_MERCURY_ADDRESS_127_0_0_1"]
        key = bytes.fromhex(v["key_hex"])
        plain = bytes.fromhex(v["plaintext_hex"])
        expected_cipher = bytes.fromhex(v["ciphertext_hex"])

        actual_cipher = BlowfishAddressFilter.encrypt(plain, key)
        assert actual_cipher == expected_cipher
        actual_plain = BlowfishAddressFilter.decrypt(actual_cipher, key)
        assert actual_plain == plain

    def test_gv05_different_ip_port(self, golden_vectors):
        v = golden_vectors["GV05_DIFFERENT_IP_PORT"]
        key = bytes.fromhex(v["key_hex"])
        plain = bytes.fromhex(v["plaintext_hex"])
        expected_cipher = bytes.fromhex(v["ciphertext_hex"])

        actual_cipher = BlowfishAddressFilter.encrypt(plain, key)
        assert actual_cipher == expected_cipher
        actual_plain = BlowfishAddressFilter.decrypt(actual_cipher, key)
        assert actual_plain == plain

    def test_gv06_zero_padded_address_mathematical_property(self, golden_vectors):
        """
        Mathematical proof test:
        For a 24-byte address payload P = [P_0, 0_8, 0_8],
        Block 1 input to E_K is (0_8 ^ P_0) = P_0.
        Therefore, C_1 MUST identically equal C_0!
        """
        v = golden_vectors["GV06_ZERO_PADDED_ADDRESS_PROPERTY"]
        key = bytes.fromhex(v["key_hex"])
        plain = bytes.fromhex(v["plaintext_hex"])

        actual_cipher = BlowfishAddressFilter.encrypt(plain, key)
        c0 = actual_cipher[0:8]
        c1 = actual_cipher[8:16]
        c2 = actual_cipher[16:24]

        # In BigWorld plaintext chaining, C_1 must equal C_0
        assert c1 == c0, f"Block 1 ({c1.hex()}) must equal Block 0 ({c0.hex()})"
        # Block 2 input is (0_8 ^ 0_8) = 0_8. So C_2 must equal E_K(0_8)
        assert c2 != c0

    def test_gv07_invalid_key_length(self, golden_vectors):
        v = golden_vectors["GV07_INVALID_KEY_LENGTH"]
        invalid_key = bytes.fromhex(v["invalid_key_hex"])
        plain = b"12345678"

        with pytest.raises(BlowfishFilterError) as exc_info:
            BlowfishAddressFilter.encrypt(plain, invalid_key)
        assert "must be exactly 56 bytes" in str(exc_info.value)

        with pytest.raises(BlowfishFilterError) as exc_info:
            BlowfishAddressFilter.decrypt(plain, invalid_key)
        assert "must be exactly 56 bytes" in str(exc_info.value)

    def test_gv08_invalid_plaintext_length(self, golden_vectors):
        v = golden_vectors["GV08_INVALID_PLAINTEXT_LENGTH"]
        key = bytes.fromhex(v["key_hex"])
        invalid_plain = bytes.fromhex(v["invalid_plaintext_hex"])

        with pytest.raises(BlowfishFilterError) as exc_info:
            BlowfishAddressFilter.encrypt(invalid_plain, key)
        assert "not a multiple of block size" in str(exc_info.value)

    def test_gv09_invalid_ciphertext_length(self, golden_vectors):
        v = golden_vectors["GV09_INVALID_CIPHERTEXT_LENGTH"]
        key = bytes.fromhex(v["key_hex"])
        invalid_cipher = bytes.fromhex(v["invalid_ciphertext_hex"])

        with pytest.raises(BlowfishFilterError) as exc_info:
            BlowfishAddressFilter.decrypt(invalid_cipher, key)
        assert "not a multiple of block size" in str(exc_info.value)

    def test_gv10_interoperability_with_oracle(self, golden_vectors):
        v = golden_vectors["GV10_INTEROPERABILITY"]
        key = bytes.fromhex(v["key_hex"])
        plain = bytes.fromhex(v["plaintext_hex"])

        # Encrypt with production class, decrypt with OpenSSL C API Oracle
        prod_cipher = BlowfishAddressFilter.encrypt(plain, key)
        ossl_plain = OpenSSLCryptoOracle.bigworld_decrypt(prod_cipher, key)
        assert ossl_plain == plain

        # Encrypt with OpenSSL C API Oracle, decrypt with production class
        ossl_cipher = OpenSSLCryptoOracle.bigworld_encrypt(plain, key)
        prod_plain = BlowfishAddressFilter.decrypt(ossl_cipher, key)
        assert prod_plain == plain


class TestNegativeDetectors:
    """Explicitly verifies that faulty cipher modes fail the test suite."""

    @pytest.fixture
    def setup_data(self):
        key = bytes([i % 256 for i in range(56)])
        p = b"AlphaOneBetaTwo8"  # 2 blocks
        return key, p

    def test_ecb_mode_fails_detection(self, setup_data):
        """Simulates raw ECB mode and proves it fails against BigWorld ciphertext."""
        key, p = setup_data
        ecb_cipher = Cipher(algorithms.Blowfish(key), modes.ECB(), backend=default_backend()).encryptor().update(p)

        # Production decrypt of ECB ciphertext must NOT equal original plaintext
        decrypted = BlowfishAddressFilter.decrypt(ecb_cipher, key)
        assert decrypted != p, "ECB ciphertext must not decrypt to original plaintext in chained mode!"
        # Specifically, Block 0 matches, but Block 1 fails
        assert decrypted[0:8] == p[0:8]
        assert decrypted[8:16] != p[8:16]

    def test_cbc_mode_fails_detection(self, setup_data):
        """Simulates standard CBC mode (IV=0) and proves it fails."""
        key, p = setup_data
        cbc_cipher = Cipher(algorithms.Blowfish(key), modes.CBC(b"\x00" * 8), backend=default_backend()).encryptor().update(p)

        decrypted = BlowfishAddressFilter.decrypt(cbc_cipher, key)
        assert decrypted != p, "CBC ciphertext must not decrypt to original plaintext in chained mode!"

    def test_first_block_xor_corruption_fails(self, setup_data):
        """Proves that XORing the first block corrupts decryption."""
        key, p = setup_data
        correct_cipher = BlowfishAddressFilter.encrypt(p, key)
        corrupted_cipher = bytearray(correct_cipher)
        corrupted_cipher[0] ^= 0xFF

        decrypted = BlowfishAddressFilter.decrypt(bytes(corrupted_cipher), key)
        assert decrypted != p

    def test_block_order_reversal_fails(self, setup_data):
        """Proves that reversing block order produces invalid plaintext."""
        key, p = setup_data
        correct_cipher = BlowfishAddressFilter.encrypt(p, key)
        reversed_cipher = correct_cipher[8:16] + correct_cipher[0:8]

        decrypted = BlowfishAddressFilter.decrypt(reversed_cipher, key)
        assert decrypted != p
