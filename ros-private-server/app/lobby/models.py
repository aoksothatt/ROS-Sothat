from enum import Enum
from dataclasses import dataclass
from typing import Optional

class PresenceStatus(str, Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    IN_ROOM = "in_room"
    MATCHMAKING = "matchmaking"
    IN_BATTLE = "in_battle"

@dataclass
class PlayerPresence:
    gid: int
    account_id: int
    nickname: str
    level: int
    status: PresenceStatus = PresenceStatus.IDLE
    room_id: Optional[str] = None
    match_id: Optional[str] = None
    last_heartbeat: float = 0.0
