"""
Backend adapter bridging Mercury transport player sessions to existing FastAPI services.
Maintains architectural isolation between the UDP socket layer and the HTTP/database backend.
"""

import time
import secrets
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from app.logging_config import get_logger
from app.account.service import AccountService
from app.lobby.service import LobbyService
from gateway.constants import (
    SESSION_STATE_AUTHENTICATED,
    SESSION_STATE_DISCONNECTED,
    SESSION_STATE_IN_LOBBY,
)

logger = get_logger("gateway.adapter")


@dataclass
class SessionContext:
    """Represents an active player session established through LoginApp / BaseApp."""
    session_key: int                # 32-bit integer token
    account_id: int
    username: str
    device_id: Optional[str]
    client_addr: Tuple[str, int]
    state: str = SESSION_STATE_AUTHENTICATED
    created_at: float = 0.0
    last_activity: float = 0.0

    def touch(self) -> None:
        self.last_activity = time.time()


class SessionRegistry:
    """In-memory thread-safe registry tracking active player sessions."""

    _instance: Optional['SessionRegistry'] = None

    def __init__(self):
        self._by_session_key: Dict[int, SessionContext] = {}
        self._by_account_id: Dict[int, SessionContext] = {}
        self._by_addr: Dict[Tuple[str, int], SessionContext] = {}

    @classmethod
    def get_instance(cls) -> 'SessionRegistry':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def register_session(self, session: SessionContext) -> None:
        """Register a new active session."""
        self._by_session_key[session.session_key] = session
        self._by_account_id[session.account_id] = session
        self._by_addr[session.client_addr] = session
        logger.info(
            f"Registered session key 0x{session.session_key:08x} for account "
            f"#{session.account_id} ({session.username}) from {session.client_addr}"
        )

    def get_by_session_key(self, session_key: int) -> Optional[SessionContext]:
        return self._by_session_key.get(session_key)

    def get_by_account_id(self, account_id: int) -> Optional[SessionContext]:
        return self._by_account_id.get(account_id)

    def get_by_addr(self, addr: Tuple[str, int]) -> Optional[SessionContext]:
        return self._by_addr.get(addr)

    def remove_session(self, session_key: int) -> Optional[SessionContext]:
        session = self._by_session_key.pop(session_key, None)
        if session:
            self._by_account_id.pop(session.account_id, None)
            self._by_addr.pop(session.client_addr, None)
            session.state = SESSION_STATE_DISCONNECTED
            logger.info(f"Terminated session 0x{session_key:08x} for account #{session.account_id}")
        return session

    def count(self) -> int:
        return len(self._by_session_key)


class BackendAdapter:
    """
    Adapter facade providing high-level integration between the Mercury UDP transport
    and the existing backend services without modifying database records or schemas.
    """

    def __init__(
        self,
        account_service: Optional[AccountService] = None,
        lobby_service: Optional[LobbyService] = None,
        session_registry: Optional[SessionRegistry] = None
    ):
        self.account_service = account_service or AccountService
        self.lobby_service = lobby_service or LobbyService.get_instance()
        self.registry = session_registry or SessionRegistry.get_instance()

    def generate_session_key(self) -> int:
        """Generate a random 32-bit positive integer session key."""
        return secrets.randbits(32)

    def create_guest_session(
        self,
        account_id: int,
        username: str,
        device_id: str,
        client_addr: Tuple[str, int]
    ) -> SessionContext:
        """Constructs and registers a session context for an authenticated guest."""
        session_key = self.generate_session_key()
        now = time.time()
        session = SessionContext(
            session_key=session_key,
            account_id=account_id,
            username=username,
            device_id=device_id,
            client_addr=client_addr,
            state=SESSION_STATE_AUTHENTICATED,
            created_at=now,
            last_activity=now
        )
        self.registry.register_session(session)
        return session

    def bind_lobby_presence(
        self,
        session_key: int,
        gid: int,
        nickname: str = "Player",
        level: int = 1
    ) -> bool:
        """
        Links an authenticated session to the in-memory LobbyService presence tracker.
        Does not alter database state or balances.
        """
        session = self.registry.get_by_session_key(session_key)
        if not session:
            logger.warning(f"Failed to bind lobby presence: session 0x{session_key:08x} not found.")
            return False

        session.state = SESSION_STATE_IN_LOBBY
        session.touch()
        self.lobby_service.enter_lobby(
            account_id=session.account_id,
            gid=gid,
            nickname=nickname,
            level=level
        )
        logger.info(f"Bound lobby presence for account #{session.account_id} (gid #{gid})")
        return True

    def close_session(self, session_key: int, gid: Optional[int] = None) -> None:
        """Closes the player session and prunes lobby presence."""
        session = self.registry.remove_session(session_key)
        if session and gid is not None:
            self.lobby_service.leave_lobby(gid)
