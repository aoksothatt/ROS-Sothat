"""
Channel State Machine Tests for Local Mercury Gateway Prototype
Phase 6.2B.8 - Research & Prototype Only

Tests channel state management and isolation:
- Channel Initialization & State Transitions
- Sequence Progression & Duplicate Detection
- Out-of-Order Handling & Gap Detection
- Piggybacked ACK Queuing & Recovery
- Cross-Channel Isolation (Channel A vs Channel B)
- Independent Channel Reset
- Immunity to Invalid Packet Corruption
"""

import unittest
import sys
from pathlib import Path

# Add gateway package to sys.path
_PKG_DIR = str(Path(__file__).resolve().parent.parent)
_PHASE6B_7_2_DIR = str(Path(__file__).resolve().parent.parent.parent / "phase6B_7_2_synthetic_research")
for d in [_PKG_DIR, _PHASE6B_7_2_DIR]:
    if d not in sys.path:
        sys.path.insert(0, d)

from config import GatewayConfig
from channel_manager import (
    ChannelManager,
    ChannelState,
    UnknownChannelError,
    DuplicatePacketError,
    OutOfOrderPacketError
)


class TestMercuryChannelState(unittest.TestCase):
    def setUp(self):
        self.mgr = ChannelManager()
        self.key1 = GatewayConfig.SYNTHETIC_MASTER_KEY
        self.key2 = GatewayConfig.SYNTHETIC_CLIENT2_KEY

    def test_01_channel_initialization(self):
        """Verify explicit channel initialization creates ESTABLISHED state."""
        ch = self.mgr.create_channel(channel_id=1, session_id="sess_alpha", session_key=self.key1, initial_seq=1)
        self.assertEqual(ch.channel_id, 1)
        self.assertEqual(ch.session_id, "sess_alpha")
        self.assertEqual(ch.state, ChannelState.STATE_ESTABLISHED)
        self.assertEqual(ch.expected_seq, 1)
        self.assertEqual(self.mgr.active_count(), 1)
        self.assertTrue(self.mgr.has_channel(1))
        self.assertFalse(self.mgr.has_channel(999))

    def test_02_sequential_progression(self):
        """Verify that sequential packets correctly advance expected_seq and record last_received_seq."""
        ch = self.mgr.create_channel(channel_id=1, session_id="sess_alpha", session_key=self.key1, initial_seq=1)
        
        status, details = ch.process_incoming_packet({"seq_num": 1, "acks": []})
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(ch.expected_seq, 2)
        self.assertEqual(ch.last_received_seq, 1)

        status, details = ch.process_incoming_packet({"seq_num": 2, "acks": []})
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(ch.expected_seq, 3)
        self.assertEqual(ch.last_received_seq, 2)

    def test_03_duplicate_sequence_detection(self):
        """Verify that duplicate sequence numbers are detected without corrupting state."""
        ch = self.mgr.create_channel(channel_id=1, session_id="sess_alpha", session_key=self.key1, initial_seq=1)
        
        # Seq 1 succeeds
        ch.process_incoming_packet({"seq_num": 1, "acks": []})
        self.assertEqual(ch.expected_seq, 2)

        # Seq 1 repeated -> DUPLICATE
        status, details = ch.process_incoming_packet({"seq_num": 1, "acks": []})
        self.assertEqual(status, "DUPLICATE")
        # Expected sequence remains 2
        self.assertEqual(ch.expected_seq, 2)

        # Older seq 0 -> DUPLICATE
        status, details = ch.process_incoming_packet({"seq_num": 0, "acks": []})
        self.assertEqual(status, "DUPLICATE")
        self.assertEqual(ch.expected_seq, 2)

    def test_04_out_of_order_sequence_handling(self):
        """Verify out-of-order sequence gap is detected explicitly."""
        ch = self.mgr.create_channel(channel_id=1, session_id="sess_alpha", session_key=self.key1, initial_seq=1)
        
        # Packet seq 5 arrives when expecting 1 (gap of 4 packets)
        status, details = ch.process_incoming_packet({"seq_num": 5, "acks": []})
        self.assertEqual(status, "OUT_OF_ORDER")
        # Packet 5 is remembered in seen_seqs
        self.assertIn(5, ch.seen_seqs)
        # Expected seq still waits for 1
        self.assertEqual(ch.expected_seq, 1)

    def test_05_ack_tracking_and_clearing(self):
        """Verify pending ACKs are queued and cleanly popped on send."""
        ch = self.mgr.create_channel(channel_id=1, session_id="sess_alpha", session_key=self.key1, initial_seq=1)
        
        ch.process_incoming_packet({"seq_num": 1, "acks": []})
        ch.process_incoming_packet({"seq_num": 2, "acks": []})
        self.assertEqual(ch.pending_acks, [1, 2])

        popped = ch.pop_pending_acks()
        self.assertEqual(popped, [1, 2])
        self.assertEqual(ch.pending_acks, [])

    def test_06_channel_isolation(self):
        """Verify Channel 1 and Channel 2 have completely separate states."""
        ch1 = self.mgr.create_channel(channel_id=1, session_id="sess_1", session_key=self.key1, initial_seq=10)
        ch2 = self.mgr.create_channel(channel_id=2, session_id="sess_2", session_key=self.key2, initial_seq=20)

        # Process packet on ch1
        ch1.process_incoming_packet({"seq_num": 10, "acks": []})
        self.assertEqual(ch1.expected_seq, 11)
        # ch2 must remain untouched at 20
        self.assertEqual(ch2.expected_seq, 20)
        self.assertEqual(ch2.pending_acks, [])

        # Process packet on ch2
        ch2.process_incoming_packet({"seq_num": 20, "acks": []})
        self.assertEqual(ch2.expected_seq, 21)
        # ch1 must remain at 11
        self.assertEqual(ch1.expected_seq, 11)

    def test_07_independent_channel_reset(self):
        """Verify resetting Channel 1 resets only Channel 1, leaving Channel 2 active."""
        ch1 = self.mgr.create_channel(channel_id=1, session_id="sess_1", session_key=self.key1, initial_seq=1)
        ch2 = self.mgr.create_channel(channel_id=2, session_id="sess_2", session_key=self.key2, initial_seq=1)

        ch1.process_incoming_packet({"seq_num": 1, "acks": []})
        ch2.process_incoming_packet({"seq_num": 1, "acks": []})

        # Reset channel 1
        success = self.mgr.reset_channel(1)
        self.assertTrue(success)
        self.assertEqual(ch1.state, ChannelState.STATE_RESET)
        self.assertEqual(ch1.expected_seq, 1)
        self.assertEqual(len(ch1.seen_seqs), 0)

        # Channel 2 remains ESTABLISHED and active
        self.assertEqual(ch2.state, ChannelState.STATE_ESTABLISHED)
        self.assertEqual(ch2.expected_seq, 2)
        self.assertIn(1, ch2.seen_seqs)

    def test_08_sequence_wraparound_28bit(self):
        """Verify 28-bit sequence wraparound across 0x0FFFFFFF -> 0x00000000."""
        # Initialize channel at max 28-bit sequence: 0x0FFFFFFF
        ch = self.mgr.create_channel(
            channel_id=1,
            session_id="sess_wrap",
            session_key=self.key1,
            initial_seq=ChannelState.SEQ_MASK
        )
        self.assertEqual(ch.expected_seq, 0x0FFFFFFF)

        # Receive 0x0FFFFFFF -> Advances to 0x00000000
        status, details = ch.process_incoming_packet({"seq_num": 0x0FFFFFFF, "acks": []})
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(ch.expected_seq, 0x00000000)
        self.assertEqual(ch.last_received_seq, 0x0FFFFFFF)

        # Receive 0x00000000 -> Advances to 0x00000001
        status, details = ch.process_incoming_packet({"seq_num": 0x00000000, "acks": []})
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(ch.expected_seq, 0x00000001)

        # Receive 0x00000001 -> Advances to 0x00000002
        status, details = ch.process_incoming_packet({"seq_num": 0x00000001, "acks": []})
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(ch.expected_seq, 0x00000002)

    def test_09_half_window_boundary_duplicate_and_old_packets(self):
        """Verify half-window threshold (0x08000000) per native 0x10091b6c0."""
        ch = self.mgr.create_channel(
            channel_id=1,
            session_id="sess_win",
            session_key=self.key1,
            initial_seq=100
        )

        # 1. Packet older than expected (seq 95 < 100):
        # diff = (95 - 100) & 0x0FFFFFFF = 0x0FFFFFFB > 0x08000000 -> DUPLICATE
        status, details = ch.process_incoming_packet({"seq_num": 95, "acks": []})
        self.assertEqual(status, "DUPLICATE")
        self.assertEqual(ch.expected_seq, 100)

        # 2. Forward gap within half-window: diff <= 0x08000000 -> OUT_OF_ORDER
        status, details = ch.process_incoming_packet({"seq_num": 150, "acks": []})
        self.assertEqual(status, "OUT_OF_ORDER")
        self.assertEqual(ch.expected_seq, 100)

        # 3. Wraparound epoch boundary: expected = 0x00000010, incoming = 0x0FFFFFE0 (old epoch)
        ch_wrap = self.mgr.create_channel(
            channel_id=2,
            session_id="sess_wrap2",
            session_key=self.key1,
            initial_seq=0x00000010
        )
        status, details = ch_wrap.process_incoming_packet({"seq_num": 0x0FFFFFE0, "acks": []})
        self.assertEqual(status, "DUPLICATE")
        self.assertEqual(ch_wrap.expected_seq, 0x00000010)

    def test_10_channel_creation_activation_gate(self):
        """Verify native channel activation gate (is_wanting_create_channel & FLAG_CREATE_CHANNEL 0x0200)."""
        ch = self.mgr.create_channel(
            channel_id=1,
            session_id="sess_gate",
            session_key=self.key1,
            initial_seq=1,
            is_pending=True
        )
        self.assertTrue(ch.is_wanting_create_channel)
        self.assertEqual(ch.state, ChannelState.STATE_INITIALIZING)

        # Attempt packet WITHOUT FLAG_CREATE_CHANNEL -> must be REJECTED per 0x1030a31cb
        status, details = ch.process_incoming_packet({
            "flags": 0x0040, # only seq_num
            "seq_num": 1,
            "acks": []
        })
        self.assertEqual(status, "REJECTED")
        self.assertIn("Dropping packet on channel wanting FLAG_CREATE_CHANNEL", details)
        self.assertTrue(ch.is_wanting_create_channel)
        self.assertEqual(ch.state, ChannelState.STATE_INITIALIZING)

        # Send packet WITH FLAG_CREATE_CHANNEL (0x0200) -> Activates channel!
        status, details = ch.process_incoming_packet({
            "flags": 0x0240, # FLAG_CREATE_CHANNEL | FLAG_HAS_SEQUENCE_NUMBER
            "seq_num": 1,
            "acks": []
        })
        self.assertEqual(status, "SUCCESS")
        self.assertFalse(ch.is_wanting_create_channel)
        self.assertEqual(ch.state, ChannelState.STATE_ESTABLISHED)
        self.assertEqual(ch.expected_seq, 2)

        # Subsequent regular packets without 0x0200 succeed normally
        status, details = ch.process_incoming_packet({
            "flags": 0x0040,
            "seq_num": 2,
            "acks": []
        })
        self.assertEqual(status, "SUCCESS")
        self.assertEqual(ch.expected_seq, 3)

    def test_11_ack_queue_accumulation_and_popping(self):
        """Verify ACK queueing on received sequence numbers and sent sequence tracking."""
        ch = self.mgr.create_channel(
            channel_id=1,
            session_id="sess_ack",
            session_key=self.key1,
            initial_seq=1
        )
        ch.record_sent_sequence(500)
        ch.record_sent_sequence(501)

        # Receive sequenced packets -> queued in pending_acks
        ch.process_incoming_packet({"seq_num": 1, "acks": [500]})
        ch.process_incoming_packet({"seq_num": 2, "acks": [501]})

        self.assertEqual(ch.pending_acks, [1, 2])
        self.assertEqual(ch.received_acks, {500, 501})

        # Pop pending ACKs
        popped = ch.pop_pending_acks()
        self.assertEqual(popped, [1, 2])
        self.assertEqual(ch.pending_acks, [])

    def test_12_monotonic_stress_around_28bit_boundary(self):
        """Verify continuous progression through 28-bit sequence wraparound boundary."""
        start_seq = 0x0FFFFF00
        count = 1000
        ch = self.mgr.create_channel(
            channel_id=1,
            session_id="sess_stress",
            session_key=self.key1,
            initial_seq=start_seq
        )
        for i in range(count):
            curr_seq = (start_seq + i) & ChannelState.SEQ_MASK
            status, details = ch.process_incoming_packet({"seq_num": curr_seq, "acks": []})
            self.assertEqual(status, "SUCCESS")

        expected_final = (start_seq + count) & ChannelState.SEQ_MASK
        self.assertEqual(ch.expected_seq, expected_final)


if __name__ == "__main__":
    unittest.main()
