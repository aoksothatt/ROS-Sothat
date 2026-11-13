"""
RSA Handshake research and test harness for the ROS LoginApp protocol.

=============================================================================
PROTOCOL SPECIFICATION & ARCHITECTURAL RESEARCH
=============================================================================

1. Handshake Structure (Recovered from neox::bwclient::ServerConnection):
   Step 1. Client resolves cluster endpoint from server_list_ios.txt (LoginIP:LoginPort).
   Step 2. Client sends probe datagram to measure network latency.
   Step 3. Client loads "entities\\loginapp.pubkey" embedded in client assets.
   Step 4. Client encrypts logon request with RSA public key:
           ServerConnection::logOnBegin server:<ip> username:<name>
   Step 5. LoginApp receives encrypted payload, decrypts using matching RSA private key,
           verifies user ticket / credentials, and issues:
           - Status code (LOGON_STATUS_OK = 0)
           - BaseApp endpoint (<ip>:<port>)
           - Session authentication key (uint32_t sessionKey)
   Step 6. Client initiates Mercury channel with BaseApp:
           BaseAppExtInterface::baseAppLogin(sessionKey)

2. Known vs Unknown Protocol Elements:
   - KNOWN:
     * High-level two-tier handshake architecture (LoginApp -> BaseApp).
     * Exact string literals, error logs, and C++ class symbols in client binary.
     * Status codes: LOGON_STATUS_OK (0), LOGON_STATUS_FAILED (1), etc.
     * Response components: status, BaseApp IP, BaseApp port, 32-bit sessionKey.
     * Post-handshake RPC flow: Account.handshake(deviceInfo, hotfixMd5, authReply).
   - UNKNOWN:
     * Official RSA private key corresponding to embedded entities/loginapp.pubkey.
     * Exact plaintext packing order before RSA encryption in native neox binary.
     * Whether client contains a hidden debug flag to accept plaintext login.

3. Safety & Control:
   This test harness operates strictly on locally generated ephemeral test keys.
   No credentials, passwords, or official server infrastructure are targeted or accessed.
"""

import json
import os
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from gateway.constants import LOGON_STATUS_FAILED, LOGON_STATUS_OK


@dataclass
class LoginHandshakeRequest:
    """Represents decrypted LoginApp logon request fields."""
    username: str
    ticket_or_token: str
    client_version: str
    timestamp: int
    nonce: bytes

    def to_bytes(self) -> bytes:
        payload_dict = {
            "u": self.username,
            "t": self.ticket_or_token,
            "v": self.client_version,
            "ts": self.timestamp,
            "nonce": self.nonce.hex()
        }
        return json.dumps(payload_dict).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> 'LoginHandshakeRequest':
        payload_dict = json.loads(data.decode("utf-8"))
        return cls(
            username=payload_dict["u"],
            ticket_or_token=payload_dict["t"],
            client_version=payload_dict["v"],
            timestamp=payload_dict["ts"],
            nonce=bytes.fromhex(payload_dict["nonce"])
        )


@dataclass
class LoginHandshakeResponse:
    """Represents LoginApp response issued to client."""
    status_code: int
    baseapp_ip: str
    baseapp_port: int
    session_key: int  # 32-bit integer token

    def encode(self) -> bytes:
        """
        Packs status code (uint8), BaseApp IP (null-terminated string or 4-byte IPv4),
        port (uint16), and sessionKey (uint32).
        """
        ip_bytes = self.baseapp_ip.encode("ascii")
        return struct.pack(
            f"<B{len(ip_bytes)}sBHI",
            self.status_code,
            ip_bytes,
            0,  # null terminator
            self.baseapp_port,
            self.session_key
        )

    @classmethod
    def decode(cls, data: bytes) -> 'LoginHandshakeResponse':
        status_code = data[0]
        # find null terminator
        null_idx = data.find(b"\x00", 1)
        if null_idx == -1:
            raise ValueError("Corrupted LoginHandshakeResponse: missing IP terminator")
        baseapp_ip = data[1:null_idx].decode("ascii")
        offset = null_idx + 1
        baseapp_port, session_key = struct.unpack_from("<HI", data, offset)
        return cls(
            status_code=status_code,
            baseapp_ip=baseapp_ip,
            baseapp_port=baseapp_port,
            session_key=session_key
        )


class LocalRSATestHarness:
    """
    Test harness for locally controlled RSA encryption/decryption of the logon handshake.
    Generates isolated 2048-bit RSA keypairs for protocol verification in automated tests.
    """

    def __init__(self, key_size: int = 2048):
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        self._public_key = self._private_key.public_key()

    def get_public_key_pem(self) -> bytes:
        """Export test public key in PEM format."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    def encrypt_logon_request(self, request: LoginHandshakeRequest) -> bytes:
        """Encrypts logon request payload using the local test public key."""
        payload_bytes = request.to_bytes()
        ciphertext = self._public_key.encrypt(
            payload_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext

    def decrypt_logon_request(self, ciphertext: bytes) -> LoginHandshakeRequest:
        """Decrypts logon request ciphertext using the local test private key."""
        plaintext = self._private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return LoginHandshakeRequest.from_bytes(plaintext)

    def process_handshake(
        self,
        ciphertext: bytes,
        baseapp_ip: str = "127.0.0.1",
        baseapp_port: int = 20001
    ) -> LoginHandshakeResponse:
        """
        Simulates LoginApp receiving an encrypted handshake, decrypting credentials,
        and returning an authenticated BaseApp session response.
        """
        try:
            req = self.decrypt_logon_request(ciphertext)
            # Generate random 32-bit session token
            session_key = secrets.randbits(32)
            return LoginHandshakeResponse(
                status_code=LOGON_STATUS_OK,
                baseapp_ip=baseapp_ip,
                baseapp_port=baseapp_port,
                session_key=session_key
            )
        except Exception:
            return LoginHandshakeResponse(
                status_code=LOGON_STATUS_FAILED,
                baseapp_ip="",
                baseapp_port=0,
                session_key=0
            )
