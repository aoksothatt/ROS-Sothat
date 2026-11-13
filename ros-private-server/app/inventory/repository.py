from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import joinedload
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.inventory.models import Item, InventoryItem, InventoryTransaction
from app.player.models import Character

class InventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------------------------------------------
    # Catalog Operations
    # ---------------------------------------------------------
    async def create_item(self, item: Item) -> Item:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def get_item_by_id(self, item_id: int) -> Optional[Item]:
        stmt = select(Item).where(Item.id == item_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_item_by_code(self, item_code: str) -> Optional[Item]:
        stmt = select(Item).where(Item.item_code == item_code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_items(
        self,
        item_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Item]:
        stmt = select(Item)
        if item_type is not None:
            stmt = stmt.where(Item.item_type == item_type)
        if is_active is not None:
            stmt = stmt.where(Item.is_active == is_active)
        stmt = stmt.order_by(Item.id.asc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def save_item(self, item: Item) -> Item:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def get_max_inventory_quantity(self, item_id: int) -> int:
        """
        Returns the highest quantity currently held by any character for the given item_id.
        Returns 0 if no character currently possesses the item.
        """
        stmt = (
            select(func.max(InventoryItem.quantity))
            .where(InventoryItem.item_id == item_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # ---------------------------------------------------------
    # Character Lookup
    # ---------------------------------------------------------
    async def get_character_by_gid(self, gid: int) -> Optional[Character]:
        stmt = select(Character).where(Character.gid == gid)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ---------------------------------------------------------
    # Player Inventory Operations
    # ---------------------------------------------------------
    async def get_inventory_item(self, character_gid: int, item_id: int) -> Optional[InventoryItem]:
        stmt = (
            select(InventoryItem)
            .options(joinedload(InventoryItem.item))
            .where(
                InventoryItem.character_gid == character_gid,
                InventoryItem.item_id == item_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_character_inventory(
        self,
        character_gid: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[InventoryItem]:
        stmt = (
            select(InventoryItem)
            .options(joinedload(InventoryItem.item))
            .where(InventoryItem.character_gid == character_gid)
            .order_by(InventoryItem.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_character_inventory(self, character_gid: int) -> int:
        stmt = (
            select(func.count(InventoryItem.id))
            .where(InventoryItem.character_gid == character_gid)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def atomic_grant(
        self,
        character_gid: int,
        item: Item,
        quantity: int
    ) -> Tuple[int, int]:
        """
        Atomically grants items into the character's inventory slot using native UPSERT.
        Enforces stackability, maximum stack limits, and positive quantities.
        Returns (quantity_before, quantity_after).
        """
        if not item.stackable and quantity != 1:
            raise ValueError("Non-stackable items can only be granted with quantity=1.")
        if quantity > item.max_stack:
            raise ValueError(f"Quantity {quantity} exceeds item max stack {item.max_stack}.")

        existing = await self.get_inventory_item(character_gid, item.id)
        quantity_before = existing.quantity if existing else 0

        if not item.stackable and quantity_before > 0:
            raise ValueError(f"Item '{item.name}' is non-stackable and character already owns it.")

        if item.stackable and (quantity_before + quantity > item.max_stack):
            raise ValueError(
                f"Cannot grant {quantity} items: would exceed max stack limit of {item.max_stack} "
                f"(current quantity: {quantity_before})."
            )

        dialect_name = getattr(self.session.bind.dialect, "name", "") if self.session.bind else ""
        insert_fn = pg_insert if dialect_name == "postgresql" else sqlite_insert

        if item.stackable:
            stmt = (
                insert_fn(InventoryItem)
                .values(
                    character_gid=character_gid,
                    item_id=item.id,
                    quantity=quantity,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                .on_conflict_do_update(
                    index_elements=["character_gid", "item_id"],
                    set_={
                        "quantity": InventoryItem.quantity + quantity,
                        "updated_at": datetime.utcnow()
                    },
                    where=(InventoryItem.quantity + quantity <= item.max_stack)
                )
                .returning(InventoryItem.quantity)
            )
        else:
            stmt = (
                insert_fn(InventoryItem)
                .values(
                    character_gid=character_gid,
                    item_id=item.id,
                    quantity=quantity,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                .returning(InventoryItem.quantity)
            )

        res = await self.session.execute(stmt)
        quantity_after = res.scalar_one_or_none()
        if quantity_after is None:
            raise ValueError(
                f"Cannot grant {quantity} items: would exceed max stack limit of {item.max_stack}."
            )

        actual_quantity_before = quantity_after - quantity
        return actual_quantity_before, quantity_after

    async def atomic_remove(
        self,
        character_gid: int,
        item_id: int,
        quantity: int
    ) -> Tuple[int, int]:
        """
        Atomically removes items from the character's inventory slot.
        Removes the slot completely if quantity reaches zero.
        Returns (quantity_before, quantity_after).
        """
        existing = await self.get_inventory_item(character_gid, item_id)
        if existing is None:
            raise ValueError("Item not found in character inventory.")

        quantity_before = existing.quantity
        if quantity_before < quantity:
            raise ValueError(
                f"Insufficient item quantity: character possesses {quantity_before}, "
                f"requested removal is {quantity}."
            )

        if quantity_before == quantity:
            # Full removal down to zero: atomically delete the slot
            del_stmt = (
                delete(InventoryItem)
                .where(
                    InventoryItem.character_gid == character_gid,
                    InventoryItem.item_id == item_id,
                    InventoryItem.quantity == quantity_before
                )
            )
            res = await self.session.execute(del_stmt)
            if res.rowcount == 0:
                raise ValueError("Insufficient item quantity or concurrent modification.")
            return quantity_before, 0
        else:
            # Partial removal: atomically decrement quantity (> 0 guaranteed)
            stmt = (
                update(InventoryItem)
                .where(
                    InventoryItem.character_gid == character_gid,
                    InventoryItem.item_id == item_id,
                    InventoryItem.quantity > quantity
                )
                .values(
                    quantity=InventoryItem.quantity - quantity,
                    updated_at=datetime.utcnow()
                )
                .returning(InventoryItem.quantity)
            )
            res = await self.session.execute(stmt)
            quantity_after = res.scalar_one_or_none()
            if quantity_after is None:
                raise ValueError("Insufficient item quantity or concurrent modification.")

            return quantity_after + quantity, quantity_after

    # ---------------------------------------------------------
    # Inventory Transaction History Operations
    # ---------------------------------------------------------
    async def get_transaction_by_idempotency_key(
        self,
        idempotency_key: str
    ) -> Optional[InventoryTransaction]:
        stmt = (
            select(InventoryTransaction)
            .where(InventoryTransaction.idempotency_key == idempotency_key)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_transaction(
        self,
        character_gid: int,
        item_id: int,
        admin_account_id: int,
        operation_type: str,
        quantity: int,
        quantity_before: int,
        quantity_after: int,
        reason: str,
        idempotency_key: str
    ) -> InventoryTransaction:
        tx = InventoryTransaction(
            character_gid=character_gid,
            item_id=item_id,
            admin_account_id=admin_account_id,
            operation_type=operation_type,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            reason=reason,
            idempotency_key=idempotency_key,
            created_at=datetime.utcnow()
        )
        self.session.add(tx)
        return tx

    async def list_character_transactions(
        self,
        character_gid: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[InventoryTransaction]:
        stmt = (
            select(InventoryTransaction)
            .where(InventoryTransaction.character_gid == character_gid)
            .order_by(InventoryTransaction.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_character_transactions(self, character_gid: int) -> int:
        stmt = (
            select(func.count(InventoryTransaction.id))
            .where(InventoryTransaction.character_gid == character_gid)
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def refresh(self, instance) -> None:
        await self.session.refresh(instance)
