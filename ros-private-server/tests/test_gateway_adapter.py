"""
Unit tests for BackendAdapter and SessionRegistry.
Validates:
1. Active session lifecycle tracking.
2. Indexing by session_key, account_id, and socket address.
3. Interfacing with in-memory LobbyService presence.
4. Safe cleanup on disconnect.
"""

import pytest

from app.lobby.service import LobbyService
from gateway.adapter import BackendAdapter, SessionContext, SessionRegistry
from gateway.constants import (
    SESSION_STATE_AUTHENTICATED,
    SESSION_STATE_DISCONNECTED,
    SESSION_STATE_IN_LOBBY,
)


class TestSessionRegistry:
    """Tests for in-memory session registry."""

    def setup_method(self):
        SessionRegistry.reset_instance()

    def test_register_and_lookup_session(self):
        registry = SessionRegistry.get_instance()
        session = SessionContext(
            session_key=0x12345678,
            account_id=42,
            username="Tester42",
            device_id="dev-uuid-001",
            client_addr=("127.0.0.1", 50123)
        )
        registry.register_session(session)

        # Lookup by session_key
        assert registry.get_by_session_key(0x12345678) is session

        # Lookup by account_id
        assert registry.get_by_account_id(42) is session

        # Lookup by addr
        assert registry.get_by_addr(("127.0.0.1", 50123)) is session
        assert registry.count() == 1

    def test_remove_session(self):
        registry = SessionRegistry.get_instance()
        session = SessionContext(
            session_key=0xAABBCCDD,
            account_id=99,
            username="RemoveMe",
            device_id="dev-uuid-002",
            client_addr=("127.0.0.1", 50124)
        )
        registry.register_session(session)
        assert registry.count() == 1

        removed = registry.remove_session(0xAABBCCDD)
        assert removed is session
        assert removed.state == SESSION_STATE_DISCONNECTED
        assert registry.get_by_session_key(0xAABBCCDD) is None
        assert registry.get_by_account_id(99) is None
        assert registry.get_by_addr(("127.0.0.1", 50124)) is None
        assert registry.count() == 0


class TestBackendAdapter:
    """Tests for BackendAdapter integration."""

    def setup_method(self):
        SessionRegistry.reset_instance()
        lobby_service = LobbyService.get_instance()
        lobby_service._presences.clear()

    def test_create_guest_session(self):
        adapter = BackendAdapter()
        session = adapter.create_guest_session(
            account_id=10,
            username="guest_10",
            device_id="device_sample",
            client_addr=("127.0.0.1", 45000)
        )
        assert session.session_key > 0
        assert session.account_id == 10
        assert session.username == "guest_10"
        assert session.state == SESSION_STATE_AUTHENTICATED

        # Verify indexed in registry
        retrieved = adapter.registry.get_by_session_key(session.session_key)
        assert retrieved is session

    def test_bind_lobby_presence(self):
        adapter = BackendAdapter()
        lobby_service = LobbyService.get_instance()

        session = adapter.create_guest_session(
            account_id=20,
            username="guest_20",
            device_id="device_20",
            client_addr=("127.0.0.1", 45001)
        )

        success = adapter.bind_lobby_presence(session.session_key, gid=200, nickname="Hero20")
        assert success is True
        assert session.state == SESSION_STATE_IN_LOBBY
        presence = lobby_service.get_presence(200)
        assert presence is not None
        assert presence.nickname == "Hero20"

    def test_close_session_cleans_lobby_presence(self):
        adapter = BackendAdapter()
        lobby_service = LobbyService.get_instance()

        session = adapter.create_guest_session(
            account_id=30,
            username="guest_30",
            device_id="device_30",
            client_addr=("127.0.0.1", 45002)
        )
        adapter.bind_lobby_presence(session.session_key, gid=300, nickname="Hero30")
        assert lobby_service.get_presence(300) is not None

        adapter.close_session(session.session_key, gid=300)
        assert lobby_service.get_presence(300) is None
        assert adapter.registry.get_by_session_key(session.session_key) is None
