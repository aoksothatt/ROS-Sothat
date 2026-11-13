from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.account.models import Account
from app.account.service import get_current_account
from app.player.schemas import CharacterCreate, CharacterOut, CharacterUpdateSettings, CharacterUpdateAppearances, CharacterPublicProfile
from app.player.service import PlayerService, get_player_service
from app.inventory.schemas import CharacterInventoryResponse
from app.inventory.service import InventoryService, get_inventory_service
from app.economy.schemas import DiamondHistoryResponse
from app.economy.service import EconomyService, get_economy_service

router = APIRouter(prefix="/player", tags=["Player Profile"])

@router.post("/character", response_model=CharacterOut, status_code=status.HTTP_201_CREATED)
async def create_character(
    req: CharacterCreate,
    current_account: Account = Depends(get_current_account),
    service: PlayerService = Depends(get_player_service)
):
    """Create a new in-game character profile for the authenticated account."""
    return await service.create_character(current_account.id, req)

@router.get("/character", response_model=CharacterOut)
async def get_my_character(
    current_account: Account = Depends(get_current_account),
    service: PlayerService = Depends(get_player_service)
):
    """Retrieve the current authenticated user's character profile."""
    return await service.get_my_character(current_account.id)

@router.get("/{gid}", response_model=CharacterPublicProfile)
async def get_public_profile(
    gid: int,
    service: PlayerService = Depends(get_player_service)
):
    """Retrieve public player statistics and profile by GID."""
    return await service.get_public_profile(gid)

@router.put("/character/settings", response_model=CharacterOut)
async def update_settings(
    req: CharacterUpdateSettings,
    current_account: Account = Depends(get_current_account),
    service: PlayerService = Depends(get_player_service)
):
    """Update personal gameplay and control settings."""
    return await service.update_settings(current_account.id, req.settings)

@router.put("/character/appearances", response_model=CharacterOut)
async def update_appearances(
    req: CharacterUpdateAppearances,
    current_account: Account = Depends(get_current_account),
    service: PlayerService = Depends(get_player_service)
):
    """Update equipped clothing and cosmetic loadout."""
    return await service.update_appearances(current_account.id, req.appearances)

@router.get("/character/inventory", response_model=CharacterInventoryResponse)
async def get_my_inventory(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_account: Account = Depends(get_current_account),
    player_service: PlayerService = Depends(get_player_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Retrieve the authenticated player's own inventory items."""
    char = await player_service.repository.get_by_account_id(current_account.id)
    if not char:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No character found for this account."
        )
    return await inventory_service.get_character_inventory(
        character_gid=char.gid,
        limit=limit,
        offset=offset
    )

@router.get("/character/diamonds/history", response_model=DiamondHistoryResponse)
async def get_my_diamond_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_account: Account = Depends(get_current_account),
    player_service: PlayerService = Depends(get_player_service),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Retrieve the authenticated player's own diamond transaction ledger."""
    char = await player_service.repository.get_by_account_id(current_account.id)
    if not char:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No character found for this account."
        )
    return await economy_service.get_character_history(
        character_gid=char.gid,
        limit=limit,
        offset=offset
    )

