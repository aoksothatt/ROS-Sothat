"""
Comprehensive Offline Automated Test Suite for Synthetic LoginApp Prototype.

Tests all 12 scenarios from Phase 6.2B.12 plus protocol edge cases:
- TC-01: Valid Login Handshake
- TC-02: Invalid Username (Not Found)
- TC-03: Invalid Password (Bad Password)
- TC-04: Malformed RSA Ciphertext
- TC-05: Invalid Login Version (Mismatch)
- TC-06: Request ID Correlation
- TC-07: Invalid Mercury Flags (Missing HAS_REQUESTS)
- TC-08: Invalid Session Key Length
- TC-09: Replayed Login Nonce (Replay Protection)
- TC-10: Rate Limiting Enforcement
- TC-11: BaseApp Endpoint Validity
- TC-12: Concurrent Synthetic Sessions
- Additional: Banned user handling, session expiration, log sanitation.
"""

import os
import sys
import time
import pytest

# Add prototype root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto import RsaOaepEngine
from src.address import MercuryAddress
from src.auth import InMemoryAccountRepository, LoginStatus
from src.session_manager import LoginSessionManager
from src.audit_logger import AuditLogger
from src.loginapp_core import SyntheticLoginApp, EXPECTED_LOGIN_VERSION
from src.synthetic_client import SyntheticLoginClient
from src.logon_params import salt_password, desalt_password, LogOnParamsError


@pytest.fixture
def rsa_engine():
    """Loads development test RSA keypair."""
    keys_path = os.path.join(os.path.dirname(__file__), '..', 'fixtures', 'keys', 'dev_loginapp_priv.pem')
    return RsaOaepEngine.from_pem_file(keys_path)


@pytest.fixture
def baseapp_endpoint():
    return MercuryAddress(ip="127.0.0.1", port=20014)


@pytest.fixture
def account_repo():
    repo = InMemoryAccountRepository()
    # Accounts: test_user_1 / password123, test_user_2 / secure_pass_456, banned_user / banned_pass
    return repo


@pytest.fixture
def session_manager():
    return LoginSessionManager(session_ttl_seconds=2.0, max_requests_per_minute=10)


@pytest.fixture
def app(rsa_engine, baseapp_endpoint, account_repo, session_manager):
    return SyntheticLoginApp(
        rsa_engine=rsa_engine,
        baseapp_address=baseapp_endpoint,
        account_repo=account_repo,
        session_manager=session_manager
    )


# ==============================================================================
# TC-01: Valid Login Handshake
# ==============================================================================
def test_tc01_valid_login_handshake(app, rsa_engine, baseapp_endpoint):
    client = SyntheticLoginClient(rsa_engine)
    req_datagram = client.build_login_datagram(username="test_user_1", password="password123")

    reply_datagram = app.handle_datagram(req_datagram, client_ip="127.0.0.1")
    assert reply_datagram is not None, "Server must return a reply for valid login."

    req_id, status, address, replacement_key = client.unpack_reply(reply_datagram)
    assert status == LoginStatus.SUCCESS
    assert req_id == client.request_id
    assert isinstance(address, MercuryAddress)
    assert address.ip == baseapp_endpoint.ip
    assert address.port == baseapp_endpoint.port
    assert app.session_manager.active_session_count == 1


