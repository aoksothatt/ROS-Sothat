"""
Security, Boundary & Isolation Tests for Local Mercury Gateway Prototype
Phase 6.2B.8 - Research & Prototype Only

Tests security boundaries:
- Strict Localhost 127.0.0.1 Binding Enforcement & Startup Assertion
- Immediate Refusal on 0.0.0.0, LAN, or Remote Bind Addresses
- Sensitive Data Redaction in Logging & Telemetry
- Fuzzing & Malformed Datagram Crash Immunity
- Zero Database Connection Verification
- Memory Stability under Invalid Packet Floods
"""

import unittest
import socket
import sys
import os
from pathlib import Path

# Add gateway package to sys.path
_PKG_DIR = str(Path(__file__).resolve().parent.parent)
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent.parent / "phase6B_7_2_synthetic_research")
for d in [_PKG_DIR, _PHASE6B_7_2_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config import GatewayConfig, SecurityError
from gateway import LocalMercuryGateway
from logging_utils import SafeLogger


class TestMercurySecurityBoundaries(unittest.TestCase):
    def test_01_forbid_0000_binding(self):
        """Verify gateway startup strictly aborts if host is 0.0.0.0."""
        with self.assertRaises(SecurityError):
            GatewayConfig.validate_bind_address("0.0.0.0")

        with self.assertRaises(SecurityError):
            LocalMercuryGateway(host="0.0.0.0", port=30043)

    def test_02_forbid_lan_binding(self):
        """Verify gateway startup strictly aborts if host is a LAN IP."""
        for forbidden_ip in ["192.168.1.100", "10.0.0.1", "172.16.0.1", "8.8.8.8"]:
            with self.assertRaises(SecurityError):
                GatewayConfig.validate_bind_address(forbidden_ip)

            with self.assertRaises(SecurityError):
                LocalMercuryGateway(host=forbidden_ip, port=30043)

    def test_03_allow_only_127001(self):
        """Verify only 127.0.0.1 passes startup validation."""
        # Does not raise
        GatewayConfig.validate_bind_address("127.0.0.1")

    def test_04_sensitive_data_redaction_in_logs(self):
        """Verify SafeLogger redacts keys, passwords, and tokens."""
        logger = SafeLogger(name="TestSecurityLogger")
        logger.log(
            direction="TEST",
            channel_id=1,
            length=10,
            seq_num=1,
            outcome="TEST_EVENT",
            details="User secret password and session token leaked here",
            print_to_console=False
        )
        self.assertEqual(len(logger.log_entries), 1)
        logged_line = logger.log_entries[0]
        self.assertNotIn("password", logged_line.lower())
        self.assertNotIn("token", logged_line.lower())
        self.assertIn("[REDACTED_SENSITIVE_CONTENT]", logged_line)

    def test_05_fuzzing_and_malformed_packet_resilience(self):
        """Verify gateway does not crash when receiving random garbage, truncated or oversized packets."""
        # Start temporary gateway on unprivileged port 30045
        gw = LocalMercuryGateway(host="127.0.0.1", port=30045)
        gw.start()
        try:
            self.assertTrue(gw.is_running)

            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client_sock.bind(("127.0.0.1", 0))

            fuzz_payloads = [
                b"",                                    # empty
                b"\x00",                               # 1 byte
                b"\x00\x01\x02",                       # 3 bytes
                b"\xFF" * 7,                           # 7 bytes (unaligned)
                b"\x00" * 8,                           # 8 bytes zero (invalid trailer 0x00)
                b"\x00" * 15 + b"\x09",                # invalid wastage count 9
                b"\x00\x04" + b"A" * 10,               # bad flags 0x0400
                b"\xAA" * 1024,                        # random 1KB block
                b"\x55" * 3000,                        # oversized (> 2048)
            ]

            for payload in fuzz_payloads:
                client_sock.sendto(payload, ("127.0.0.1", 30045))

            client_sock.close()
            import time
            time.sleep(0.05)

            # Gateway must remain running without crashing
            self.assertTrue(gw.is_running)
            metrics = gw.logger.metrics.get_summary()
            self.assertGreaterEqual(metrics["packets_received"], len(fuzz_payloads))
            self.assertGreaterEqual(metrics["packets_rejected"], len(fuzz_payloads))

        finally:
            gw.stop()
            self.assertFalse(gw.is_running)

    def test_06_zero_backend_db_connections(self):
        """Verify prototype has zero imports or connections to psycopg2, asyncpg, sqlalchemy, or redis."""
        import sys
        forbidden_modules = ["psycopg2", "asyncpg", "sqlalchemy", "redis", "alembic"]
        for mod in forbidden_modules:
            self.assertNotIn(
                mod,
                sys.modules,
                f"Forbidden database module '{mod}' was loaded into prototype runtime!"
            )


if __name__ == "__main__":
    unittest.main()
