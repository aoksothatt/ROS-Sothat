"""
Synthetic LoginApp Core Service.

Coordinates the end-to-end authentication pipeline:
1. Ingests raw Mercury datagram.
2. Unpacks framing and footers.
3. Demuxes BigWorld bundle header (MsgID 0x00, Ver 43).
4. Decrypts RSA-OAEP envelope.
5. Deserializes LogOnParams (User, Salted Password, 56B Blowfish Key, Nonce).
6. Verifies replay defense (Nonce & Rate limits).
7. Authenticates with account repository.
8. Encrypts BaseApp address with 56B Blowfish key.
9. Emits correlated LoginReply datagram.
"""

from typing import Optional, Tuple
import struct
import time

from .mercury_parser import MercuryParser, MercuryFramingError, FLAG_HAS_REQUESTS, FLAG_HAS_SEQUENCE_NUMBER
from .bundle_parser import BundleParser, BundleParsingError
from .crypto import RsaOaepEngine, RsaDecryptionError
from .logon_params import LogOnParams, LogOnParamsError
from .auth import InMemoryAccountRepository, LoginStatus, AuthResult
from .session_manager import LoginSessionManager
from .address import MercuryAddress
from .blowfish_filter import BlowfishFilterError
from .login_reply import LoginReplyBuilder
from .audit_logger import AuditLogger


EXPECTED_LOGIN_VERSION = 43


class SyntheticLoginApp:
    """The central synthetic LoginApp server instance."""

    def __init__(
        self,
        rsa_engine: RsaOaepEngine,
        baseapp_address: Optional[MercuryAddress] = None,
        account_repo: Optional[InMemoryAccountRepository] = None,
        session_manager: Optional[LoginSessionManager] = None,
        audit_logger: Optional[AuditLogger] = None
    ):
        self.rsa_engine = rsa_engine
        self.baseapp_address = baseapp_address or MercuryAddress(ip="127.0.0.1", port=20014)
        self.account_repo = account_repo or InMemoryAccountRepository()
        self.session_manager = session_manager or LoginSessionManager()
        self.audit_logger = audit_logger or AuditLogger()
        self._server_seq = 100

    def handle_datagram(self, datagram: bytes, client_ip: str = "127.0.0.1") -> Optional[bytes]:
        """
        Processes a single incoming Mercury datagram and returns the Mercury reply datagram (or None).
        """
        start_time = time.time()

        # 1. Rate Limiting Check
        if not self.session_manager.check_rate_limit(client_ip):
            self.audit_logger.log_event("RATE_LIMITED", client_ip)
            return None

        # 2. Mercury Framing Unpack
        try:
            frame = MercuryParser.unpack(datagram)
        except MercuryFramingError as e:
            self.audit_logger.log_event("MALFORMED_MERCURY_FRAME", client_ip, error=str(e))
            return None

        # Validate mandatory initial packet flags
        if not (frame.flags & FLAG_HAS_REQUESTS):
            self.audit_logger.log_event("MISSING_HAS_REQUESTS_FLAG", client_ip, flags=frame.flags)
            return None

        client_seq = frame.seq_num
        self._server_seq += 1

        # 3. BigWorld Bundle Unpack
        try:
            msg = BundleParser.unpack_login_request(frame.payload)
        except BundleParsingError as e:
            self.audit_logger.log_event("MALFORMED_BUNDLE", client_ip, error=str(e))
            return None

        request_id = msg.request_id

        # 4. Login Version Validation
        if len(msg.body) < 4:
            self.audit_logger.log_event("TRUNCATED_BODY", client_ip, request_id=request_id)
            return LoginReplyBuilder.build_failure_reply(
                request_id=request_id,
                status=LoginStatus.MALFORMED_REQUEST,
                error_message="Body too short for login version.",
                seq_num=self._server_seq,
                ack_seq=client_seq
            )

        login_version = struct.unpack('<I', msg.body[:4])[0]
        if login_version != EXPECTED_LOGIN_VERSION:
            self.audit_logger.log_event(
                "VERSION_MISMATCH", client_ip,
                expected=EXPECTED_LOGIN_VERSION, received=login_version, request_id=request_id
            )
            return LoginReplyBuilder.build_failure_reply(
                request_id=request_id,
                status=LoginStatus.VERSION_MISMATCH,
                error_message=f"Protocol version mismatch: expected {EXPECTED_LOGIN_VERSION}, got {login_version}.",
                seq_num=self._server_seq,
                ack_seq=client_seq
            )

        ciphertext = msg.body[4:]

        # 5. RSA-OAEP Decryption
        try:
            plaintext = self.rsa_engine.decrypt(ciphertext)
        except RsaDecryptionError as e:
            self.audit_logger.log_event("RSA_DECRYPTION_FAILED", client_ip, request_id=request_id, error=str(e))
            return LoginReplyBuilder.build_failure_reply(
                request_id=request_id,
                status=LoginStatus.MALFORMED_REQUEST,
                error_message="Malformed RSA encryption envelope.",
                seq_num=self._server_seq,
                ack_seq=client_seq
            )

        # 6. LogOnParams Deserialization
        try:
            params = LogOnParams.deserialize(plaintext, reverse_client_salt=True)
        except LogOnParamsError as e:
            self.audit_logger.log_event("LOGONPARAMS_PARSE_FAILED", client_ip, request_id=request_id, error=str(e))
            return LoginReplyBuilder.build_failure_reply(
                request_id=request_id,
                status=LoginStatus.MALFORMED_REQUEST,
                error_message=f"Invalid login parameters: {e}",
                seq_num=self._server_seq,
                ack_seq=client_seq
            )

        # 7. Replay Protection Check
        if not self.session_manager.check_and_record_nonce(params.client_nonce):
            self.audit_logger.log_event(
                "REPLAY_ATTACK_DETECTED", client_ip,
                username=params.username, request_id=request_id, nonce=params.client_nonce.hex()
            )
            # Replay attack: drop packet immediately
            return None

        # 8. User Authentication
        auth_result = self.account_repo.authenticate(params.username, params.password)

        latency_ms = (time.time() - start_time) * 1000.0

        if auth_result.status != LoginStatus.SUCCESS:
            self.audit_logger.log_event(
                "LOGIN_FAILED", client_ip,
                username=params.username, status=auth_result.status.name,
                request_id=request_id, latency_ms=latency_ms
            )
            return LoginReplyBuilder.build_failure_reply(
                request_id=request_id,
                status=auth_result.status,
                error_message=auth_result.error_message,
                seq_num=self._server_seq,
                ack_seq=client_seq
            )

        # 9. Successful Authentication -> Create Session
        session = self.session_manager.create_session(
            account_id=auth_result.account_id,
            username=auth_result.username,
            session_key=params.session_key,
            client_nonce=params.client_nonce,
            client_ip=client_ip
        )

        self.audit_logger.log_event(
            "LOGIN_SUCCESS", client_ip,
            account_id=auth_result.account_id, username=auth_result.username,
            request_id=request_id, latency_ms=latency_ms
        )

        # 10. Construct LoginReply with Blowfish-Encrypted BaseApp Address
        try:
            reply_datagram = LoginReplyBuilder.build_success_reply(
                request_id=request_id,
                baseapp_addr=self.baseapp_address,
                session_key=params.session_key,
                seq_num=self._server_seq,
                ack_seq=client_seq
            )
            return reply_datagram
        except BlowfishFilterError as e:
            self.audit_logger.log_event("BLOWFISH_ENCRYPT_FAILED", client_ip, request_id=request_id, error=str(e))
            return None
