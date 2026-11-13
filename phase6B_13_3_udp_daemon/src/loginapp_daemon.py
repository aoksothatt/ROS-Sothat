"""
Localhost UDP LoginApp Daemon Implementation.

Provides an operational localhost-only UDP daemon for the ROS Sothat private server:
- Strictly bound to 127.0.0.1 (hard-rejects non-loopback addresses).
- Non-blocking asynchronous I/O using asyncio.DatagramProtocol.
- Offloads CPU-intensive cryptographic operations to thread pool.
- Full exception guards to prevent malformed datagrams from terminating the server.
- Structured audit logging with zero credential exposure.
"""

from typing import Optional, Tuple, Any, Dict
import asyncio
import os
import sys
import logging

from .crypto import RsaOaepEngine
from .address import MercuryAddress
from .auth import InMemoryAccountRepository
from .session_manager import LoginSessionManager
from .audit_logger import AuditLogger
from .loginapp_core import SyntheticLoginApp

DEFAULT_LOGINAPP_PORT = 20013
DEFAULT_BASEAPP_PORT = 20014
MAX_DATAGRAM_SIZE = 2048  # Safe standard MTU for UDP bundles


class LoginAppProtocol(asyncio.DatagramProtocol):
    """Asynchronous UDP protocol handler for Mercury datagrams."""

    def __init__(
        self,
        app: SyntheticLoginApp,
        audit_logger: AuditLogger,
        max_datagram_size: int = MAX_DATAGRAM_SIZE
    ):
        self.app = app
        self.logger = audit_logger
        self.max_datagram_size = max_datagram_size
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.loop = asyncio.get_event_loop()
        self.packets_received = 0
        self.packets_sent = 0
        self.packets_dropped = 0
        self.error_count = 0

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = transport  # type: ignore
        sockname = self.transport.get_extra_info("sockname")
        self.logger.log_event(
            "udp_daemon_started",
            client_ip=sockname[0],
            port=sockname[1],
            status="listening"
        )

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        self.packets_received += 1
        client_ip, client_port = addr

        # Guard 1: Reject empty packets
        if not data:
            self.packets_dropped += 1
            self.logger.log_event("empty_datagram_dropped", client_ip=client_ip, port=client_port)
            return

        # Guard 2: Reject oversized datagrams
        if len(data) > self.max_datagram_size:
            self.packets_dropped += 1
            self.logger.log_event(
                "oversized_datagram_dropped",
                client_ip=client_ip,
                port=client_port,
                size=len(data),
                max_size=self.max_datagram_size
            )
            return

        # Offload processing to thread pool to avoid blocking the asyncio event loop
        asyncio.create_task(self._process_datagram_async(data, addr))

    async def _process_datagram_async(self, data: bytes, addr: Tuple[str, int]) -> None:
        client_ip, client_port = addr
        try:
            # Run crypto and bundle unpacking in executor
            loop = asyncio.get_running_loop()
            reply_bytes = await loop.run_in_executor(
                None,
                self.app.handle_datagram,
                data,
                client_ip
            )

            if reply_bytes and self.transport and not self.transport.is_closing():
                self.transport.sendto(reply_bytes, addr)
                self.packets_sent += 1
            elif not reply_bytes:
                self.packets_dropped += 1
        except Exception as exc:
            self.error_count += 1
            self.logger.log_event(
                "packet_processing_error",
                client_ip=client_ip,
                port=client_port,
                error=str(exc)
            )

    def error_received(self, exc: Exception) -> None:
        self.error_count += 1
        self.logger.log_event("socket_error", client_ip="127.0.0.1", error=str(exc))

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.logger.log_event("udp_daemon_stopped", client_ip="127.0.0.1", status="closed")


