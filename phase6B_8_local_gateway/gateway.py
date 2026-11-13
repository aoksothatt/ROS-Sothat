"""
Local Synthetic Mercury UDP Gateway
Phase 6.2B.8 - Research & Prototype Only

Strict Security Controls:
- Binds strictly to 127.0.0.1.
- Immediate startup assertion halts if any non-localhost host is specified.
- Maintains isolated synthetic channels in ChannelManager.
- Decrypts via Blowfish PBC, removes single-byte trailer, verifies 32-bit XOR checksum.
- Rejects malformed, tampered, or unknown channel datagrams without crashing.
"""

import socket
import select
import threading
import json
import struct
from typing import Dict, Any, Optional, Tuple
from config import GatewayConfig, SecurityError
from logging_utils import SafeLogger
from packet_parser import MercuryPacketFlags, MercuryPacketParser, PacketFramingError
from protocol_engine import (
    MercuryProtocolEngine,
    PacketDecryptionError,
    PaddingError,
    ChecksumError
)
from channel_manager import ChannelManager, ChannelState, UnknownChannelError


class LocalMercuryGateway:
    def __init__(
        self,
        host: str = GatewayConfig.HOST,
        port: int = GatewayConfig.PORT,
        master_key: bytes = GatewayConfig.SYNTHETIC_MASTER_KEY
    ):
        # Strict security validation on startup
        GatewayConfig.validate_bind_address(host)

        self.host = host
        self.port = port
        self.master_key = master_key
        self.logger = SafeLogger(name="MercuryGateway")
        self.channel_mgr = ChannelManager()

        # Channel ID -> Session Key registry
        self._key_registry: Dict[int, bytes] = {}
        # Client addr -> Channel ID mapping
        self._addr_to_channel: Dict[Tuple[str, int], int] = {}

        self.sock: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._server_seq = 1000

    def register_channel_key(self, channel_id: int, key: bytes):
        """Pre-registers a synthetic session key for a specific channel ID."""
        self._key_registry[channel_id] = key

    def get_key_for_channel(self, channel_id: Optional[int]) -> bytes:
        if channel_id is not None and channel_id in self._key_registry:
            return self._key_registry[channel_id]
        return self.master_key

    def start(self):
        """Binds to 127.0.0.1 and starts the receiver loop in a daemon thread."""
        GatewayConfig.validate_bind_address(self.host)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(False)

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, name="GatewayWorker", daemon=True)
        self._thread.start()

        self.logger.log(
            direction="INIT",
            channel_id=None,
            length=0,
            seq_num=None,
            outcome="STARTED",
            details=f"Bound strictly to {self.host}:{self.port}"
        )

    def stop(self):
        """Stops the gateway cleanly and releases resources."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

        self.logger.log(
            direction="HALT",
            channel_id=None,
            length=0,
            seq_num=None,
            outcome="STOPPED",
            details="Gateway cleanly shut down"
        )

    @property
    def is_running(self) -> bool:
        return self._running

    def _run_loop(self):
        while self._running:
            try:
                rlist, _, _ = select.select([self.sock], [], [], 0.1)
                if not rlist:
                    continue

                data, client_addr = self.sock.recvfrom(GatewayConfig.BUFFER_SIZE)
                self.logger.metrics.record_received()

                # Process datagram with full exception containment (cannot crash gateway)
                self._handle_datagram(data, client_addr)

            except Exception as e:
                if not self._running:
                    break
                self.logger.log(
                    direction="RECV",
                    channel_id=None,
                    length=0,
                    seq_num=None,
                    outcome="ERROR",
                    error_category="SOCKET_LOOP_EXCEPTION",
                    details=str(e)
                )

    def _resolve_engine(self, data: bytes, client_addr: Tuple[str, int]) -> Tuple[MercuryProtocolEngine, Optional[int]]:
        """
        Attempts to resolve the proper session key engine for incoming datagram.
        """
        # If client address is known, try its registered channel key
        if client_addr in self._addr_to_channel:
            cid = self._addr_to_channel[client_addr]
            key = self.get_key_for_channel(cid)
            return MercuryProtocolEngine(key), cid

        # Fallback to master key engine
        return MercuryProtocolEngine(self.master_key), None

    def _handle_datagram(self, data: bytes, client_addr: Tuple[str, int]):
        length = len(data)

        # 1. Size sanity check
        if length < 8 or length > GatewayConfig.MAX_PACKET_SIZE or length % 8 != 0:
            self.logger.metrics.record_rejected()
            self.logger.log(
                direction="DROP",
                channel_id=None,
                length=length,
                seq_num=None,
                outcome="REJECTED",
                error_category="MALFORMED_DATAGRAM_SIZE"
            )
            return

        # 2. Cryptographic pipeline decryption & verification
        engine, anticipated_cid = self._resolve_engine(data, client_addr)
        try:
            unpacked = engine.receive_packet(data)
        except (PacketDecryptionError, PaddingError, ChecksumError, PacketFramingError) as pe:
            # If anticipated_cid failed, try secondary registered keys before dropping
            recovered = False
            for cid, alt_key in self._key_registry.items():
                if alt_key == engine.session_key:
                    continue
                try:
                    alt_engine = MercuryProtocolEngine(alt_key)
                    unpacked = alt_engine.receive_packet(data)
                    engine = alt_engine
                    recovered = True
                    break
                except Exception:
                    continue

            if not recovered:
                self.logger.metrics.record_rejected()
                err_type = type(pe).__name__
                self.logger.log(
                    direction="DROP",
                    channel_id=anticipated_cid,
                    length=length,
                    seq_num=None,
                    outcome="REJECTED",
                    error_category=err_type,
                    details=str(pe)
                )
                return

        # 3. Channel dispatch & validation
        flags = unpacked["flags"]
        channel_id = unpacked.get("channel_id")
        seq_num = unpacked.get("seq_num")
        payload = unpacked.get("payload", b"")

        # Map client address to channel
        if channel_id is not None:
            self._addr_to_channel[client_addr] = channel_id

        # 4. Handle Channel Initialization (FLAG_CREATE_CHANNEL = 0x0001)
        if flags & MercuryPacketFlags.FLAG_CREATE_CHANNEL:
            self._handle_channel_init(unpacked, engine, client_addr)
            return

        # 5. Handle packets on established channel
        if channel_id is None or not self.channel_mgr.has_channel(channel_id):
            self.logger.metrics.record_rejected()
            self.logger.log(
                direction="DROP",
                channel_id=channel_id,
                length=length,
                seq_num=seq_num,
                outcome="REJECTED",
                error_category="UNKNOWN_CHANNEL",
                details=f"Channel {channel_id} is not initialized"
            )
            return

        channel = self.channel_mgr.get_channel(channel_id)
        outcome, details = channel.process_incoming_packet(unpacked)

        if outcome == "REJECTED":
            self.logger.metrics.record_rejected()
            self.logger.log(
                direction="DROP",
                channel_id=channel_id,
                length=length,
                seq_num=seq_num,
                outcome="REJECTED",
                error_category="CHANNEL_STATE_REJECTION",
                details=details
            )
            return

        if outcome == "DUPLICATE":
            self.logger.log(
                direction="RECV",
                channel_id=channel_id,
                length=length,
                seq_num=seq_num,
                outcome="DUPLICATE",
                details=details
            )
            # Re-send ACK for duplicate so client is not stuck
            self._send_ack_response(channel, client_addr, ack_seq=seq_num)
            return

        if outcome in ("SUCCESS", "OUT_OF_ORDER"):
            self.logger.metrics.record_processed()
            self.logger.log(
                direction="RECV",
                channel_id=channel_id,
                length=length,
                seq_num=seq_num,
                outcome="PROCESSED",
                details=details
            )
            # Process application payload and respond
            self._handle_application_message(channel, client_addr, unpacked)

    def _handle_channel_init(
        self,
        unpacked: Dict[str, Any],
        engine: MercuryProtocolEngine,
        client_addr: Tuple[str, int]
    ):
        channel_id = unpacked.get("channel_id")
        seq_num = unpacked.get("seq_num", 1)
        if channel_id is None:
            self.logger.metrics.record_rejected()
            return

        # Parse session id from payload
        session_id = "default_session"
        try:
            body = json.loads(unpacked["payload"].decode("utf-8"))
            session_id = body.get("session_id", session_id)
        except Exception:
            pass

        # Create isolated state in ChannelManager (active upon receiving FLAG_CREATE_CHANNEL)
        channel = self.channel_mgr.create_channel(
            channel_id=channel_id,
            session_id=session_id,
            session_key=engine.session_key,
            initial_seq=(seq_num + 1) & ChannelState.SEQ_MASK,
            is_pending=False
        )
        self.channel_mgr._channels[channel_id].seen_seqs.add(seq_num & ChannelState.SEQ_MASK)
        self.logger.metrics.update_active_channels(self.channel_mgr.active_count())
        self.logger.metrics.record_processed()

        self.logger.log(
            direction="INIT",
            channel_id=channel_id,
            length=len(unpacked["payload"]),
            seq_num=seq_num,
            outcome="ESTABLISHED",
            details=f"Session {session_id} registered"
        )

        # Build response packet with ACK
        resp_payload = json.dumps({"status": "ESTABLISHED", "channel_id": channel_id}).encode("utf-8")
        self._server_seq = (self._server_seq + 1) & ChannelState.SEQ_MASK
        server_seq = self._server_seq
        channel.record_sent_sequence(server_seq)

        resp_flags = (
            MercuryPacketFlags.FLAG_ON_CHANNEL |
            MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
            MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER |
            MercuryPacketFlags.FLAG_HAS_ACKS |
            MercuryPacketFlags.FLAG_HAS_CHECKSUM
        )

        datagram = channel.engine.send_packet(
            payload=resp_payload,
            flags=resp_flags,
            seq_num=server_seq,
            channel_id=channel_id,
            acks=[seq_num],
            enable_checksum=True
        )

        self.sock.sendto(datagram, client_addr)
        self.logger.metrics.record_sent()
        self.logger.log(
            direction="SEND",
            channel_id=channel_id,
            length=len(datagram),
            seq_num=server_seq,
            outcome="SENT",
            details=f"Init ACK for seq {seq_num}"
        )

    def _handle_application_message(
        self,
        channel: ChannelState,
        client_addr: Tuple[str, int],
        unpacked: Dict[str, Any]
    ):
        seq_num = unpacked.get("seq_num")
        pending_acks = channel.pop_pending_acks()
        if seq_num is not None and seq_num not in pending_acks:
            pending_acks.append(seq_num & ChannelState.SEQ_MASK)

        # Echo / acknowledge application message
        self._server_seq = (self._server_seq + 1) & ChannelState.SEQ_MASK
        server_seq = self._server_seq
        channel.record_sent_sequence(server_seq)

        resp_payload = b"ACK_AND_ECHO:" + unpacked["payload"]
        resp_flags = (
            MercuryPacketFlags.FLAG_ON_CHANNEL |
            MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
            MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER |
            MercuryPacketFlags.FLAG_HAS_ACKS |
            MercuryPacketFlags.FLAG_HAS_CHECKSUM
        )

        datagram = channel.engine.send_packet(
            payload=resp_payload,
            flags=resp_flags,
            seq_num=server_seq,
            channel_id=channel.channel_id,
            acks=pending_acks,
            enable_checksum=True
        )

        self.sock.sendto(datagram, client_addr)
        self.logger.metrics.record_sent()
        self.logger.log(
            direction="SEND",
            channel_id=channel.channel_id,
            length=len(datagram),
            seq_num=server_seq,
            outcome="SENT",
            details=f"ACKed client seqs {pending_acks}"
        )

    def _send_ack_response(self, channel: ChannelState, client_addr: Tuple[str, int], ack_seq: Optional[int]):
        acks = [ack_seq & ChannelState.SEQ_MASK] if ack_seq is not None else []
        self._server_seq = (self._server_seq + 1) & ChannelState.SEQ_MASK
        server_seq = self._server_seq
        channel.record_sent_sequence(server_seq)

        resp_flags = (
            MercuryPacketFlags.FLAG_ON_CHANNEL |
            MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
            MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER |
            MercuryPacketFlags.FLAG_HAS_ACKS |
            MercuryPacketFlags.FLAG_HAS_CHECKSUM
        )

        datagram = channel.engine.send_packet(
            payload=b"DUPLICATE_ACK",
            flags=resp_flags,
            seq_num=server_seq,
            channel_id=channel.channel_id,
            acks=acks,
            enable_checksum=True
        )

        self.sock.sendto(datagram, client_addr)
        self.logger.metrics.record_sent()
