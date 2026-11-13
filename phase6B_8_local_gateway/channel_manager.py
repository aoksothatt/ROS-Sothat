"""
Stateful Mercury Channel Manager Module
Phase 6.2B.8 - Research & Prototype Only

Tracks stateful communication channels for synthetic clients:
- Channel ID & Synthetic Session Identifier
- Expected Sequence Number & Last Received Sequence Number
- Duplicate Packet Detection
- Sequence Progression & Out-of-Order Tracking
- Outgoing ACK Queue & Received ACK Verification
- Channel Isolation (independent state per channel)
- Explicit Channel Initialization & Independent Reset
"""

import time
import threading
from typing import Dict, Any, List, Optional, Set, Tuple
from protocol_engine import MercuryProtocolEngine, PacketFramingError
from packet_parser import MercuryPacketFlags


class ChannelError(Exception):
    """Base class for channel-related state errors."""
    pass


class UnknownChannelError(ChannelError):
    """Raised when a packet references an unregistered or uninitialized channel."""
    pass


class DuplicatePacketError(ChannelError):
    """Raised when a packet with an already processed sequence number is received."""
    pass


class OutOfOrderPacketError(ChannelError):
    """Raised when a packet arrives with a gap in sequence progression."""
    pass


class ChannelState:
    """
    Maintains state for a single isolated Mercury channel adhering to native BigWorld Mercury rules:
    - 28-bit sequence arithmetic (SEQ_MASK = 0x0FFFFFFF, wraparound at 0x10000000)
    - Half-window comparison (HALF_WINDOW = 0x08000000 per 0x10091b6c0)
    - Channel activation gate (is_wanting_create_channel cleared on FLAG_CREATE_CHANNEL 0x0200)
    - Duplicate & Out-of-order sequence detection
    - Piggybacked ACK accumulation & draining
    """
    STATE_UNINITIALIZED = "UNINITIALIZED"
    STATE_INITIALIZING  = "INITIALIZING"
    STATE_ESTABLISHED   = "ESTABLISHED"
    STATE_RESET         = "RESET"

    SEQ_MASK    = 0x0FFFFFFF  # 28-bit sequence space (0x10091b6bc: and w9, w9, #0xfffffff)
    HALF_WINDOW = 0x08000000  # 2^27 half-window threshold (0x10091b6c0: movk w10, #0x800, lsl #16)
    SEQ_NULL    = 0x10000000  # Sentinel unsequenced sequence number

    def __init__(
        self,
        channel_id: int,
        session_id: str,
        session_key: bytes,
        initial_seq: int = 1,
        is_pending: bool = False
    ):
        self.channel_id = channel_id
        self.session_id = session_id
        self.session_key = session_key
        self.engine = MercuryProtocolEngine(session_key)
        self.is_wanting_create_channel = is_pending
        self.state = self.STATE_INITIALIZING if is_pending else self.STATE_ESTABLISHED
        self.expected_seq = initial_seq & self.SEQ_MASK
        self.last_received_seq: Optional[int] = None
        self.seen_seqs: Set[int] = set()
        self.sent_seqs: Set[int] = set()
        self.pending_acks: List[int] = []
        self.received_acks: Set[int] = set()
        self.last_activity = time.time()
        self._lock = threading.Lock()

    def process_incoming_packet(self, unpacked: Dict[str, Any]) -> Tuple[str, str]:
        """
        Validates sequence number progression, updates ACKs, enforces channel activation,
        and prevents state corruption using native 28-bit modular difference arithmetic.
        Returns (outcome_status, details).
        """
        with self._lock:
            self.last_activity = time.time()
            flags = unpacked.get("flags", 0)
            seq_num = unpacked.get("seq_num")
            acks = unpacked.get("acks") or []
            is_create_channel = bool(flags & MercuryPacketFlags.FLAG_CREATE_CHANNEL) or unpacked.get("is_create_channel", False)

            # 1. Channel Activation Gate (VA 0x100923208 & 0x100923368)
            # If channel is waiting for creation (is_wanting_create_channel == True):
            if self.is_wanting_create_channel:
                if not is_create_channel:
                    # Dropping packet on channel wanting FLAG_CREATE_CHANNEL (0x1030a31cb)
                    return "REJECTED", "Dropping packet on channel wanting FLAG_CREATE_CHANNEL"
                # Arriving packet carries FLAG_CREATE_CHANNEL (0x0200) -> Clear pending flag!
                self.is_wanting_create_channel = False
                self.state = self.STATE_ESTABLISHED

            # 2. Process Piggybacked ACKs (must match packets sent by gateway)
            for ack in acks:
                ack_masked = ack & self.SEQ_MASK
                if ack_masked in self.sent_seqs:
                    self.received_acks.add(ack_masked)

            # 3. Process Sequence Number if present
            if seq_num is not None:
                seq_num = seq_num & self.SEQ_MASK

                # Duplicate detection via seen_seqs
                if seq_num in self.seen_seqs:
                    return "DUPLICATE", f"Packet with seq {seq_num} already processed"

                # Native 28-bit modular difference:
                # diff = (incoming_seq - expected_seq) & 0x0FFFFFFF
                diff = (seq_num - self.expected_seq) & self.SEQ_MASK

                if diff == 0:
                    # Normal in-order packet progression: seq_num == expected_seq
                    self.seen_seqs.add(seq_num)
                    self.last_received_seq = seq_num
                    self.expected_seq = (self.expected_seq + 1) & self.SEQ_MASK
                    self.pending_acks.append(seq_num)
                    return "SUCCESS", f"Sequence advanced to {self.expected_seq}"

                elif diff > self.HALF_WINDOW:
                    # Circular difference > 2^27: sequence is behind/older within circular window
                    return "DUPLICATE", f"Packet seq {seq_num} is behind expected {self.expected_seq} (diff 0x{diff:07x} > 0x{self.HALF_WINDOW:07x})"

                else:
                    # 0 < diff <= HALF_WINDOW: Gap detected (out-of-order forward arrival)
                    self.seen_seqs.add(seq_num)
                    self.pending_acks.append(seq_num)
                    return "OUT_OF_ORDER", f"Received seq {seq_num}, expected {self.expected_seq} (diff {diff})"

            return "SUCCESS", "Unsequenced packet processed"

    def pop_pending_acks(self) -> List[int]:
        """Returns and clears currently pending ACKs to piggyback on outgoing responses."""
        with self._lock:
            acks = list(self.pending_acks)
            self.pending_acks.clear()
            return acks

    def record_sent_sequence(self, seq_num: int):
        with self._lock:
            self.sent_seqs.add(seq_num & self.SEQ_MASK)

    def reset(self):
        """Resets only this channel's state."""
        with self._lock:
            self.state = self.STATE_RESET
            self.is_wanting_create_channel = False
            self.expected_seq = 1
            self.last_received_seq = None
            self.seen_seqs.clear()
            self.pending_acks.clear()
            self.sent_seqs.clear()
            self.received_acks.clear()
            self.last_activity = time.time()


