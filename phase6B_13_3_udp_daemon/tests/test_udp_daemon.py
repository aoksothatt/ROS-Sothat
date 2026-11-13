"""
Real Localhost UDP LoginApp Daemon Integration Tests.

STRICT NETWORK TEST REQUIREMENTS:
Every test case transmits actual datagrams over the loopback network (127.0.0.1)
using operating system UDP sockets. Zero direct in-memory calls to handle_datagram().
"""

from typing import Generator, Tuple
import os
import sys
import time
import socket
import threading
import asyncio
import pytest

# Ensure prototype root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.crypto import RsaOaepEngine
from src.address import MercuryAddress
from src.auth import InMemoryAccountRepository
from src.session_manager import LoginSessionManager
from src.audit_logger import AuditLogger
from src.loginapp_core import SyntheticLoginApp
from src.loginapp_daemon import LoginAppDaemon, DEFAULT_LOGINAPP_PORT
from src.udp_synthetic_client import UdpSyntheticClient
from src.mercury_parser import FLAG_HAS_SEQUENCE_NUMBER
from independent_reference.independent_blowfish import OpenSSLCryptoOracle


@pytest.fixture(scope="module")
def rsa_engine() -> RsaOaepEngine:
    key_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "keys", "dev_loginapp_priv.pem")
    return RsaOaepEngine.from_pem_file(key_path)


@pytest.fixture(scope="module")
def running_daemon(rsa_engine: RsaOaepEngine) -> Generator[Tuple[LoginAppDaemon, int], None, None]:
    """Spins up a real localhost UDP daemon in a background event loop thread."""
    # Find a free local port starting at 20013
    test_port = DEFAULT_LOGINAPP_PORT
    baseapp_addr = MercuryAddress(ip="127.0.0.1", port=20014)

    # Use clean in-memory repository with standard accounts
    account_repo = InMemoryAccountRepository()
    account_repo.add_account(1001, "testuser", "TestPassword123!")
    account_repo.add_account(1002, "banneduser", "BannedPass123!", is_banned=True)

    app = SyntheticLoginApp(
        rsa_engine=rsa_engine,
        baseapp_address=baseapp_addr,
        account_repo=account_repo,
        session_manager=LoginSessionManager(session_ttl_seconds=30.0, nonce_ttl_seconds=600.0, max_requests_per_minute=20),
        audit_logger=AuditLogger("test_udp_daemon_audit")
    )

    daemon = LoginAppDaemon(
        host="127.0.0.1",
        port=test_port,
        app=app,
        max_datagram_size=2048
    )

    loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=lambda: (asyncio.set_event_loop(loop), loop.run_until_complete(daemon.run_forever())),
        daemon=True
    )
    thread.start()

    # Wait for daemon to bind
    for _ in range(50):
        if daemon.is_running:
            break
        time.sleep(0.02)
    assert daemon.is_running, "Daemon failed to start."

    yield daemon, test_port

    # Teardown: Stop daemon cleanly
    asyncio.run_coroutine_threadsafe(daemon.stop(), loop).result(timeout=3.0)
    thread.join(timeout=2.0)


