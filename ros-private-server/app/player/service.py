import re
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.player.models import Character
from app.player.repository import PlayerRepository
from app.player.schemas import CharacterCreate, CharacterOut, CharacterPublicProfile

NICKNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{2,24}$")

class PlayerService:
    def __init__(self, repository: PlayerRepository):
        self.repository = repository

    async def create_character(self, account_id: int, req: CharacterCreate) -> CharacterOut:
        # Check if nickname is valid format
        clean_nickname = req.nickname.strip()
        if not NICKNAME_REGEX.match(clean_nickname):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nickname must be 2-24 alphanumeric characters (letters, numbers, underscores)."
            )
        
        # Check if account already has a character
        existing_char = await self.repository.get_by_account_id(account_id)
        if existing_char:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This account already has a character created."
            )
            
        # Check if nickname is already taken
        taken = await self.repository.get_by_nickname(clean_nickname)
        if taken:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Nickname '{clean_nickname}' is already taken."
            )
            
        char = await self.repository.create(account_id, clean_nickname, req.char_type)
        return CharacterOut.model_validate(char)

    async def get_my_character(self, account_id: int) -> CharacterOut:
        char = await self.repository.get_by_account_id(account_id)
        if not char:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No character found for this account. Character creation is required."
            )
        return CharacterOut.model_validate(char)

    async def get_public_profile(self, gid: int) -> CharacterPublicProfile:
        char = await self.repository.get_by_gid(gid)
        if not char:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with GID {gid} not found."
            )
        return CharacterPublicProfile(
            gid=char.gid,
            nickname=char.nickname,
            char_type=char.char_type,
            level=char.level,
            stats=char.stats
        )

    async def update_settings(self, account_id: int, new_settings: Dict[str, Any]) -> CharacterOut:
        char = await self.repository.get_by_account_id(account_id)
        if not char:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found.")
        char.settings = {**char.settings, **new_settings}
        updated = await self.repository.save(char)
        return CharacterOut.model_validate(updated)

    async def update_appearances(self, account_id: int, new_appearances: Dict[str, Any]) -> CharacterOut:
        char = await self.repository.get_by_account_id(account_id)
        if not char:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found.")
        char.appearances = {**char.appearances, **new_appearances}
        updated = await self.repository.save(char)
        return CharacterOut.model_validate(updated)

# Dependency injection helper
async def get_player_service(session: AsyncSession = Depends(get_db)) -> PlayerService:
    repo = PlayerRepository(session)
    return PlayerService(repo)
