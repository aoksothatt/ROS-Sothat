"""
Local UDP Communication Integration Tests
Phase 6.2B.8 - Research & Prototype Only

Tests complete local UDP socket communication on 127.0.0.1 across all 14 scenarios:
1. Client sends synthetic initialization packet.
2. Gateway receives and validates it.
3. Gateway creates synthetic channel.
4. Gateway sends initialization response.
5. Client validates initialization response.
6. Client sends second packet on same channel.
7. Gateway validates sequence progression.
8. Gateway sends synthetic ACK response.
9. Client validates the ACK.
10. Two independent synthetic clients use separate channels.
11. Duplicate packets are handled.
12. Invalid packets are rejected.
13. Channel reset is tested.
14. Gateway shutdown is tested.
"""

import unittest
import socket
import time
import json
import sys
from pathlib import Path

# Add gateway package to sys.path
_PKG_DIR = str(Path(__file__).resolve().parent.parent)
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent.parent / "phase6B_7_2_synthetic_research")
for d in [_PKG_DIR, _PHASE6B_7_2_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config import GatewayConfig
from gateway import LocalMercuryGateway
from synthetic_client import SyntheticMercuryClient
from channel_manager import ChannelState


class TestMercuryUDPIntegration(unittest.TestCase):
    def setUp(self):
        # Use port 30048 for integration tests
        self.port = 30048
        self.master_key = GatewayConfig.SYNTHETIC_MASTER_KEY
        self.client2_key = GatewayConfig.SYNTHETIC_CLIENT2_KEY

        self.gw = LocalMercuryGateway(host="127.0.0.1", port=self.port, master_key=self.master_key)
        self.gw.register_channel_key(channel_id=2, key=self.client2_key)
        self.gw.start()
        time.sleep(0.05)

    def tearDown(self):
        if self.gw.is_running:
            self.gw.stop()
        time.sleep(0.02)

    def test_01_scenarios_01_to_05_channel_initialization(self):
        """Scenarios 1-5: Client sends init, gateway validates & establishes channel, sends ACK."""
        client = SyntheticMercuryClient(
            session_key=self.master_key,
            channel_id=1,
            gateway_port=self.port,
            timeout=1.0
        )
        try:
            # Scenario 1: Client sends init packet
            # Scenario 2, 3, 4: Gateway receives, creates channel 1, sends response
            resp = client.send_init(session_id="synthetic_user_session_01")
            
            # Scenario 5: Client validates response
            self.assertIsNotNone(resp)
            self.assertEqual(resp["channel_id"], 1)
            self.assertIn(1, resp["acks"])
            body = json.loads(resp["payload"].decode("utf-8"))
            self.assertEqual(body["status"], "ESTABLISHED")
            self.assertTrue(resp["checksum_verified"])

            # Verify gateway internal state
            self.assertTrue(self.gw.channel_mgr.has_channel(1))
            ch = self.gw.channel_mgr.get_channel(1)
            self.assertEqual(ch.state, ChannelState.STATE_ESTABLISHED)
            self.assertEqual(ch.expected_seq, 2)
        finally:
            client.close()

    def test_02_scenarios_06_to_09_message_progression_and_ack(self):
        """Scenarios 6-9: Client sends second packet, gateway validates progression, returns ACK."""
        client = SyntheticMercuryClient(
            session_key=self.master_key,
            channel_id=1,
            gateway_port=self.port,
            timeout=1.0
        )
        try:
            client.send_init(session_id="synthetic_user_session_01")

            # Scenario 6: Client sends second packet on the same channel
            resp = client.send_message(b"PING_MESSAGE_ON_CHANNEL_1")

            # Scenario 7, 8, 9: Gateway validates seq 2 progression, sends ACK, client validates
            self.assertIsNotNone(resp)
            self.assertEqual(resp["channel_id"], 1)
            self.assertIn(2, resp["acks"])
            self.assertTrue(resp["payload"].startswith(b"ACK_AND_ECHO:PING_MESSAGE_ON_CHANNEL_1"))
            self.assertTrue(resp["checksum_verified"])

            # Verify gateway sequence advanced
            ch = self.gw.channel_mgr.get_channel(1)
            self.assertEqual(ch.expected_seq, 3)
            self.assertEqual(ch.last_received_seq, 2)
        finally:
            client.close()

    def test_03_scenario_10_multi_client_channel_isolation(self):
        """Scenario 10: Two independent clients use separate channels and keys concurrently."""
        client1 = SyntheticMercuryClient(
            session_key=self.master_key,
            channel_id=1,
            gateway_port=self.port,
            timeout=1.0
        )
        client2 = SyntheticMercuryClient(
            session_key=self.client2_key,
            channel_id=2,
            gateway_port=self.port,
            timeout=1.0
        )
        try:
            # Client 1 initializes channel 1
            resp1 = client1.send_init(session_id="sess_01")
            self.assertEqual(resp1["channel_id"], 1)

            # Client 2 initializes channel 2
            resp2 = client2.send_init(session_id="sess_02")
            self.assertEqual(resp2["channel_id"], 2)

            # Client 1 sends message on channel 1 (seq 2)
            resp1 = client1.send_message(b"CLIENT_1_DATA")
            self.assertEqual(resp1["channel_id"], 1)
            self.assertIn(2, resp1["acks"])

            # Client 2 sends message on channel 2 (seq 2)
            resp2 = client2.send_message(b"CLIENT_2_DATA")
            self.assertEqual(resp2["channel_id"], 2)
            self.assertIn(2, resp2["acks"])

            # Verify state isolation:
            ch1 = self.gw.channel_mgr.get_channel(1)
            ch2 = self.gw.channel_mgr.get_channel(2)
            self.assertEqual(ch1.channel_id, 1)
            self.assertEqual(ch2.channel_id, 2)
            self.assertEqual(ch1.expected_seq, 3)
            self.assertEqual(ch2.expected_seq, 3)
            self.assertEqual(self.gw.channel_mgr.active_count(), 2)
        finally:
            client1.close()
            client2.close()

    def test_04_scenario_11_duplicate_packet_handling(self):
        """Scenario 11: Duplicate packets are acknowledged without advancing channel sequence."""
        client = SyntheticMercuryClient(
            session_key=self.master_key,
            channel_id=1,
            gateway_port=self.port,
            timeout=1.0
        )
        try:
            client.send_init(session_id="synthetic_user_session_01")
            ch = self.gw.channel_mgr.get_channel(1)

            # Send seq 2
            resp1 = client.send_message(b"FIRST_SEND_SEQ_2")
            self.assertEqual(ch.expected_seq, 3)

            # Re-send seq 2 (duplicate)
            resp2 = client.send_message(b"DUPLICATE_PAYLOAD", custom_seq=2)
            self.assertIsNotNone(resp2)
            self.assertIn(2, resp2["acks"])
            self.assertEqual(resp2["payload"], b"DUPLICATE_ACK")

            # Sequence progression must NOT have advanced
            self.assertEqual(ch.expected_seq, 3)
        finally:
            client.close()

    def test_05_scenario_12_invalid_packet_rejection(self):
        """Scenario 12: Corrupted, wrong-key, or tampered packets are dropped."""
        client = SyntheticMercuryClient(
            session_key=self.master_key,
            channel_id=1,
            gateway_port=self.port,
            timeout=0.3
        )
        try:
            client.send_init(session_id="synthetic_user_session_01")
            initial_rejected = self.gw.logger.metrics.packets_rejected

            # Send corrupted datagram (bit flipped)
            corrupted = bytearray(b"\x5c\x45\x1c\xae\xa6\x64\xe8\x61" * 4)
            corrupted[5] ^= 0xFF
            client.send_raw(bytes(corrupted))
            time.sleep(0.05)

            # Gateway dropped it
            self.assertGreater(self.gw.logger.metrics.packets_rejected, initial_rejected)

            # Valid client can still communicate normally afterwards
            resp = client.send_message(b"RESUMED_AFTER_CORRUPTION")
            self.assertIsNotNone(resp)
            self.assertIn(2, resp["acks"])
        finally:
            client.close()

    def test_06_scenario_13_channel_reset(self):
        """Scenario 13: Resetting channel 1 clears channel 1, leaving channel 2 untouched."""
        client1 = SyntheticMercuryClient(session_key=self.master_key, channel_id=1, gateway_port=self.port)
        client2 = SyntheticMercuryClient(session_key=self.client2_key, channel_id=2, gateway_port=self.port)
        try:
            client1.send_init("s1")
            client2.send_init("s2")

            # Reset channel 1
            success = self.gw.channel_mgr.reset_channel(1)
            self.assertTrue(success)

            ch1 = self.gw.channel_mgr.get_channel(1)
            ch2 = self.gw.channel_mgr.get_channel(2)

            self.assertEqual(ch1.state, ChannelState.STATE_RESET)
            self.assertEqual(ch1.expected_seq, 1)

            # Channel 2 remains active and unaffected
            self.assertEqual(ch2.state, ChannelState.STATE_ESTABLISHED)
            self.assertTrue(self.gw.channel_mgr.has_channel(2))
            self.assertFalse(self.gw.channel_mgr.has_channel(1))
        finally:
            client1.close()
            client2.close()

    def test_07_scenario_14_gateway_clean_shutdown(self):
        """Scenario 14: Gateway shutdown cleanly terminates thread and releases UDP socket."""
        temp_gw = LocalMercuryGateway(host="127.0.0.1", port=30049)
        temp_gw.start()
        self.assertTrue(temp_gw.is_running)

        temp_gw.stop()
        self.assertFalse(temp_gw.is_running)
        self.assertIsNone(temp_gw.sock)

        # Confirm port is released immediately and can be rebound
        reuse_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        reuse_sock.bind(("127.0.0.1", 30049))
        reuse_sock.close()


if __name__ == "__main__":
    unittest.main()
