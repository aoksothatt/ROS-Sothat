from typing import List, Optional
from pydantic import BaseModel
from app.lobby.models import PresenceStatus

class PlayerPresenceOut(BaseModel):
    gid: int
    nickname: str
    level: int
    status: PresenceStatus
    room_id: Optional[str] = None
    last_heartbeat_seconds_ago: float

class LobbyEnterResponse(BaseModel):
    gid: int
    nickname: str
    status: PresenceStatus
    message: str = "Welcome to the Lobby Hall"

class HeartbeatResponse(BaseModel):
    gid: int
    status: PresenceStatus
    acknowledged: bool = True

class LobbyOnlineListResponse(BaseModel):
    total_online: int
    players: List[PlayerPresenceOut]
