from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from app.account.models import Account
from app.account.service import get_current_account
from app.room.schemas import RoomCreateRequest, RoomJoinRequest, RoomOut, RoomListResponse, RoomStartResponse
from app.room.service import RoomService, get_room_service

router = APIRouter(prefix="/room", tags=["Private Room Management"])

@router.post("/create", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    req: RoomCreateRequest,
    current_account: Account = Depends(get_current_account),
    room_service: RoomService = Depends(get_room_service)
):
    """Create a new custom match room."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    char = current_account.character
    return room_service.create_room(char.gid, char.nickname, char.level, req)

@router.get("/list", response_model=RoomListResponse)
async def list_rooms(
    public_only: bool = True,
    room_service: RoomService = Depends(get_room_service)
):
    """List open and available custom rooms."""
    rooms = room_service.list_rooms(is_public_only=public_only)
    return RoomListResponse(total_rooms=len(rooms), rooms=rooms)

@router.get("/{room_id}", response_model=RoomOut)
async def get_room(
    room_id: str,
    room_service: RoomService = Depends(get_room_service)
):
    """Get detailed state of a specific room."""
    return room_service.get_room_details(room_id)

@router.post("/{room_id}/join", response_model=RoomOut)
async def join_room(
    room_id: str,
    req: RoomJoinRequest = RoomJoinRequest(),
    current_account: Account = Depends(get_current_account),
    room_service: RoomService = Depends(get_room_service)
):
    """Join an open custom room with optional password."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    char = current_account.character
    return room_service.join_room(room_id, char.gid, char.nickname, char.level, req.password)

@router.post("/{room_id}/leave")
async def leave_room(
    room_id: str,
    current_account: Account = Depends(get_current_account),
    room_service: RoomService = Depends(get_room_service)
):
    """Leave the current room."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    return room_service.leave_room(room_id, current_account.character.gid)

@router.post("/{room_id}/ready", response_model=RoomOut)
async def toggle_ready(
    room_id: str,
    is_ready: bool = True,
    current_account: Account = Depends(get_current_account),
    room_service: RoomService = Depends(get_room_service)
):
    """Toggle ready state in room."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    return room_service.set_ready(room_id, current_account.character.gid, is_ready)

@router.post("/{room_id}/kick/{target_gid}", response_model=RoomOut)
async def kick_member(
    room_id: str,
    target_gid: int,
    current_account: Account = Depends(get_current_account),
    room_service: RoomService = Depends(get_room_service)
):
    """Kick a player from the room (Host only)."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    return room_service.kick_member(room_id, current_account.character.gid, target_gid)

@router.post("/{room_id}/start", response_model=RoomStartResponse)
async def start_room_match(
    room_id: str,
    current_account: Account = Depends(get_current_account),
    room_service: RoomService = Depends(get_room_service)
):
    """Start the match from the room (Host only)."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    return room_service.start_room_match(room_id, current_account.character.gid)
