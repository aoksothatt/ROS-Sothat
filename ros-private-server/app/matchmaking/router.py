from fastapi import APIRouter, Depends, HTTPException, status
from app.account.models import Account
from app.account.service import get_current_account
from app.matchmaking.schemas import MatchQueueRequest, MatchTicketResponse, MatchStatusResponse
from app.matchmaking.service import MatchmakingService, get_matchmaking_service

router = APIRouter(prefix="/matchmaking", tags=["Matchmaking Queue"])

@router.post("/queue", response_model=MatchTicketResponse, status_code=status.HTTP_201_CREATED)
async def enqueue_matchmaking(
    req: MatchQueueRequest = MatchQueueRequest(),
    current_account: Account = Depends(get_current_account),
    mm_service: MatchmakingService = Depends(get_matchmaking_service)
):
    """Enqueue player into matchmaking pool."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    char = current_account.character
    return mm_service.enqueue(char.gid, char.nickname, char.level, req.match_mode, req.region)

@router.get("/ticket/{ticket_id}", response_model=MatchStatusResponse)
async def get_ticket_status(
    ticket_id: str,
    current_account: Account = Depends(get_current_account),
    mm_service: MatchmakingService = Depends(get_matchmaking_service)
):
    """Poll the status of an active matchmaking ticket."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    return mm_service.get_ticket_status(ticket_id, current_account.character.gid)

@router.post("/cancel/{ticket_id}")
async def cancel_matchmaking(
    ticket_id: str,
    current_account: Account = Depends(get_current_account),
    mm_service: MatchmakingService = Depends(get_matchmaking_service)
):
    """Cancel an active matchmaking ticket and return to idle lobby state."""
    if not current_account.character:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No character profile.")
    return mm_service.cancel(ticket_id, current_account.character.gid)