class LoginAppDaemon:
    """Manages the operational lifecycle of the local UDP LoginApp service."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = DEFAULT_LOGINAPP_PORT,
        app: Optional[SyntheticLoginApp] = None,
        private_key_path: Optional[str] = None,
        baseapp_ip: str = "127.0.0.1",
        baseapp_port: int = DEFAULT_BASEAPP_PORT,
        max_datagram_size: int = MAX_DATAGRAM_SIZE,
        audit_logger: Optional[AuditLogger] = None
    ):
        # Mandatory Security Check: HARD REJECT non-loopback binding
        if host not in ("127.0.0.1", "localhost"):
            raise ValueError(
                f"Security Violation: LoginApp daemon is restricted to 127.0.0.1 (localhost). "
                f"Attempted bind to '{host}' is strictly forbidden."
            )

        self.host = "127.0.0.1" if host == "localhost" else host
        self.port = port
        self.max_datagram_size = max_datagram_size
        self.logger = audit_logger or AuditLogger()

        if app is not None:
            self.app = app
        else:
            if not private_key_path or not os.path.exists(private_key_path):
                raise ValueError(f"Valid private key path required, got: {private_key_path}")
            rsa_engine = RsaOaepEngine.from_pem_file(private_key_path)
            baseapp_addr = MercuryAddress(ip=baseapp_ip, port=baseapp_port)
            self.app = SyntheticLoginApp(
                rsa_engine=rsa_engine,
                baseapp_address=baseapp_addr,
                audit_logger=self.logger
            )

        self.transport: Optional[asyncio.DatagramTransport] = None
        self.protocol: Optional[LoginAppProtocol] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running and self.transport is not None and not self.transport.is_closing()

    @property
    def bound_address(self) -> Optional[Tuple[str, int]]:
        if self.transport:
            return self.transport.get_extra_info("sockname")
        return None

    @property
    def stats(self) -> Dict[str, Any]:
        if self.protocol:
            return {
                "packets_received": self.protocol.packets_received,
                "packets_sent": self.protocol.packets_sent,
                "packets_dropped": self.protocol.packets_dropped,
                "errors": self.protocol.error_count
            }
        return {"packets_received": 0, "packets_sent": 0, "packets_dropped": 0, "errors": 0}

    async def start(self) -> Tuple[str, int]:
        """Starts the UDP listener on 127.0.0.1:port."""
        if self.is_running:
            raise RuntimeError("Daemon is already running.")

        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: LoginAppProtocol(self.app, self.logger, self.max_datagram_size),
            local_addr=(self.host, self.port)
        )
        self.transport = transport  # type: ignore
        self.protocol = protocol  # type: ignore
        self._is_running = True

        bound_addr = self.bound_address
        print(f"[LoginAppDaemon] Bound and listening on UDP {bound_addr[0]}:{bound_addr[1]}")
        return bound_addr

    async def stop(self) -> None:
        """Closes the UDP socket cleanly and releases the port."""
        if self.transport and not self.transport.is_closing():
            self.transport.close()
            # Allow event loop a brief cycle to flush socket closure
            await asyncio.sleep(0.05)
        self._is_running = False
        print("[LoginAppDaemon] UDP socket closed cleanly.")

    async def run_forever(self) -> None:
        """Runs the daemon until cancelled or interrupted."""
        await self.start()
        try:
            while self.is_running:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()


def run_daemon_cli():
    """CLI entry point for running the LoginApp UDP daemon."""
    import argparse
    parser = argparse.ArgumentParser(description="ROS Sothat Localhost UDP LoginApp Daemon")
    parser.add_argument("--host", default="127.0.0.1", help="Binding host (strictly 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_LOGINAPP_PORT, help="Binding UDP port (default: 20013)")
    parser.add_argument("--key", default="fixtures/keys/dev_loginapp_priv.pem", help="Path to RSA private key PEM")
    parser.add_argument("--baseapp-ip", default="127.0.0.1", help="Target BaseApp IP")
    parser.add_argument("--baseapp-port", type=int, default=DEFAULT_BASEAPP_PORT, help="Target BaseApp port")
    args = parser.parse_args()

    daemon = LoginAppDaemon(
        host=args.host,
        port=args.port,
        private_key_path=args.key,
        baseapp_ip=args.baseapp_ip,
        baseapp_port=args.baseapp_port
    )
    try:
        asyncio.run(daemon.run_forever())
    except KeyboardInterrupt:
        print("\n[LoginAppDaemon] Received shutdown signal. Terminating.")


if __name__ == "__main__":
    run_daemon_cli()
