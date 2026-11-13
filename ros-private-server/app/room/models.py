from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

class RoomStatus(str, Enum):
    WAITING = "waiting"
    READY = "ready"
    PLAYING = "playing"
    CLOSED = "closed"

@dataclass
class RoomMember:
    gid: int
    nickname: str
    level: int
    is_host: bool = False
    is_ready: bool = False
    slot_idx: int = 0
    joined_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Room:
    room_id: str
    name: str
    host_gid: int
    map_id: int = 1
    capacity: int = 4
    team_mode: int = 4 # 1: Solo, 2: Duo, 4: Squad, 5: Fireteam
    is_public: bool = True
    password_hash: Optional[str] = None
    status: RoomStatus = RoomStatus.WAITING
    members: Dict[int, RoomMember] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    match_token: Optional[str] = None
