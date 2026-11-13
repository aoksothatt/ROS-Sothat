from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class MatchMode(str, Enum):
    SOLO = "solo"
    DUO = "duo"
    SQUAD = "squad"
    FIRETEAM = "fireteam"

class MatchTicketStatus(str, Enum):
    QUEUED = "queued"
    MATCHED = "matched"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class MatchQueueRequest(BaseModel):
    match_mode: MatchMode = Field(MatchMode.SOLO, description="Selected game queue mode")
    region: str = Field("local", description="Match region")

class MatchTicketResponse(BaseModel):
    ticket_id: str
    gid: int
    nickname: str
    match_mode: MatchMode
    status: MatchTicketStatus
    queued_at: datetime

class MatchStatusResponse(BaseModel):
    ticket_id: str
    gid: int
    status: MatchTicketStatus
    match_id: Optional[str] = None
    battle_server_ip: Optional[str] = None
    battle_server_port: Optional[int] = None
    match_token: Optional[str] = None
    assigned_players: Optional[List[str]] = None
    error_message: Optional[str] = None
