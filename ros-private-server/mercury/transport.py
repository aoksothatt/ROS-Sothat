"""
Mercury asynchronous UDP transport layer using asyncio.DatagramProtocol.
Provides non-blocking socket handling, graceful startup/shutdown, and robust malformed packet isolation.
"""

import asyncio
from typing import Callable, Dict, Optional, Tuple

from app.logging_config import get_logger
from mercury.channel import ChannelState, MercuryChannel
from mercury.constants import FLAG_HAS_ACKS
from mercury.packet import MalformedPacketError, MercuryPacket

logger = get_logger("mercury.transport")


class MercuryProtocol(asyncio.DatagramProtocol):
    """AsyncIO DatagramProtocol implementation for Mercury UDP sockets."""

    def __init__(self, server: 'MercuryTransportServer'):
        self.server = server
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        self.transport = transport
        sock = transport.get_extra_info("socket")
        addr = sock.getsockname() if sock else ("?", "?")
        logger.info(f"Mercury UDP socket bound and listening on {addr[0]}:{addr[1]}")

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        self.server.stats["packets_received"] += 1
        self.server.stats["bytes_received"] += len(data)

        # 1. Parse and validate raw datagram safely
        try:
            packet = MercuryPacket.decode(data)
        except MalformedPacketError as exc:
            self.server.stats["malformed_packets_rejected"] += 1
            logger.warning(f"Rejected malformed Mercury packet from {addr}: {exc}")
            return
        except Exception as exc:
            self.server.stats["malformed_packets_rejected"] += 1
            logger.error(f"Unexpected error decoding packet from {addr}: {exc}", exc_info=True)
            return

        # 2. Retrieve or create virtual channel for this peer
        channel = self.server.get_or_create_channel(addr)

        # 3. Process packet within channel sequence tracking
        is_dup, messages = channel.receive_packet(packet)

        # 4. If packet requested reliable delivery, immediately send back queued ACKs
        if packet.is_reliable() and channel.pending_acks:
            ack_packet = channel.create_packet(body=b"", reliable=False)
            self.send_packet(ack_packet, addr)

        # 5. Notify custom packet/message handler if registered
        if self.server.on_packet_received and not is_dup:
            try:
                self.server.on_packet_received(addr, channel, packet, messages)
            except Exception as e:
                logger.error(f"Error in on_packet_received callback: {e}", exc_info=True)

    def send_packet(self, packet: MercuryPacket, addr: Tuple[str, int]):
        """Encodes and transmits a Mercury packet to destination."""
        if not self.transport or self.transport.is_closing():
            logger.warning(f"Cannot send packet to {addr}: transport is closed.")
            return

        try:
            raw_bytes = packet.encode()
            self.transport.sendto(raw_bytes, addr)
            self.server.stats["packets_sent"] += 1
            self.server.stats["bytes_sent"] += len(raw_bytes)
        except Exception as e:
            logger.error(f"Failed to send packet to {addr}: {e}", exc_info=True)

    def error_received(self, exc: Exception):
        logger.warning(f"UDP socket error received: {exc}")

    def connection_lost(self, exc: Optional[Exception]):
        if exc:
            logger.error(f"UDP socket connection lost with error: {exc}")
        else:
            logger.info("UDP socket closed successfully.")


class MercuryTransportServer:
    """Manages the Mercury UDP socket lifecycle and peer channel connections."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 20001,
        on_packet_received: Optional[Callable] = None
    ):
        self.host = host
        self.port = port
        self.on_packet_received = on_packet_received
        self.channels: Dict[Tuple[str, int], MercuryChannel] = {}
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[MercuryProtocol] = None
        self.is_running: bool = False

        self.stats = {
            "packets_received": 0,
            "packets_sent": 0,
            "bytes_received": 0,
            "bytes_sent": 0,
            "malformed_packets_rejected": 0,
        }

    async def start(self) -> None:
        """Binds and starts the UDP listener."""
        if self.is_running:
            return

        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: MercuryProtocol(self),
            local_addr=(self.host, self.port)
        )
        self.is_running = True
        logger.info(f"Mercury UDP Server started on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Gracefully shuts down the UDP listener and closes channels."""
        if not self.is_running:
            return

        logger.info(f"Stopping Mercury UDP Server on {self.host}:{self.port}...")
        for channel in list(self.channels.values()):
            channel.disconnect()
        self.channels.clear()

        if self.transport and not self.transport.is_closing():
            self.transport.close()

        self.transport = None
        self.protocol = None
        self.is_running = False
        logger.info("Mercury UDP Server stopped.")

    def get_or_create_channel(self, addr: Tuple[str, int]) -> MercuryChannel:
        """Retrieves an existing channel or constructs a new one for this peer."""
        if addr not in self.channels:
            channel = MercuryChannel(addr)
            self.channels[addr] = channel
            logger.debug(f"Created new Mercury channel for {addr}")
        return self.channels[addr]

    def send_packet(self, packet: MercuryPacket, addr: Tuple[str, int]) -> None:
        """Convenience method to transmit via the active protocol."""
        if self.protocol:
            self.protocol.send_packet(packet, addr)
        else:
            logger.warning(f"Cannot send to {addr}: transport not started.")
