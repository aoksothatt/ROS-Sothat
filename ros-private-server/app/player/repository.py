from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.player.models import Character

class PlayerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, account_id: int, nickname: str, char_type: int) -> Character:
        character = Character(
            account_id=account_id,
            nickname=nickname,
            char_type=char_type
        )
        self.session.add(character)
        await self.session.commit()
        await self.session.refresh(character)
        return character

    async def get_by_gid(self, gid: int) -> Optional[Character]:
        stmt = select(Character).where(Character.gid == gid)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_account_id(self, account_id: int) -> Optional[Character]:
        stmt = select(Character).where(Character.account_id == account_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_nickname(self, nickname: str) -> Optional[Character]:
        stmt = select(Character).where(Character.nickname == nickname)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def save(self, character: Character) -> Character:
        self.session.add(character)
        await self.session.commit()
        await self.session.refresh(character)
        return character