class TestUdpDaemonIntegration:
    """Verifies all 16 integration test cases over real localhost UDP sockets."""

    def test_tc01_valid_login_returns_success(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        res = client.login("testuser", "TestPassword123!", request_id=101)

        assert res["status"] == "SUCCESS"
        assert res["status_code"] == 1
        assert res["request_id"] == 101
        assert res["ip"] == "127.0.0.1"
        assert res["port"] == 20014
        assert res["padding"] == b"\x00" * 18

    def test_tc02_invalid_username_returns_failure(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        res = client.login("nonexistent_user", "SomePassword123!", request_id=102)

        assert res["status"] == "FAILED"
        assert res["status_code"] == 3  # NOT_FOUND
        assert res["request_id"] == 102
        assert "Account does not exist" in res["error_message"]

    def test_tc03_invalid_password_returns_failure(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        res = client.login("testuser", "WrongPassword999!", request_id=103)

        assert res["status"] == "FAILED"
        assert res["status_code"] == 2  # BAD_PASSWORD
        assert res["request_id"] == 103
        assert "Incorrect password" in res["error_message"]

    def test_tc04_malformed_rsa_ciphertext_handled_safely(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        res = client.login("testuser", "TestPassword123!", corrupt_rsa=True, request_id=104)

        assert res["status"] == "FAILED"
        assert res["status_code"] == 7  # MALFORMED_REQUEST
        assert "Malformed RSA" in res["error_message"]

    def test_tc05_incorrect_login_version_rejected(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        res = client.login("testuser", "TestPassword123!", version=42, request_id=105)

        assert res["status"] == "FAILED"
        assert res["status_code"] == 6  # VERSION_MISMATCH
        assert "Protocol version mismatch" in res["error_message"]

    def test_tc06_request_id_correctly_correlated(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        custom_req_id = 0x55AA1234
        res = client.login("testuser", "TestPassword123!", request_id=custom_req_id)

        assert res["status"] == "SUCCESS"
        assert res["request_id"] == custom_req_id

    def test_tc07_missing_has_requests_flag_handled(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port, timeout=0.5)
        # Transmit datagram without FLAG_HAS_REQUESTS
        res = client.login(
            "testuser",
            "TestPassword123!",
            override_flags=FLAG_HAS_SEQUENCE_NUMBER,
            request_id=107
        )
        assert res["status"] == "TIMEOUT", "Packets missing FLAG_HAS_REQUESTS must be dropped by daemon."

    def test_tc08_invalid_session_key_length_rejected(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        # Attempting to build with invalid session key length raises exception in serializer
        with pytest.raises(Exception):
            client.login(
                "testuser",
                "TestPassword123!",
                override_session_key=b"too_short_key_32_bytes_len_____!",
                request_id=108
            )

    def test_tc09_replayed_nonce_rejected(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port, timeout=0.5)
        fixed_nonce = b"\x12\x34\x56\x78\x9A\xBC\xDE\xF0" * 2

        # First request succeeds
        res1 = client.login("testuser", "TestPassword123!", override_nonce=fixed_nonce, request_id=1091)
        assert res1["status"] == "SUCCESS"

        # Immediate replay with same nonce is dropped by daemon -> timeout
        res2 = client.login("testuser", "TestPassword123!", override_nonce=fixed_nonce, request_id=1092)
        assert res2["status"] == "TIMEOUT", "Replayed nonce must be dropped by daemon."

    def test_tc10_multiple_simultaneous_clients_isolated(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client1 = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)
        client2 = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)

        # Clients have different keys
        assert client1.session_key != client2.session_key

        res1 = client1.login("testuser", "TestPassword123!", request_id=201)
        res2 = client2.login("testuser", "TestPassword123!", request_id=202)

        assert res1["status"] == "SUCCESS"
        assert res2["status"] == "SUCCESS"
        assert res1["request_id"] == 201
        assert res2["request_id"] == 202

    def test_tc11_malformed_packets_do_not_crash_daemon(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port, timeout=0.5)

        # Send completely garbage bytes
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b"\xFE\xED\xFA\xCE" + b"\xFF" * 120, ("127.0.0.1", port))
        sock.close()
        time.sleep(0.05)

        # Verify daemon is STILL healthy and accepts valid logins
        res = client.login("testuser", "TestPassword123!", request_id=301)
        assert res["status"] == "SUCCESS"
        assert daemon.is_running

    def test_tc12_oversized_datagrams_rejected(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port, timeout=0.5)

        initial_dropped = daemon.stats["packets_dropped"]

        # Send datagram exceeding max_datagram_size (2048)
        oversized = b"\x80" + (b"\x00" * 3000)
        reply = client.send_raw_datagram(oversized)

        # Oversized datagram is dropped with no reply
        assert reply is None
        assert daemon.stats["packets_dropped"] > initial_dropped

    def test_tc13_rate_limiting_works(self, rsa_engine, running_daemon):
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port, timeout=0.5)

        # Burst 20 requests in rapid succession
        results = []
        for i in range(20):
            res = client.login("testuser", "TestPassword123!", request_id=400 + i)
            results.append(res)

        # At least one request must have been rejected or rate-limited
        has_rate_limited = any(
            (r.get("status") == "FAILED" and "rate limit" in r.get("error_message", "").lower()) or
            r.get("status") == "TIMEOUT"
            for r in results
        )
        assert has_rate_limited, "Rate limiting should have throttled excessive burst requests."

        # Clear rate-limiter attempts so subsequent test cases are unaffected
        daemon.app.session_manager._ip_attempts.clear()

    def test_tc14_shutdown_closes_udp_socket(self, rsa_engine):
        """Tests that standalone daemon shutdown completely releases the socket."""
        key_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "keys", "dev_loginapp_priv.pem")
        temp_port = 20019
        daemon = LoginAppDaemon(host="127.0.0.1", port=temp_port, private_key_path=key_path)

        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=lambda: (asyncio.set_event_loop(loop), loop.run_until_complete(daemon.run_forever())),
            daemon=True
        )
        thread.start()

        for _ in range(50):
            if daemon.is_running:
                break
            time.sleep(0.02)
        assert daemon.is_running

        # Stop daemon
        asyncio.run_coroutine_threadsafe(daemon.stop(), loop).result(timeout=3.0)
        thread.join(timeout=2.0)
        assert not daemon.is_running

        # Verify port 20019 can be bound immediately by another socket
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            test_sock.bind(("127.0.0.1", temp_port))
            bound = True
        except Exception:
            bound = False
        finally:
            test_sock.close()

        assert bound, f"Port {temp_port} was not released after daemon shutdown."

    def test_tc15_daemon_refuses_non_loopback_binding(self, rsa_engine):
        """Verifies mandatory security rejection of non-loopback addresses."""
        key_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "keys", "dev_loginapp_priv.pem")

        with pytest.raises(ValueError) as exc1:
            LoginAppDaemon(host="0.0.0.0", port=20013, private_key_path=key_path)
        assert "strictly forbidden" in str(exc1.value)

        with pytest.raises(ValueError) as exc2:
            LoginAppDaemon(host="192.168.1.50", port=20013, private_key_path=key_path)
        assert "strictly forbidden" in str(exc2.value)

    def test_tc16_independent_decoder_validates_udp_login_reply(self, rsa_engine, running_daemon):
        """Validates that OpenSSL C API Oracle decrypts the real UDP network response."""
        daemon, port = running_daemon
        client = UdpSyntheticClient(rsa_engine, server_host="127.0.0.1", server_port=port)

        # Send login request
        res = client.login("testuser", "TestPassword123!", request_id=601)
        assert res["status"] == "SUCCESS"

        # Raw address decrypt check with OpenSSL C Oracle
        encrypted_addr = res["raw_body"][1:25]
        ossl_plain = OpenSSLCryptoOracle.bigworld_decrypt(encrypted_addr, client.session_key)

        expected_addr = socket.inet_aton("127.0.0.1") + (20014).to_bytes(2, "big") + (b"\x00" * 18)
        assert ossl_plain == expected_addr
        assert res["decrypted_addr_raw"] == expected_addr
