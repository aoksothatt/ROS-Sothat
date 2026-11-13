from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.economy.models import DiamondTransaction
from app.player.models import Character

class EconomyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_character_by_gid(self, gid: int, for_update: bool = False) -> Optional[Character]:
        stmt = select(Character).where(Character.gid == gid)
        # Note: SQLite does not support FOR UPDATE clauses
        try:
            dialect_name = self.session.bind.dialect.name if self.session.bind else ""
        except Exception:
            dialect_name = ""
        if for_update and dialect_name and dialect_name != "sqlite":
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def atomic_grant(
        self,
        character_gid: int,
        amount: int
    ) -> Optional[int]:
        """
        Atomically increment character diamonds using database-level UPDATE ... RETURNING.
        Prevents lost updates under concurrent access across all supporting engines.
        Returns the updated balance (balance_after), or None if character does not exist.
        """
        stmt = (
            update(Character)
            .where(Character.gid == character_gid)
            .values(
                diamonds=Character.diamonds + amount,
                updated_at=datetime.utcnow()
            )
            .returning(Character.diamonds)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def atomic_deduct(
        self,
        character_gid: int,
        amount: int
    ) -> Optional[int]:
        """
        Atomically decrement character diamonds using database-level UPDATE ... RETURNING
        only if current balance is >= amount.
        Prevents double spending and overdrafts under concurrent access.
        Returns the updated balance (balance_after), or None if character does not exist
        or has insufficient diamonds.
        """
        stmt = (
            update(Character)
            .where(
                Character.gid == character_gid,
                Character.diamonds >= amount
            )
            .values(
                diamonds=Character.diamonds - amount,
                updated_at=datetime.utcnow()
            )
            .returning(Character.diamonds)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_transaction_by_idempotency_key(self, idempotency_key: str) -> Optional[DiamondTransaction]:
        stmt = select(DiamondTransaction).where(DiamondTransaction.idempotency_key == idempotency_key)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_transaction(
        self,
        character_gid: int,
        admin_account_id: int,
        operation_type: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        idempotency_key: str,
        reason: str
    ) -> DiamondTransaction:
        tx = DiamondTransaction(
            character_gid=character_gid,
            admin_account_id=admin_account_id,
            operation_type=operation_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            idempotency_key=idempotency_key,
            reason=reason
        )
        self.session.add(tx)
        return tx

    async def list_character_transactions(
        self,
        character_gid: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[DiamondTransaction]:
        stmt = (
            select(DiamondTransaction)
            .where(DiamondTransaction.character_gid == character_gid)
            .order_by(DiamondTransaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_character_transactions(self, character_gid: int) -> int:
        stmt = (
            select(func.count(DiamondTransaction.id))
            .where(DiamondTransaction.character_gid == character_gid)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, instance) -> None:
        await self.session.refresh(instance)
