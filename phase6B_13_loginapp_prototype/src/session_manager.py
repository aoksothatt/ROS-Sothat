"""
Login Session Management and Replay Attack Protection.

Implements:
- 128-bit client nonce deduplication to block replay attacks.
- Ephemeral login session state with 60-second TTL.
- IP-based rate limiting to prevent authentication brute-forcing.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple
import os
import time


@dataclass
class LoginSession:
    """Represents an active post-authentication session ticket."""
    session_token: str
    account_id: int
    username: str
    session_key: bytes
    client_nonce: bytes
    client_ip: str
    created_at: float
    expires_at: float

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class LoginSessionManager:
    """Manages login sessions, replay cache, and rate limits."""

    def __init__(self, session_ttl_seconds: float = 60.0, nonce_ttl_seconds: float = 600.0, max_requests_per_minute: int = 20):
        self._session_ttl = session_ttl_seconds
        self._nonce_ttl = nonce_ttl_seconds
        self._max_rpm = max_requests_per_minute

        self._sessions: Dict[str, LoginSession] = {} # Key: session_token
        self._seen_nonces: Dict[bytes, float] = {}   # Key: nonce, Value: seen_timestamp
        self._ip_attempts: Dict[str, list] = {}      # Key: IP, Value: list of attempt timestamps

    def check_and_record_nonce(self, nonce: bytes) -> bool:
        """
        Validates whether a 16-byte client nonce is fresh.
        Returns True if fresh (valid request); False if already seen (replay attack!).
        """
        now = time.time()
        self._purge_expired_nonces(now)

        if nonce in self._seen_nonces:
            return False

        self._seen_nonces[nonce] = now
        return True

    def check_rate_limit(self, client_ip: str) -> bool:
        """
        Checks whether client IP has exceeded the allowed request rate.
        Returns True if request is allowed, False if rate-limited.
        """
        now = time.time()
        window_start = now - 60.0

        timestamps = self._ip_attempts.setdefault(client_ip, [])
        # Filter timestamps within current 60s window
        self._ip_attempts[client_ip] = [t for t in timestamps if t > window_start]

        if len(self._ip_attempts[client_ip]) >= self._max_rpm:
            return False

        self._ip_attempts[client_ip].append(now)
        return True

    def create_session(
        self,
        account_id: int,
        username: str,
        session_key: bytes,
        client_nonce: bytes,
        client_ip: str
    ) -> LoginSession:
        """
        Creates a new authenticated login session record.
        """
        now = time.time()
        token = os.urandom(24).hex()
        session = LoginSession(
            session_token=token,
            account_id=account_id,
            username=username,
            session_key=session_key,
            client_nonce=client_nonce,
            client_ip=client_ip,
            created_at=now,
            expires_at=now + self._session_ttl
        )
        self._sessions[token] = session
        return session

    def get_session(self, token: str) -> Optional[LoginSession]:
        """Retrieves active session by token, pruning if expired."""
        session = self._sessions.get(token)
        if session and session.is_expired:
            del self._sessions[token]
            return None
        return session

    @property
    def active_session_count(self) -> int:
        now = time.time()
        return sum(1 for s in self._sessions.values() if s.expires_at > now)

    def _purge_expired_nonces(self, now: float):
        cutoff = now - self._nonce_ttl
        expired = [n for n, ts in self._seen_nonces.items() if ts < cutoff]
        for n in expired:
            del self._seen_nonces[n]