class ChannelManager:
    """Manages all active synthetic Mercury channels with strict isolation."""
    def __init__(self):
        self._channels: Dict[int, ChannelState] = {}
        self._lock = threading.Lock()

    def create_channel(
        self,
        channel_id: int,
        session_id: str,
        session_key: bytes,
        initial_seq: int = 1,
        is_pending: bool = False
    ) -> ChannelState:
        with self._lock:
            if channel_id in self._channels and self._channels[channel_id].state in (ChannelState.STATE_ESTABLISHED, ChannelState.STATE_INITIALIZING):
                # Channel already exists, reset it cleanly
                self._channels[channel_id].reset()
                self._channels[channel_id].is_wanting_create_channel = is_pending
                self._channels[channel_id].state = ChannelState.STATE_INITIALIZING if is_pending else ChannelState.STATE_ESTABLISHED
                self._channels[channel_id].expected_seq = initial_seq & ChannelState.SEQ_MASK
                return self._channels[channel_id]

            state = ChannelState(
                channel_id=channel_id,
                session_id=session_id,
                session_key=session_key,
                initial_seq=initial_seq,
                is_pending=is_pending
            )
            self._channels[channel_id] = state
            return state

    def get_channel(self, channel_id: int) -> Optional[ChannelState]:
        with self._lock:
            return self._channels.get(channel_id)

    def has_channel(self, channel_id: int) -> bool:
        with self._lock:
            if channel_id not in self._channels:
                return False
            ch = self._channels[channel_id]
            return ch.state in (ChannelState.STATE_ESTABLISHED, ChannelState.STATE_INITIALIZING)

    def reset_channel(self, channel_id: int) -> bool:
        """Resets the specified channel without touching any other channel."""
        with self._lock:
            if channel_id in self._channels:
                self._channels[channel_id].reset()
                return True
            return False

    def remove_channel(self, channel_id: int) -> bool:
        with self._lock:
            if channel_id in self._channels:
                del self._channels[channel_id]
                return True
            return False

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for c in self._channels.values() if c.state in (ChannelState.STATE_ESTABLISHED, ChannelState.STATE_INITIALIZING))
