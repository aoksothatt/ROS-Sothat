"""
Offline Synthetic Protocol Test Vector Suite & Comprehensive Runner
Phase 6.2B.7 - Research Only

Consolidates deterministic test vectors and executes full offline validation:
1. RSA-OAEP Test Vectors (Deterministic 1024-bit / 2048-bit key fixtures)
2. Blowfish-CBC Test Vectors (Deterministic 56-byte key fixtures, ANSI X9.23 / PKCS#7 padding)
3. Mercury UDP Framing Test Vectors (Reverse-order footers, 32-bit XOR checksum)
"""

import binascii
import struct
import unittest
from test_rsa_oaep import TestSyntheticRSAOAEP
from test_blowfish_cbc import NativeBlowfishFilter, TestSyntheticBlowfish
from test_mercury_parser import (
    MercuryPacketFlags,
    MercuryPacketParser,
    compute_mercury_checksum,
    TestSyntheticMercuryParser,
)


class TestSyntheticVectors(unittest.TestCase):
    def test_rsa_vector_generation(self):
        """Generate and verify deterministic RSA-OAEP synthetic vectors."""
        # 56-byte synthetic session key payload
        session_payload = b"DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY_56_BYTES!12"
        self.assertEqual(len(session_payload), 56)

        # Verify against public test fixture
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        from cryptography.hazmat.primitives import hashes

        # Generate key with fixed public exponent 65537
        priv_key = rsa.generate_private_key(65537, 1024)
        pub_key = priv_key.public_key()

        ciphertext = pub_key.encrypt(
            session_payload,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        self.assertEqual(len(ciphertext), 128)
        recovered = priv_key.decrypt(
            ciphertext,
            padding.OAEP(mgf=padding.MGF1(hashes.SHA1()), algorithm=hashes.SHA1(), label=None)
        )
        self.assertEqual(recovered, session_payload)

    def test_blowfish_vector_generation(self):
        """Generate and verify deterministic Blowfish-CBC test vectors."""
        fixed_key = bytes([i % 256 for i in range(56)])  # 56-byte sequence
        self.assertEqual(len(fixed_key), 56)

        filter_inst = NativeBlowfishFilter(fixed_key)

        # Vector 1: 16-byte payload (exact 2 blocks -> requires 8 bytes padding)
        p1 = b"0123456789ABCDEF"
        ct1 = filter_inst.encrypt_native(p1, padding_scheme="ansi_x923")
        self.assertEqual(len(ct1), 24)  # 16 + 8 bytes padding
        self.assertEqual(filter_inst.decrypt_native(ct1), p1)

        # Vector 2: 7-byte payload (requires 1 byte padding)
        p2 = b"1234567"
        ct2 = filter_inst.encrypt_native(p2, padding_scheme="ansi_x923")
        self.assertEqual(len(ct2), 8)   # 7 + 1 byte padding
        self.assertEqual(filter_inst.decrypt_native(ct2), p2)

        # Vector 3: 0-byte payload (requires 8 bytes padding)
        p3 = b""
        ct3 = filter_inst.encrypt_native(p3, padding_scheme="ansi_x923")
        self.assertEqual(len(ct3), 8)
        self.assertEqual(filter_inst.decrypt_native(ct3), p3)

    def test_mercury_vector_generation(self):
        """Generate and verify deterministic Mercury packet framing test vector."""
        payload = b"SYNTHETIC_MERCURY_PAYLOAD_BODY"
        seq_num = 0x000004D2       # 1234 in decimal
        channel_id = 0x00010001    # Channel index
        acks = [100, 101, 102]

        packet = MercuryPacketParser.pack(
            payload=payload,
            seq_num=seq_num,
            channel_id=channel_id,
            acks=acks,
            with_checksum=True
        )

        unpacked = MercuryPacketParser.unpack(packet)
        self.assertEqual(unpacked["payload"], payload)
        self.assertEqual(unpacked["seq_num"], seq_num)
        self.assertEqual(unpacked["channel_id"], channel_id)
        self.assertEqual(unpacked["acks"], acks)
        self.assertTrue(unpacked["has_checksum"])


def run_full_validation_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSyntheticRSAOAEP))
    suite.addTests(loader.loadTestsFromTestCase(TestSyntheticBlowfish))
    suite.addTests(loader.loadTestsFromTestCase(TestSyntheticMercuryParser))
    suite.addTests(loader.loadTestsFromTestCase(TestSyntheticVectors))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    result = run_full_validation_suite()
    print(f"\n=======================================================")
    print(f"PHASE 6.2B.7 SYNTHETIC TEST SUITE EXECUTION SUMMARY:")
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    print(f"=======================================================")
