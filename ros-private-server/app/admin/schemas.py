from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class AdminAuditLogOut(BaseModel):
    id: int
    admin_account_id: int
    admin_username: Optional[str] = None
    action_type: str
    target_type: str
    target_id: int
    reason: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AdminAuditLogListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    logs: List[AdminAuditLogOut]

class AdminDashboardSummary(BaseModel):
    total_accounts: int
    active_accounts: int
    suspended_accounts: int
    total_characters: int
    total_diamonds: int
    total_inventory_items: int
    active_lobby_presences: int
    active_rooms: int
    queued_matchmaking_tickets: int
    recent_activity: List[AdminAuditLogOut] = Field(default_factory=list)

class AdminPlayerSummary(BaseModel):
    account_id: int
    username: str
    email: Optional[str] = None
    role: str = "player"
    is_banned: bool = False
    ban_reason: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    character_gid: Optional[int] = None
    character_nickname: Optional[str] = None
    character_level: Optional[int] = None
    diamonds: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

class AdminPlayerListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    players: List[AdminPlayerSummary]

class SuspendRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255, description="Reason for suspending player account")

class ReactivateRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=255, description="Reason for reactivating player account")

class AdminPlayerDetail(BaseModel):
    account_id: int
    username: str
    email: Optional[str] = None
    role: str = "player"
    is_banned: bool = False
    ban_reason: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    character: Optional[Dict[str, Any]] = None
    inventory_items: List[Dict[str, Any]] = Field(default_factory=list)
    recent_diamond_transactions: List[Dict[str, Any]] = Field(default_factory=list)
    recent_audit_logs: List[AdminAuditLogOut] = Field(default_factory=list)
