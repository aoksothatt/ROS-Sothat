"""
Unit tests for RSA Handshake research and LocalRSATestHarness.
Validates:
1. Local test RSA keypair generation.
2. Logon request serialization and round-trip parsing.
3. Asymmetric RSA encryption with public key and decryption with private key.
4. LoginHandshakeResponse packing and unpacking.
5. Error handling on corrupted / undecryptable payloads.
"""

import os
import secrets
import time
import pytest

from gateway.constants import LOGON_STATUS_FAILED, LOGON_STATUS_OK
from gateway.handshake import (
    LocalRSATestHarness,
    LoginHandshakeRequest,
    LoginHandshakeResponse,
)


class TestLoginHandshakePayloads:
    """Tests for payload encoding and decoding."""

    def test_request_serialization_roundtrip(self):
        req = LoginHandshakeRequest(
            username="TestPlayer_01",
            ticket_or_token="mock_ticket_abc123",
            client_version="1.200000.123456",
            timestamp=int(time.time()),
            nonce=secrets.token_bytes(16)
        )
        data = req.to_bytes()
        decoded = LoginHandshakeRequest.from_bytes(data)

        assert decoded.username == "TestPlayer_01"
        assert decoded.ticket_or_token == "mock_ticket_abc123"
        assert decoded.client_version == "1.200000.123456"
        assert decoded.timestamp == req.timestamp
        assert decoded.nonce == req.nonce

    def test_response_serialization_roundtrip(self):
        resp = LoginHandshakeResponse(
            status_code=LOGON_STATUS_OK,
            baseapp_ip="192.168.1.150",
            baseapp_port=20001,
            session_key=0x1A2B3C4D
        )
        data = resp.encode()
        decoded = LoginHandshakeResponse.decode(data)

        assert decoded.status_code == LOGON_STATUS_OK
        assert decoded.baseapp_ip == "192.168.1.150"
        assert decoded.baseapp_port == 20001
        assert decoded.session_key == 0x1A2B3C4D


class TestLocalRSATestHarness:
    """Tests for local RSA encryption and decryption test harness."""

    def test_key_generation_and_export(self):
        harness = LocalRSATestHarness(key_size=2048)
        pem = harness.get_public_key_pem()
        assert b"BEGIN PUBLIC KEY" in pem
        assert b"END PUBLIC KEY" in pem

    def test_encryption_and_decryption_flow(self):
        harness = LocalRSATestHarness(key_size=2048)
        req = LoginHandshakeRequest(
            username="iOS_Private_User",
            ticket_or_token="token_xyz",
            client_version="1.0",
            timestamp=1700000000,
            nonce=secrets.token_bytes(16)
        )

        # Encrypt with public key
        ciphertext = harness.encrypt_logon_request(req)
        assert len(ciphertext) == 256  # 2048 bits = 256 bytes

        # Decrypt with private key
        decrypted = harness.decrypt_logon_request(ciphertext)
        assert decrypted.username == "iOS_Private_User"
        assert decrypted.ticket_or_token == "token_xyz"
        assert decrypted.nonce == req.nonce

    def test_process_handshake_success(self):
        harness = LocalRSATestHarness(key_size=2048)
        req = LoginHandshakeRequest(
            username="ValidUser",
            ticket_or_token="token_valid",
            client_version="1.0",
            timestamp=1700000000,
            nonce=secrets.token_bytes(16)
        )
        ciphertext = harness.encrypt_logon_request(req)

        resp = harness.process_handshake(
            ciphertext=ciphertext,
            baseapp_ip="127.0.0.1",
            baseapp_port=20001
        )
        assert resp.status_code == LOGON_STATUS_OK
        assert resp.baseapp_ip == "127.0.0.1"
        assert resp.baseapp_port == 20001
        assert resp.session_key > 0

    def test_process_handshake_corrupted_ciphertext(self):
        harness = LocalRSATestHarness(key_size=2048)
        # Random garbage bytes that cannot be decrypted
        garbage = os.urandom(256)
        resp = harness.process_handshake(garbage)
        assert resp.status_code == LOGON_STATUS_FAILED
        assert resp.session_key == 0
