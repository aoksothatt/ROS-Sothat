import json
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException, status, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.inventory.models import Item, InventoryItem, InventoryTransaction
from app.admin.models import AdminAuditLog
from app.inventory.repository import InventoryRepository
from app.inventory.schemas import (
    ItemCreate,
    ItemUpdate,
    ItemOut,
    InventoryGrantRequest,
    InventoryRemoveRequest,
    InventoryItemOut,
    CharacterInventoryResponse,
    InventoryTransactionOut,
    InventoryHistoryResponse,
)

class InventoryService:
    def __init__(self, repository: InventoryRepository):
        self.repository = repository

    # ---------------------------------------------------------
    # Catalog Management
    # ---------------------------------------------------------
    async def create_item(self, req: ItemCreate) -> ItemOut:
        existing = await self.repository.get_item_by_code(req.item_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Item with code '{req.item_code}' already exists."
            )

        item = Item(
            item_code=req.item_code,
            name=req.name,
            description=req.description,
            item_type=req.item_type,
            icon=req.icon,
            stackable=req.stackable,
            max_stack=req.max_stack if req.stackable else 1,
            is_active=req.is_active
        )
        created = await self.repository.create_item(item)
        await self.repository.commit()
        await self.repository.refresh(created)
        return ItemOut.model_validate(created)

    async def get_item_by_id(self, item_id: int) -> ItemOut:
        item = await self.repository.get_item_by_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found."
            )
        return ItemOut.model_validate(item)

    async def list_items(
        self,
        item_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ItemOut]:
        items = await self.repository.list_items(
            item_type=item_type,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        return [ItemOut.model_validate(it) for it in items]

    async def update_item(self, item_id: int, req: ItemUpdate) -> ItemOut:
        item = await self.repository.get_item_by_id(item_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Item with ID {item_id} not found."
            )

        if req.max_stack is not None:
            if not item.stackable and req.max_stack != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot set max_stack > 1 on non-stackable item."
                )
            if req.max_stack < item.max_stack:
                max_held = await self.repository.get_max_inventory_quantity(item_id)
                if max_held > req.max_stack:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Cannot reduce max_stack to {req.max_stack}: existing player inventory "
                            f"contains stacks up to {max_held} for item '{item.name}'."
                        )
                    )
            item.max_stack = req.max_stack

        if req.name is not None:
            item.name = req.name
        if req.description is not None:
            item.description = req.description
        if req.icon is not None:
            item.icon = req.icon
        if req.is_active is not None:
            item.is_active = req.is_active

        saved = await self.repository.save_item(item)
        await self.repository.commit()
        await self.repository.refresh(saved)
        return ItemOut.model_validate(saved)

    # ---------------------------------------------------------
    # Inventory Management
    # ---------------------------------------------------------
    async def get_character_inventory(
        self,
        character_gid: int,
        limit: int = 50,
        offset: int = 0
    ) -> CharacterInventoryResponse:
        character = await self.repository.get_character_by_gid(character_gid)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character with GID {character_gid} not found."
            )

        total = await self.repository.count_character_inventory(character_gid)
        slots = await self.repository.list_character_inventory(character_gid, limit=limit, offset=offset)

        items_out = [
            InventoryItemOut(
                id=s.id,
                character_gid=s.character_gid,
                item_id=s.item_id,
                quantity=s.quantity,
                created_at=s.created_at,
                updated_at=s.updated_at,
                item=ItemOut.model_validate(s.item) if s.item else None
            )
            for s in slots
        ]

        return CharacterInventoryResponse(
            character_gid=character_gid,
            total_items=total,
            items=items_out
        )

    async def grant_inventory(
        self,
        character_gid: int,
        admin_account_id: int,
        req: InventoryGrantRequest
    ) -> InventoryTransactionOut:
        # Check idempotency first
        existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
        if existing:
            if (
                existing.character_gid == character_gid
                and existing.item_id == req.item_id
                and existing.operation_type == "GRANT"
                and existing.quantity == req.quantity
            ):
                return InventoryTransactionOut.model_validate(existing)
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
                )

        try:
            # Character verification
            character = await self.repository.get_character_by_gid(character_gid)
            if not character:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Character with GID {character_gid} not found."
                )

            # Item verification
            item = await self.repository.get_item_by_id(req.item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item with ID {req.item_id} not found."
                )
            if not item.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Item '{item.name}' is inactive and cannot be granted."
                )

            try:
                qty_before, qty_after = await self.repository.atomic_grant(
                    character_gid=character_gid,
                    item=item,
                    quantity=req.quantity
                )
            except ValueError as ve:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(ve)
                )

            tx = await self.repository.create_transaction(
                character_gid=character_gid,
                item_id=req.item_id,
                admin_account_id=admin_account_id,
                operation_type="GRANT",
                quantity=req.quantity,
                quantity_before=qty_before,
                quantity_after=qty_after,
                reason=req.reason,
                idempotency_key=req.idempotency_key
            )

            # Record administrator audit log in the same atomic transaction
            audit = AdminAuditLog(
                admin_account_id=admin_account_id,
                action_type="INVENTORY_GRANT",
                target_type="character",
                target_id=character_gid,
                reason=req.reason,
                details=json.dumps({
                    "item_id": req.item_id,
                    "item_name": item.name,
                    "quantity": req.quantity,
                    "quantity_before": qty_before,
                    "quantity_after": qty_after,
                    "idempotency_key": req.idempotency_key
                }),
                created_at=datetime.utcnow()
            )
            self.repository.session.add(audit)

            await self.repository.commit()
            await self.repository.refresh(tx)
            return InventoryTransactionOut.model_validate(tx)
        except HTTPException:
            await self.repository.rollback()
            raise
        except IntegrityError as exc:
            await self.repository.rollback()
            # Handle concurrent race on identical idempotency key
            existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
            if (
                existing
                and existing.character_gid == character_gid
                and existing.item_id == req.item_id
                and existing.operation_type == "GRANT"
                and existing.quantity == req.quantity
            ):
                return InventoryTransactionOut.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
            )
        except Exception:
            await self.repository.rollback()
            raise

    async def remove_inventory(
        self,
        character_gid: int,
        admin_account_id: int,
        req: InventoryRemoveRequest
    ) -> InventoryTransactionOut:
        # Check idempotency first
        existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
        if existing:
            if (
                existing.character_gid == character_gid
                and existing.item_id == req.item_id
                and existing.operation_type == "REMOVE"
                and existing.quantity == req.quantity
            ):
                return InventoryTransactionOut.model_validate(existing)
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
                )

        try:
            # Character verification
            character = await self.repository.get_character_by_gid(character_gid)
            if not character:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Character with GID {character_gid} not found."
                )

            # Item verification
            item = await self.repository.get_item_by_id(req.item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item with ID {req.item_id} not found."
                )

            try:
                qty_before, qty_after = await self.repository.atomic_remove(
                    character_gid=character_gid,
                    item_id=req.item_id,
                    quantity=req.quantity
                )
            except ValueError as ve:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(ve)
                )

            tx = await self.repository.create_transaction(
                character_gid=character_gid,
                item_id=req.item_id,
                admin_account_id=admin_account_id,
                operation_type="REMOVE",
                quantity=req.quantity,
                quantity_before=qty_before,
                quantity_after=qty_after,
                reason=req.reason,
                idempotency_key=req.idempotency_key
            )

            # Safeguard: if item was fully removed down to 0, automatically unequip it from appearances
            if qty_after == 0 and character.appearances:
                appearances = dict(character.appearances)
                equipped = list(appearances.get("equipped_clothing", []))
                modified = False
                if req.item_id in equipped:
                    equipped.remove(req.item_id)
                    modified = True
                try:
                    code_num = int(item.item_code)
                    if code_num in equipped:
                        equipped.remove(code_num)
                        modified = True
                except ValueError:
                    pass
                if modified:
                    appearances["equipped_clothing"] = equipped
                    character.appearances = appearances
                    self.repository.session.add(character)

            # Record administrator audit log in the same atomic transaction
            audit = AdminAuditLog(
                admin_account_id=admin_account_id,
                action_type="INVENTORY_REMOVE",
                target_type="character",
                target_id=character_gid,
                reason=req.reason,
                details=json.dumps({
                    "item_id": req.item_id,
                    "item_name": item.name,
                    "quantity": req.quantity,
                    "quantity_before": qty_before,
                    "quantity_after": qty_after,
                    "idempotency_key": req.idempotency_key
                }),
                created_at=datetime.utcnow()
            )
            self.repository.session.add(audit)

            await self.repository.commit()
            await self.repository.refresh(tx)
            return InventoryTransactionOut.model_validate(tx)
        except HTTPException:
            await self.repository.rollback()
            raise
        except IntegrityError as exc:
            await self.repository.rollback()
            # Handle concurrent race on identical idempotency key
            existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
            if (
                existing
                and existing.character_gid == character_gid
                and existing.item_id == req.item_id
                and existing.operation_type == "REMOVE"
                and existing.quantity == req.quantity
            ):
                return InventoryTransactionOut.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
            )
        except Exception:
            await self.repository.rollback()
            raise

    async def get_inventory_history(
        self,
        character_gid: int,
        limit: int = 50,
        offset: int = 0
    ) -> InventoryHistoryResponse:
        character = await self.repository.get_character_by_gid(character_gid)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character with GID {character_gid} not found."
            )

        total = await self.repository.count_character_transactions(character_gid)
        txs = await self.repository.list_character_transactions(character_gid, limit=limit, offset=offset)

        return InventoryHistoryResponse(
            character_gid=character_gid,
            total_transactions=total,
            transactions=[InventoryTransactionOut.model_validate(t) for t in txs]
        )

# Dependency injection helper
async def get_inventory_service(session: AsyncSession = Depends(get_db)) -> InventoryService:
    repo = InventoryRepository(session)
    return InventoryService(repo)
