"""
Synthetic Mercury UDP Test Client
Phase 6.2B.8 - Research & Prototype Only

Strict Localhost Controls:
- Binds strictly to 127.0.0.1 (ephemeral client port).
- Connects strictly to 127.0.0.1:PORT.
- Constructs synthetic Mercury packets with PBC encryption, single-byte padding, and 32-bit XOR checksum.
- Validates returned responses, ACKs, and channel progression.
"""

import socket
import json
import struct
from typing import Dict, Any, List, Optional
from config import GatewayConfig, SecurityError
from protocol_engine import MercuryProtocolEngine, PacketDecryptionError, ChecksumError
from packet_parser import MercuryPacketFlags, MercuryPacketParser


class SyntheticMercuryClient:
    def __init__(
        self,
        session_key: bytes,
        channel_id: int,
        gateway_host: str = GatewayConfig.HOST,
        gateway_port: int = GatewayConfig.PORT,
        timeout: float = 1.5
    ):
        GatewayConfig.validate_bind_address(gateway_host)

        self.session_key = session_key
        self.channel_id = channel_id
        self.gateway_addr = (gateway_host, gateway_port)
        self.engine = MercuryProtocolEngine(session_key)
        self.timeout = timeout
        self.current_seq = 1
        self.last_received_server_seq: Optional[int] = None

        # Create UDP socket bound exclusively to localhost
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))  # strictly 127.0.0.1
        self.sock.settimeout(timeout)

    @property
    def local_port(self) -> int:
        return self.sock.getsockname()[1]

    def send_init(self, session_id: str) -> Dict[str, Any]:
        """
        Sends synthetic channel initialization datagram with FLAG_CREATE_CHANNEL (0x0200).
        """
        payload = json.dumps({"action": "INIT_CHANNEL", "session_id": session_id}).encode("utf-8")
        flags = (
            MercuryPacketFlags.FLAG_CREATE_CHANNEL |
            MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
            MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER |
            MercuryPacketFlags.FLAG_HAS_CHECKSUM
        )

        datagram = self.engine.send_packet(
            payload=payload,
            flags=flags,
            seq_num=self.current_seq,
            channel_id=self.channel_id,
            enable_checksum=True
        )

        self.sock.sendto(datagram, self.gateway_addr)
        self.current_seq = (self.current_seq + 1) & 0x0FFFFFFF

        # Wait for initialization response
        resp = self.receive_response()
        return resp

    def send_message(
        self,
        msg: bytes,
        acks: Optional[List[int]] = None,
        custom_seq: Optional[int] = None,
        is_reliable: bool = False,
        enable_checksum: bool = True
    ) -> Dict[str, Any]:
        """
        Sends an application message packet on the established channel.
        """
        seq = custom_seq if custom_seq is not None else self.current_seq
        flags = (
            MercuryPacketFlags.FLAG_ON_CHANNEL |
            MercuryPacketFlags.FLAG_INDEXED_CHANNEL |
            MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER
        )
        if is_reliable:
            flags |= MercuryPacketFlags.FLAG_IS_RELIABLE
        if enable_checksum:
            flags |= MercuryPacketFlags.FLAG_HAS_CHECKSUM

        datagram = self.engine.send_packet(
            payload=msg,
            flags=flags,
            seq_num=seq,
            channel_id=self.channel_id,
            acks=acks,
            enable_checksum=enable_checksum
        )

        self.sock.sendto(datagram, self.gateway_addr)
        if custom_seq is None:
            self.current_seq = (self.current_seq + 1) & 0x0FFFFFFF

        return self.receive_response()

    def send_raw(self, raw_bytes: bytes):
        """Sends raw bytes to gateway without encryption/framing for security/fuzzing tests."""
        self.sock.sendto(raw_bytes, self.gateway_addr)

    def receive_response(self, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Receives and verifies a Mercury response packet from the gateway."""
        if timeout is not None:
            self.sock.settimeout(timeout)
        else:
            self.sock.settimeout(self.timeout)

        data, addr = self.sock.recvfrom(GatewayConfig.BUFFER_SIZE)
        unpacked = self.engine.receive_packet(data)
        if unpacked.get("seq_num") is not None:
            self.last_received_server_seq = unpacked["seq_num"]
        return unpacked

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
