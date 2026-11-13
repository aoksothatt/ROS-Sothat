"""
Gateway package connecting Mercury UDP transport with existing backend services.
"""

from gateway.constants import (
    LOGON_STATUS_OK,
    LOGON_STATUS_FAILED,
    LOGON_STATUS_BANNED,
    LOGON_STATUS_VERSION_MISMATCH,
    LOGON_STATUS_ALREADY_ONLINE,
    SESSION_STATE_AUTHENTICATED,
    SESSION_STATE_IN_LOBBY,
    SESSION_STATE_IN_ROOM,
    SESSION_STATE_IN_MATCH,
    SESSION_STATE_DISCONNECTED,
)
from gateway.handshake import (
    LoginHandshakeRequest,
    LoginHandshakeResponse,
    LocalRSATestHarness,
)
from gateway.adapter import (
    SessionContext,
    SessionRegistry,
    BackendAdapter,
)

__all__ = [
    "LOGON_STATUS_OK",
    "LOGON_STATUS_FAILED",
    "LOGON_STATUS_BANNED",
    "LOGON_STATUS_VERSION_MISMATCH",
    "LOGON_STATUS_ALREADY_ONLINE",
    "SESSION_STATE_AUTHENTICATED",
    "SESSION_STATE_IN_LOBBY",
    "SESSION_STATE_IN_ROOM",
    "SESSION_STATE_IN_MATCH",
    "SESSION_STATE_DISCONNECTED",
    "LoginHandshakeRequest",
    "LoginHandshakeResponse",
    "LocalRSATestHarness",
    "SessionContext",
    "SessionRegistry",
    "BackendAdapter",
]
