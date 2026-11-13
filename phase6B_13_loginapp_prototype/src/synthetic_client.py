"""
Synthetic Login Client Test Harness Helper.

Constructs native-compatible Mercury datagrams for testing:
- Generates 56-byte session key and 16-byte nonce.
- Applies client-side password salt ('aec05336' + byte decrement).
- Encrypts LogOnParams using RSA-OAEP SHA-1.
- Packs BigWorld bundle (MsgID 0x00, Length, RequestID, Ver 43).
- Packs Mercury headers (HAS_REQUESTS, HAS_SEQUENCE_NUMBER) and footers.
- Unpacks and decrypts LoginReply from server.
"""

from typing import Optional, Tuple, Union
import io
import os
import struct

from cryptography.hazmat.primitives.asymmetric import rsa

from .mercury_parser import MercuryParser, FLAG_HAS_REQUESTS, FLAG_HAS_SEQUENCE_NUMBER
from .bundle_parser import encode_bw_string
from .crypto import RsaOaepEngine
from .logon_params import LogOnParams
from .address import MercuryAddress
from .auth import LoginStatus
from .login_reply import LoginReplyBuilder


class SyntheticLoginClient:
    """Emulates the original client network output for offline testing."""

    def __init__(self, rsa_engine: RsaOaepEngine, client_ip: str = "127.0.0.1"):
        self.rsa_engine = rsa_engine
        self.client_ip = client_ip
        self.session_key = os.urandom(56) # Exactly 56 bytes
        self.client_nonce = os.urandom(16) # 16 bytes
        self.seq_num = 1
        self.request_id = 100

    def build_login_datagram(
        self,
        username: str,
        password: str,
        version: int = 43,
        request_id: Optional[int] = None,
        flags: Optional[int] = None,
        corrupt_rsa: bool = False,
        override_session_key: Optional[bytes] = None,
        override_nonce: Optional[bytes] = None,
        override_flags: Optional[int] = None
    ) -> bytes:
        """
        Builds a complete Mercury UDP datagram matching native client output.
        Supports parameter overrides for testing protocol edge cases.
        """
        curr_req_id = request_id if request_id is not None else self.request_id
        session_key = override_session_key if override_session_key is not None else self.session_key
        nonce = override_nonce if override_nonce is not None else self.client_nonce

        # 1. Build and serialize LogOnParams
        params = LogOnParams(
            logon_type=1,
            username=username,
            password=password,
            session_key=session_key,
            client_nonce=nonce,
            client_flags=0
        )
        plaintext = params.serialize(apply_client_salt=True)

        # 2. Asymmetric RSA-OAEP SHA-1 Encryption
        if corrupt_rsa:
            # Corrupted ciphertext
            ciphertext = b'\xAA' * 256
        else:
            ciphertext = self.rsa_engine.encrypt(plaintext)

        # 3. BigWorld Bundle Envelope
        body = struct.pack('<I', version) + ciphertext
        total_len = 4 + len(body) # RequestID (4B) + Body
        bundle_hdr = struct.pack('<BHI', 0x00, total_len, curr_req_id)
        bundle_data = bundle_hdr + body

        # 4. Mercury Transport Framing
        if override_flags is not None:
            active_flags = override_flags
            req_cnt = 1 if (override_flags & FLAG_HAS_REQUESTS) else 0
            seq = self.seq_num if (override_flags & FLAG_HAS_SEQUENCE_NUMBER) else None
        else:
            active_flags = FLAG_HAS_REQUESTS | FLAG_HAS_SEQUENCE_NUMBER
            req_cnt = 1
            seq = self.seq_num

        return MercuryParser.pack(
            payload=bundle_data,
            flags=active_flags,
            seq_num=seq,
            request_count=req_cnt
        )

    def unpack_reply(
        self,
        datagram: bytes
    ) -> Tuple[int, LoginStatus, Union[MercuryAddress, str], Optional[bytes]]:
        """
        Unpacks and verifies the server's reply datagram using the client's session key.
        """
        return LoginReplyBuilder.unpack_reply(datagram, self.session_key)
