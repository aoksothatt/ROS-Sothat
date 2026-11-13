"""
Separate Real UDP Synthetic Client.

Implements an operational network client communicating strictly over actual UDP sockets:
- Transmits raw datagrams to 127.0.0.1:port via socket.socket(AF_INET, SOCK_DGRAM).
- Zero direct calls to SyntheticLoginApp.handle_datagram().
- Parses responses independently using IndependentBigWorldBlowfish.
- Decoupled from server-side Blowfish classes.
"""

from typing import Optional, Dict, Any, Tuple
import socket
import struct
import io
import os
import sys

from .mercury_parser import MercuryParser
from .crypto import RsaOaepEngine
from .synthetic_client import SyntheticLoginClient
from .login_reply import decode_bw_string
from independent_reference.independent_blowfish import IndependentBigWorldBlowfish


class UdpSyntheticClient:
    """
    Network-based synthetic client that communicates with the LoginApp daemon
    strictly through operating system UDP sockets.
    """

    def __init__(
        self,
        rsa_engine: RsaOaepEngine,
        server_host: str = "127.0.0.1",
        server_port: int = 20013,
        timeout: float = 2.0
    ):
        self.rsa_engine = rsa_engine
        self.server_host = server_host
        self.server_port = server_port
        self.timeout = timeout
        self.internal_client = SyntheticLoginClient(rsa_engine)
        self.session_key = self.internal_client.session_key
        self.independent_blowfish = IndependentBigWorldBlowfish(self.session_key)

    def send_raw_datagram(self, datagram: bytes) -> Optional[bytes]:
        """Transmits arbitrary raw bytes over UDP and waits for response."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout)
        try:
            sock.sendto(datagram, (self.server_host, self.server_port))
            reply_bytes, _ = sock.recvfrom(4096)
            return reply_bytes
        except socket.timeout:
            return None
        finally:
            sock.close()

    def login(
        self,
        username: str,
        password: str,
        version: int = 43,
        request_id: Optional[int] = None,
        corrupt_rsa: bool = False,
        override_session_key: Optional[bytes] = None,
        override_nonce: Optional[bytes] = None,
        override_flags: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Builds a login datagram, transmits it over UDP socket, and parses
        the reply independently.
        """
        # 1. Update session key if overridden
        active_key = override_session_key or self.session_key
        self.session_key = active_key
        if len(active_key) == 56:
            self.independent_blowfish = IndependentBigWorldBlowfish(active_key)

        # 2. Build datagram using packet builder
        req_id = request_id if request_id is not None else 100
        datagram = self.internal_client.build_login_datagram(
            username=username,
            password=password,
            version=version,
            request_id=req_id,
            corrupt_rsa=corrupt_rsa,
            override_session_key=override_session_key,
            override_nonce=override_nonce,
            override_flags=override_flags
        )

        # 3. Transmit over UDP socket
        reply_bytes = self.send_raw_datagram(datagram)
        if reply_bytes is None:
            return {"status": "TIMEOUT", "error": "UDP socket timed out waiting for daemon reply"}

        # 4. Independent Parsing of Mercury & BigWorld Reply
        return self.parse_reply_independently(reply_bytes, expected_req_id=req_id)

    def parse_reply_independently(self, datagram: bytes, expected_req_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Parses the LoginReply datagram without importing server cipher code.
        Uses IndependentBigWorldBlowfish to decrypt the address payload.
        """
        frame = MercuryParser.unpack(datagram)
        bundle_data = frame.payload

        if len(bundle_data) < 7:
            raise ValueError(f"Bundle too short: {len(bundle_data)} bytes")

        msg_id, total_len, reply_request_id = struct.unpack('<BHI', bundle_data[:7])
        assert msg_id == 0xFF, f"Expected BigWorld reply message ID 0xFF, got 0x{msg_id:02x}"

        if expected_req_id is not None:
            assert reply_request_id == expected_req_id, (
                f"Request ID mismatch: expected {expected_req_id}, got {reply_request_id}"
            )

        body = bundle_data[7:]
        status_byte = body[0]

        result: Dict[str, Any] = {
            "status_code": status_byte,
            "request_id": reply_request_id,
            "raw_body": body
        }

        if status_byte == 0x01:  # LOGON_STATUS_SUCCESS
            assert len(body) >= 25, f"Success body must be at least 25 bytes, got {len(body)}"
            encrypted_addr = body[1:25]

            # Decrypt address using INDEPENDENT reference oracle
            decrypted_addr = self.independent_blowfish.decrypt(encrypted_addr)
            assert len(decrypted_addr) == 24

            ip_bytes = decrypted_addr[0:4]
            port_bytes = decrypted_addr[4:6]
            padding = decrypted_addr[6:24]

            result["status"] = "SUCCESS"
            result["ip"] = socket.inet_ntoa(ip_bytes)
            result["port"] = struct.unpack("!H", port_bytes)[0]
            result["padding"] = padding
            result["decrypted_addr_raw"] = decrypted_addr
        else:
            stream = io.BytesIO(body[1:])
            error_msg = decode_bw_string(stream)
            result["status"] = "FAILED"
            result["error_message"] = error_msg

        return result