# ==============================================================================
# TC-02: Invalid Username (Account Not Found)
# ==============================================================================
def test_tc02_invalid_username(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    req_datagram = client.build_login_datagram(username="non_existent_user_999", password="password123")

    reply_datagram = app.handle_datagram(req_datagram, client_ip="127.0.0.1")
    assert reply_datagram is not None

    req_id, status, error_msg, _ = client.unpack_reply(reply_datagram)
    assert status == LoginStatus.NOT_FOUND
    assert req_id == client.request_id
    assert "does not exist" in error_msg.lower()
    assert app.session_manager.active_session_count == 0


# ==============================================================================
# TC-03: Invalid Password (Bad Password)
# ==============================================================================
def test_tc03_invalid_password(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    req_datagram = client.build_login_datagram(username="test_user_1", password="WRONG_PASSWORD_XYZ")

    reply_datagram = app.handle_datagram(req_datagram, client_ip="127.0.0.1")
    assert reply_datagram is not None

    req_id, status, error_msg, _ = client.unpack_reply(reply_datagram)
    assert status == LoginStatus.BAD_PASSWORD
    assert req_id == client.request_id
    assert "incorrect password" in error_msg.lower()
    assert app.session_manager.active_session_count == 0


# ==============================================================================
# TC-04: Malformed RSA Ciphertext
# ==============================================================================
def test_tc04_malformed_rsa_ciphertext(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    req_datagram = client.build_login_datagram(
        username="test_user_1", password="password123", corrupt_rsa=True
    )

    reply_datagram = app.handle_datagram(req_datagram, client_ip="127.0.0.1")
    assert reply_datagram is not None

    req_id, status, error_msg, _ = client.unpack_reply(reply_datagram)
    assert status == LoginStatus.MALFORMED_REQUEST
    assert "rsa" in error_msg.lower()


# ==============================================================================
# TC-05: Invalid Login Version
# ==============================================================================
def test_tc05_invalid_login_version(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    # Native client is 43; test with 42 and 44
    req_datagram = client.build_login_datagram(
        username="test_user_1", password="password123", version=42
    )

    reply_datagram = app.handle_datagram(req_datagram, client_ip="127.0.0.1")
    assert reply_datagram is not None

    req_id, status, error_msg, _ = client.unpack_reply(reply_datagram)
    assert status == LoginStatus.VERSION_MISMATCH
    assert "version mismatch" in error_msg.lower()


# ==============================================================================
# TC-06: Request ID Correlation
# ==============================================================================
def test_tc06_request_id_correlation(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    arbitrary_req_id = 0x76543210
    req_datagram = client.build_login_datagram(
        username="test_user_1", password="password123", request_id=arbitrary_req_id
    )

    reply_datagram = app.handle_datagram(req_datagram, client_ip="127.0.0.1")
    assert reply_datagram is not None

    req_id, status, address, _ = client.unpack_reply(reply_datagram)
    assert status == LoginStatus.SUCCESS
    assert req_id == arbitrary_req_id


# ==============================================================================
# TC-07: Invalid Mercury Flags (Missing HAS_REQUESTS)
# ==============================================================================
def test_tc07_invalid_mercury_flags(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    # Send packet without FLAG_HAS_REQUESTS (0x0001)
    req_datagram = client.build_login_datagram(
        username="test_user_1", password="password123", override_flags=0x0040 # Only HAS_SEQUENCE_NUMBER
    )

    reply_datagram = app.handle_datagram(req_datagram, client_ip="127.0.0.1")
    # Datagram without HAS_REQUESTS must be dropped
    assert reply_datagram is None


# ==============================================================================
# TC-08: Invalid Session Key Length
# ==============================================================================
def test_tc08_invalid_session_key_length(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    # Attempt with 32-byte key instead of 56 bytes
    with pytest.raises(LogOnParamsError):
        # Client serializer itself enforces 56 bytes
        client.build_login_datagram(
            username="test_user_1", password="password123", override_session_key=b'A' * 32
        )


# ==============================================================================
# TC-09: Replayed Login Nonce (Replay Attack Defense)
# ==============================================================================
def test_tc09_replayed_login_nonce(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    reused_nonce = os.urandom(16)

    # First request: should succeed
    req1 = client.build_login_datagram(
        username="test_user_1", password="password123", override_nonce=reused_nonce
    )
    rep1 = app.handle_datagram(req1, client_ip="127.0.0.1")
    assert rep1 is not None

    # Second request with identical nonce: must be dropped as replay attack
    req2 = client.build_login_datagram(
        username="test_user_1", password="password123", override_nonce=reused_nonce
    )
    rep2 = app.handle_datagram(req2, client_ip="127.0.0.1")
    assert rep2 is None, "Replay attack with identical nonce must be dropped."


# ==============================================================================
# TC-10: Rate Limiting Enforcement
# ==============================================================================
def test_tc10_rate_limiting(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    client_ip = "192.168.1.100"

    # Limit is 10 rpm in fixture
    allowed_count = 0
    for i in range(15):
        # Unique nonce per request
        req = client.build_login_datagram(
            username="test_user_1", password="password123", override_nonce=os.urandom(16)
        )
        rep = app.handle_datagram(req, client_ip=client_ip)
        if rep is not None:
            allowed_count += 1

    assert allowed_count == 10, f"Expected exactly 10 requests allowed, got {allowed_count}."


# ==============================================================================
# TC-11: BaseApp Endpoint Validity
# ==============================================================================
def test_tc11_baseapp_endpoint_validity(app, rsa_engine):
    custom_endpoint = MercuryAddress(ip="10.0.0.50", port=25000)
    app.baseapp_address = custom_endpoint

    client = SyntheticLoginClient(rsa_engine)
    req = client.build_login_datagram(username="test_user_1", password="password123")
    rep = app.handle_datagram(req, client_ip="127.0.0.1")

    _, status, address, _ = client.unpack_reply(rep)
    assert status == LoginStatus.SUCCESS
    assert address.ip == "10.0.0.50"
    assert address.port == 25000


# ==============================================================================
# TC-12: Concurrent Synthetic Sessions
# ==============================================================================
def test_tc12_concurrent_sessions(app, rsa_engine):
    # Authenticate 10 distinct synthetic clients
    clients = []
    for i in range(10):
        # Add synthetic account
        username = f"concurrent_user_{i}"
        password = f"pass_{i}_xyz"
        app.account_repo.add_account(2000 + i, username, password)

        cli = SyntheticLoginClient(rsa_engine)
        req = cli.build_login_datagram(username=username, password=password)
        rep = app.handle_datagram(req, client_ip=f"10.0.0.{100 + i}")
        assert rep is not None

        _, status, _, _ = cli.unpack_reply(rep)
        assert status == LoginStatus.SUCCESS
        clients.append(cli)

    assert app.session_manager.active_session_count == 10


# ==============================================================================
# Additional Tests: Banned Accounts, Salt Reversal, Logging
# ==============================================================================
def test_banned_account_rejection(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    req = client.build_login_datagram(username="banned_user", password="banned_pass")
    rep = app.handle_datagram(req, client_ip="127.0.0.1")

    _, status, error_msg, _ = client.unpack_reply(rep)
    assert status == LoginStatus.BANNED
    assert "suspended" in error_msg.lower()


def test_password_salt_reversal():
    raw_pass = "MySecretP@ssword2026!"
    salted = salt_password(raw_pass)
    assert salted.startswith("aec05336")
    assert raw_pass not in salted # Obfuscated

    recovered = desalt_password(salted)
    assert recovered == raw_pass


def test_session_expiration(app, rsa_engine):
    client = SyntheticLoginClient(rsa_engine)
    req = client.build_login_datagram(username="test_user_1", password="password123")
    rep = app.handle_datagram(req, client_ip="127.0.0.1")
    assert rep is not None
    assert app.session_manager.active_session_count == 1

    # Wait for TTL to expire (fixture session_ttl_seconds = 2.0s)
    time.sleep(2.1)
    assert app.session_manager.active_session_count == 0


def test_no_credential_leak_in_logs():
    logger = AuditLogger()
    event = logger.log_event(
        "TEST_EVENT", "127.0.0.1",
        username="test_user_1",
        password="SUPER_SECRET_PASSWORD",
        plain_password="SUPER_SECRET_PASSWORD",
        session_key=b'X' * 56
    )
    assert "password" not in event
    assert "plain_password" not in event
    assert "session_key" not in event
    assert event["username"] == "test_user_1"
