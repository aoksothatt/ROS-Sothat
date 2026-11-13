from fastapi import APIRouter, Depends, HTTPException, status
from app.account.models import Account
from app.account.service import get_current_account
from app.lobby.schemas import LobbyEnterResponse, HeartbeatResponse, LobbyOnlineListResponse
from app.lobby.service import LobbyService, get_lobby_service

router = APIRouter(prefix="/lobby", tags=["Lobby & Presence"])

@router.post("/enter", response_model=LobbyEnterResponse)
async def enter_lobby(
    current_account: Account = Depends(get_current_account),
    lobby_service: LobbyService = Depends(get_lobby_service)
):
    """Register presence in the lobby hall. Requires an existing Character profile."""
    if not current_account.character:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot enter lobby without creating an in-game character first."
        )
    char = current_account.character
    presence = lobby_service.enter_lobby(
        account_id=current_account.id,
        gid=char.gid,
        nickname=char.nickname,
        level=char.level
    )
    return LobbyEnterResponse(
        gid=presence.gid,
        nickname=presence.nickname,
        status=presence.status
    )

@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    current_account: Account = Depends(get_current_account),
    lobby_service: LobbyService = Depends(get_lobby_service)
):
    """Keep player presence alive in lobby. Call periodically (e.g. every 15-30s)."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    presence = lobby_service.heartbeat(current_account.character.gid)
    return HeartbeatResponse(
        gid=presence.gid,
        status=presence.status
    )

@router.get("/online", response_model=LobbyOnlineListResponse)
async def list_online_players(
    lobby_service: LobbyService = Depends(get_lobby_service)
):
    """List all currently active and online players in the lobby."""
    players = lobby_service.list_online_players()
    return LobbyOnlineListResponse(
        total_online=len(players),
        players=players
    )

@router.post("/leave")
async def leave_lobby(
    current_account: Account = Depends(get_current_account),
    lobby_service: LobbyService = Depends(get_lobby_service)
):
    """Leave the lobby and mark presence as offline."""
    if current_account.character:
        lobby_service.leave_lobby(current_account.character.gid)
    return {"message": "Successfully left lobby."}
