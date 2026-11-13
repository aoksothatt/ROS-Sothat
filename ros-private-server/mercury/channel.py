"""
Mercury virtual channel maintaining sequenced, reliable transmission over UDP.
Tracks sliding windows, ACKs, retransmissions, and overflow limits.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from app.logging_config import get_logger
from mercury.constants import (
    FLAG_HAS_ACKS,
    FLAG_HAS_SEQUENCE_NUMBER,
    FLAG_RELIABLE,
    MAX_WINDOW_SIZE,
)
from mercury.message import MercuryMessage
from mercury.packet import MercuryPacket

logger = get_logger("mercury.channel")


class ChannelState(Enum):
    INITIALIZING = "INITIALIZING"
    ESTABLISHED = "ESTABLISHED"
    DISCONNECTED = "DISCONNECTED"


class ChannelOverflowError(Exception):
    """Raised when channel sliding window capacity is exceeded."""
    pass


class MercuryChannel:
    """
    Implements a bidirectional reliable virtual channel.
    Manages sequence numbers and sliding window limits as verified from
    neox::bwclient::Mercury::Channel and ServerConnection::send disassembly.
    """

    def __init__(self, address: Tuple[str, int], channel_id: Optional[int] = None):
        self.address = address
        self.channel_id = channel_id
        self.state = ChannelState.INITIALIZING

        # Outgoing Sequence & Sliding Window
        self.large_out_seq_at: int = 0         # Next outgoing sequence number to assign
        self.oldest_unacked_seq: int = 0       # Oldest unacknowledged outgoing packet
        self.unacked_packets: Dict[int, MercuryPacket] = {}

        # Incoming Sequence & Deduplication
        self.expected_in_seq: int = 0
        self.received_seqs: Set[int] = set()
        self.pending_acks: List[int] = []

    @property
    def send_wind_usage(self) -> int:
        """Current sliding window usage count."""
        return self.large_out_seq_at - self.oldest_unacked_seq

    def create_packet(
        self,
        body: bytes = b"",
        reliable: bool = True,
        extra_flags: int = 0
    ) -> MercuryPacket:
        """
        Creates an outgoing packet, assigning sequence numbers and attaching pending ACKs.
        Enforces channel overflow limits.
        """
        if self.state == ChannelState.DISCONNECTED:
            raise RuntimeError(f"Cannot send on disconnected channel {self.address}")

        # Check window capacity limit (256 packets)
        if reliable and self.send_wind_usage >= MAX_WINDOW_SIZE:
            self.state = ChannelState.DISCONNECTED
            err_msg = (
                f"ServerConnection::send: Disconnecting since channel has overflowed "
                f"largeOutSeqAt {self.large_out_seq_at}, oldestUnackedSeq {self.oldest_unacked_seq}, "
                f"sendWindUsage {self.send_wind_usage}"
            )
            logger.error(err_msg)
            raise ChannelOverflowError(err_msg)

        flags = extra_flags
        seq_num: Optional[int] = None

        if reliable:
            flags |= (FLAG_RELIABLE | FLAG_HAS_SEQUENCE_NUMBER)
            seq_num = self.large_out_seq_at
            self.large_out_seq_at += 1

        # Attach pending ACKs (up to 32 at once)
        attached_acks: List[int] = []
        if self.pending_acks:
            flags |= FLAG_HAS_ACKS
            attached_acks = self.pending_acks[:32]
            self.pending_acks = self.pending_acks[32:]

        packet = MercuryPacket(
            flags=flags,
            seq_num=seq_num,
            acks=attached_acks,
            indexed_channel_id=self.channel_id,
            body=body
        )

        if reliable and seq_num is not None:
            self.unacked_packets[seq_num] = packet

        return packet

    def receive_packet(self, packet: MercuryPacket) -> Tuple[bool, List[MercuryMessage]]:
        """
        Process an incoming packet, queueing ACKs and validating in-order sequencing.
        Returns:
            (is_duplicate, unpacked_messages)
        """
        if self.state == ChannelState.INITIALIZING:
            self.state = ChannelState.ESTABLISHED
            logger.info(f"Mercury channel established with {self.address}")

        # Process incoming ACKs first
        if packet.acks:
            self.process_acks(packet.acks)

        # Handle packet sequence number and queuing ACKs
        is_duplicate = False
        if packet.seq_num is not None:
            # Always acknowledge receipt of sequenced packet
            self.pending_acks.append(packet.seq_num)

            if packet.seq_num in self.received_seqs:
                logger.debug(f"Duplicate packet received: seq {packet.seq_num} from {self.address}")
                is_duplicate = True
            else:
                self.received_seqs.add(packet.seq_num)
                if packet.seq_num == self.expected_in_seq:
                    self.expected_in_seq += 1
                elif packet.seq_num > self.expected_in_seq:
                    logger.debug(
                        f"Out-of-order packet: expected {self.expected_in_seq}, got {packet.seq_num}"
                    )

        if is_duplicate:
            return True, []

        messages = MercuryMessage.decode_stream(packet.body)
        return False, messages

    def process_acks(self, ack_list: List[int]) -> None:
        """Processes remote ACKs, removing confirmed packets and sliding the window forward."""
        for ack in ack_list:
            if ack in self.unacked_packets:
                del self.unacked_packets[ack]
                logger.debug(f"Packet seq #{ack} acknowledged by {self.address}")

        # Advance oldest_unacked_seq to the lowest remaining unacked packet
        if self.unacked_packets:
            self.oldest_unacked_seq = min(self.unacked_packets.keys())
        else:
            self.oldest_unacked_seq = self.large_out_seq_at

    def disconnect(self) -> None:
        """Mark channel as disconnected."""
        self.state = ChannelState.DISCONNECTED
        self.unacked_packets.clear()
        self.pending_acks.clear()
        logger.info(f"Mercury channel with {self.address} closed.")
