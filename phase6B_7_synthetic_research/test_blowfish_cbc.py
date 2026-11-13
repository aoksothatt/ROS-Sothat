"""
Offline Synthetic Blowfish Encryption & Decryption Verification Module
Phase 6.2B.7 - Research Only

Implements and validates:
1. Native client algorithm: Blowfish-ECB block chaining with zero IV and ANSI X9.23 / PKCS#7 padding
   (as disassembled from neox::bwclient::Mercury::EncryptionFilter at VA 0x10091c7f0 - 0x10091c834).
2. Equivalence against standard library Blowfish-CBC with zero IV (b'\x00' * 8).
3. Exact plaintext recovery across critical length boundaries: 0, 1, 7, 8, 9, 15, 16, 17 bytes.
4. Key length boundary enforcement: 4 to 56 bytes (disassembly bounds check: sub w8, w21, #4; cmp w8, #0x34).
5. Error handling: non-multiple of 8 byte inputs, invalid pad lengths, corrupted ciphertexts.
6. Per-datagram statelessness: zero IV reset on each independent datagram.
"""

import unittest
from cryptography.hazmat.primitives.ciphers import Cipher, modes
from cryptography.hazmat.decrepit.ciphers.algorithms import Blowfish


class NativeBlowfishFilter:
    """
    Python model of neox::bwclient::Mercury::EncryptionFilter disassembled from Mach-O.
    VA 0x10091c300 - 0x10091ca20.
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
        # Setup ECB cipher for block-by-block operation
        self.cipher = Cipher(Blowfish(self.key), modes.ECB())

    def encrypt_native(self, data: bytes, padding_scheme="ansi_x923") -> bytes:
        """
        Disassembled from EncryptionFilter::encrypt (VA 0x10091c780 - 0x10091c834).
        1. Pad data to multiple of 8 (pad_len = 8 - (len % 8) -> 1 to 8 bytes).
        2. Set last byte of buffer to pad_len.
        3. Loop through 8-byte blocks with CBC chaining using zero IV for block 0.
        """
        raw_len = len(data)
        pad_len = self.BLOCK_SIZE - (raw_len % self.BLOCK_SIZE)
        
        if padding_scheme == "ansi_x923":
            # ANSI X9.23: zero bytes with last byte = pad_len
            pad_bytes = bytes([0] * (pad_len - 1)) + bytes([pad_len])
        elif padding_scheme == "pkcs7":
            # PKCS#7: all bytes = pad_len
            pad_bytes = bytes([pad_len] * pad_len)
        else:
            raise ValueError(f"Unknown padding scheme: {padding_scheme}")

        padded_data = data + pad_bytes
        padded_len = len(padded_data)
        assert padded_len % self.BLOCK_SIZE == 0

        # CBC loop using ECB encryptor and zero IV
        encryptor = self.cipher.encryptor()
        ciphertext = bytearray()
        prev_block = bytes(self.BLOCK_SIZE)  # Zero IV for each datagram (VA 0x10091c7f4)

        for offset in range(0, padded_len, self.BLOCK_SIZE):
            block = padded_data[offset:offset + self.BLOCK_SIZE]
            xored = bytes(a ^ b for a, b in zip(block, prev_block))
            c_block = encryptor.update(xored)
            ciphertext.extend(c_block)
            prev_block = c_block

        return bytes(ciphertext)

    def decrypt_native(self, ciphertext: bytes) -> bytes:
        """
        Disassembled from EncryptionFilter::decrypt (VA 0x10091c8f0 - 0x10091ca20).
        1. Input length must be a multiple of 8.
        2. Decrypt each 8-byte block using ECB and XOR with previous ciphertext.
        3. Read last byte as pad_len. Validate 1 <= pad_len <= 8.
        4. Truncate pad_len bytes.
        """
        ct_len = len(ciphertext)
        if ct_len % self.BLOCK_SIZE != 0:
            raise ValueError(
                f"EncryptionFilter::decrypt: Input stream size ({ct_len}) "
                f"is not a multiple of the block size ({self.BLOCK_SIZE})"
            )
        if ct_len == 0:
            return b""

        decryptor = self.cipher.decryptor()
        plaintext_buf = bytearray()
        prev_block = bytes(self.BLOCK_SIZE)  # Zero IV

        for offset in range(0, ct_len, self.BLOCK_SIZE):
            c_block = ciphertext[offset:offset + self.BLOCK_SIZE]
            raw_p = decryptor.update(c_block)
            p_block = bytes(a ^ b for a, b in zip(raw_p, prev_block))
            plaintext_buf.extend(p_block)
            prev_block = c_block

        # Read last byte as pad length (VA 0x10091c9dc: ldrb w21, [x10, #0x5f])
        pad_len = plaintext_buf[-1]
        if not (1 <= pad_len <= self.BLOCK_SIZE):
            raise ValueError(f"EncryptionFilter::decrypt: Illegal pad length {pad_len}")

        return bytes(plaintext_buf[:-pad_len])

    def encrypt_standard_cbc(self, data: bytes) -> bytes:
        """Standard cryptography library Blowfish CBC with zero IV."""
        raw_len = len(data)
        pad_len = self.BLOCK_SIZE - (raw_len % self.BLOCK_SIZE)
        padded_data = data + bytes([0] * (pad_len - 1)) + bytes([pad_len])

        cipher_cbc = Cipher(Blowfish(self.key), modes.CBC(bytes(self.BLOCK_SIZE)))
        enc = cipher_cbc.encryptor()
        return enc.update(padded_data) + enc.finalize()


class TestSyntheticBlowfish(unittest.TestCase):
    def setUp(self):
        # 56-byte synthetic session key
        self.synthetic_key = b"0123456789abcdef0123456789abcdef0123456789abcdef01234567"
        self.assertEqual(len(self.synthetic_key), 56)
        self.filter = NativeBlowfishFilter(self.synthetic_key)

    def test_01_key_length_boundaries(self):
        """Verify key length boundaries: 4 to 56 bytes strictly enforced."""
        # Valid key lengths
        for klen in (4, 16, 24, 32, 48, 56):
            key = b"K" * klen
            f = NativeBlowfishFilter(key)
            self.assertEqual(len(f.key), klen)

        # Invalid key lengths (< 4 or > 56)
        for klen in (0, 1, 2, 3, 57, 64, 128):
            key = b"X" * klen
            with self.assertRaises(ValueError):
                NativeBlowfishFilter(key)

    def test_02_native_vs_standard_cbc_equivalence(self):
        """Verify native unrolled ECB loop produces exact identical bytes to standard Blowfish-CBC."""
        test_payloads = [
            b"",
            b"A",
            b"1234567",
            b"12345678",
            b"123456789",
            b"HELLO_WORLD_TEST",
            b"EXACTLY_TWENTY_FOUR_BYTES!!",
            b"A" * 120
        ]
        for p in test_payloads:
            ct_native = self.filter.encrypt_native(p, padding_scheme="ansi_x923")
            ct_std = self.filter.encrypt_standard_cbc(p)
            self.assertEqual(ct_native, ct_std, f"Mismatch on payload length {len(p)}")

    def test_03_exact_plaintext_recovery_across_lengths(self):
        """Verify exact recovery for plaintexts of 0, 1, 7, 8, 9, 15, 16, 17 bytes."""
        critical_lengths = [0, 1, 7, 8, 9, 15, 16, 17, 31, 32, 33, 63, 64, 65]
        for length in critical_lengths:
            plaintext = bytes([(i % 256) for i in range(length)])
            # Test ANSI X9.23
            ct_ansi = self.filter.encrypt_native(plaintext, padding_scheme="ansi_x923")
            self.assertEqual(len(ct_ansi) % 8, 0)
            self.assertTrue(len(ct_ansi) >= len(plaintext) + 1)
            recovered_ansi = self.filter.decrypt_native(ct_ansi)
            self.assertEqual(recovered_ansi, plaintext)

            # Test PKCS#7
            ct_pkcs7 = self.filter.encrypt_native(plaintext, padding_scheme="pkcs7")
            self.assertEqual(len(ct_pkcs7) % 8, 0)
            recovered_pkcs7 = self.filter.decrypt_native(ct_pkcs7)
            self.assertEqual(recovered_pkcs7, plaintext)

    def test_04_tampered_ciphertext(self):
        """Verify tampered ciphertext produces corrupted data or invalid padding error."""
        plaintext = b"RULES_OF_SURVIVAL_MERCURY_PACKET_TEST"
        ciphertext = bytearray(self.filter.encrypt_native(plaintext))
        # Corrupt a byte in the last block (affecting padding)
        ciphertext[-1] ^= 0x0F
        try:
            res = self.filter.decrypt_native(bytes(ciphertext))
            self.assertNotEqual(res, plaintext)
        except ValueError:
            pass  # Expected if pad_len > 8 or pad_len == 0

    def test_05_truncated_ciphertext(self):
        """Verify truncated ciphertext (not multiple of 8) is rejected."""
        plaintext = b"VALID_PACKET_DATA"
        ciphertext = self.filter.encrypt_native(plaintext)
        truncated = ciphertext[:-3]  # Drop 3 bytes -> length not multiple of 8
        with self.assertRaises(ValueError):
            self.filter.decrypt_native(truncated)

    def test_06_independent_datagram_statelessness(self):
        """Verify each datagram begins with fresh zero IV (no state carried between packets)."""
        packet1 = b"DATAGRAM_ONE_PAYLOAD"
        packet2 = b"DATAGRAM_TWO_DIFFERENT_PAYLOAD"

        # Encrypt packet 1 then packet 2
        ct1 = self.filter.encrypt_native(packet1)
        ct2 = self.filter.encrypt_native(packet2)

        # Encrypt packet 2 standalone
        filter_fresh = NativeBlowfishFilter(self.synthetic_key)
        ct2_fresh = filter_fresh.encrypt_native(packet2)

        # Must be bit-for-bit identical!
        self.assertEqual(ct2, ct2_fresh)

        # Decrypt out-of-order
        self.assertEqual(self.filter.decrypt_native(ct2), packet2)
        self.assertEqual(self.filter.decrypt_native(ct1), packet1)


if __name__ == "__main__":
    unittest.main()
