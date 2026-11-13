from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.room.models import RoomStatus

class RoomCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=32, description="Room display title")
    map_id: int = Field(1, ge=1, le=10, description="Target game map ID")
    capacity: int = Field(4, ge=2, le=60, description="Max player slots")
    team_mode: int = Field(4, description="Team mode: 1 (Solo), 2 (Duo), 4 (Squad), 5 (Fireteam)")
    is_public: bool = Field(True, description="Whether room is visible in public listing")
    password: Optional[str] = Field(None, max_length=16, description="Optional entry password")

class RoomJoinRequest(BaseModel):
    password: Optional[str] = Field(None, description="Password if room is locked")

class RoomMemberOut(BaseModel):
    gid: int
    nickname: str
    level: int
    is_host: bool
    is_ready: bool
    slot_idx: int

class RoomOut(BaseModel):
    room_id: str
    name: str
    host_gid: int
    map_id: int
    capacity: int
    current_players: int
    team_mode: int
    is_public: bool
    has_password: bool
    status: RoomStatus
    members: List[RoomMemberOut]
    created_at: datetime

class RoomListResponse(BaseModel):
    total_rooms: int
    rooms: List[RoomOut]

class RoomStartResponse(BaseModel):
    room_id: str
    status: RoomStatus
    match_token: str
    battle_server_ip: str
    battle_server_port: int
    player_count: int
