import json
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException, status, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.economy.models import DiamondTransaction
from app.economy.repository import EconomyRepository
from app.admin.models import AdminAuditLog
from app.economy.schemas import (
    DiamondGrantRequest,
    DiamondDeductRequest,
    DiamondTransactionOut,
    DiamondHistoryResponse,
)

class EconomyService:
    def __init__(self, repository: EconomyRepository):
        self.repository = repository

    async def grant_diamonds(
        self,
        character_gid: int,
        admin_account_id: int,
        req: DiamondGrantRequest
    ) -> DiamondTransactionOut:
        # Check idempotency first
        existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
        if existing:
            # If all parameters match, return existing (idempotent success)
            if (
                existing.character_gid == character_gid
                and existing.operation_type == "GRANT"
                and existing.amount == req.amount
            ):
                return DiamondTransactionOut.model_validate(existing)
            else:
                # Key reused with conflicting parameters
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
                )

        try:
            # Atomic database update
            balance_after = await self.repository.atomic_grant(character_gid, req.amount)
            if balance_after is None:
                # Character does not exist
                character = await self.repository.get_character_by_gid(character_gid)
                if not character:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Character with GID {character_gid} not found."
                    )

            balance_before = balance_after - req.amount

            # Create ledger record within same atomic transaction
            tx = await self.repository.create_transaction(
                character_gid=character_gid,
                admin_account_id=admin_account_id,
                operation_type="GRANT",
                amount=req.amount,
                balance_before=balance_before,
                balance_after=balance_after,
                idempotency_key=req.idempotency_key,
                reason=req.reason
            )

            # Record administrator audit log in the same atomic transaction
            audit = AdminAuditLog(
                admin_account_id=admin_account_id,
                action_type="DIAMOND_GRANT",
                target_type="character",
                target_id=character_gid,
                reason=req.reason,
                details=json.dumps({
                    "amount": req.amount,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "idempotency_key": req.idempotency_key
                }),
                created_at=datetime.utcnow()
            )
            self.repository.session.add(audit)

            await self.repository.commit()
            await self.repository.refresh(tx)
            return DiamondTransactionOut.model_validate(tx)
        except HTTPException:
            await self.repository.rollback()
            raise
        except IntegrityError as exc:
            await self.repository.rollback()
            # If concurrent race on same idempotency_key
            existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
            if (
                existing
                and existing.character_gid == character_gid
                and existing.operation_type == "GRANT"
                and existing.amount == req.amount
            ):
                return DiamondTransactionOut.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
            )
        except Exception:
            await self.repository.rollback()
            raise

    async def deduct_diamonds(
        self,
        character_gid: int,
        admin_account_id: int,
        req: DiamondDeductRequest
    ) -> DiamondTransactionOut:
        # Check idempotency first
        existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
        if existing:
            # If all parameters match, return existing (idempotent success)
            if (
                existing.character_gid == character_gid
                and existing.operation_type == "DEDUCT"
                and existing.amount == req.amount
            ):
                return DiamondTransactionOut.model_validate(existing)
            else:
                # Key reused with conflicting parameters
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
                )

        try:
            # Atomic database update (only succeeds if diamonds >= req.amount)
            balance_after = await self.repository.atomic_deduct(character_gid, req.amount)
            if balance_after is None:
                # Distinguish between character not found vs insufficient funds
                character = await self.repository.get_character_by_gid(character_gid)
                if not character:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Character with GID {character_gid} not found."
                    )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient diamond balance: current balance is {character.diamonds}, requested deduction is {req.amount}."
                )

            balance_before = balance_after + req.amount

            # Create ledger record within same atomic transaction
            tx = await self.repository.create_transaction(
                character_gid=character_gid,
                admin_account_id=admin_account_id,
                operation_type="DEDUCT",
                amount=req.amount,
                balance_before=balance_before,
                balance_after=balance_after,
                idempotency_key=req.idempotency_key,
                reason=req.reason
            )

            # Record administrator audit log in the same atomic transaction
            audit = AdminAuditLog(
                admin_account_id=admin_account_id,
                action_type="DIAMOND_DEDUCT",
                target_type="character",
                target_id=character_gid,
                reason=req.reason,
                details=json.dumps({
                    "amount": req.amount,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "idempotency_key": req.idempotency_key
                }),
                created_at=datetime.utcnow()
            )
            self.repository.session.add(audit)

            await self.repository.commit()
            await self.repository.refresh(tx)
            return DiamondTransactionOut.model_validate(tx)
        except HTTPException:
            await self.repository.rollback()
            raise
        except IntegrityError as exc:
            await self.repository.rollback()
            # If concurrent race on same idempotency_key
            existing = await self.repository.get_transaction_by_idempotency_key(req.idempotency_key)
            if (
                existing
                and existing.character_gid == character_gid
                and existing.operation_type == "DEDUCT"
                and existing.amount == req.amount
            ):
                return DiamondTransactionOut.model_validate(existing)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Idempotency key '{req.idempotency_key}' has already been used with different parameters."
            )
        except Exception:
            await self.repository.rollback()
            raise

    async def get_character_history(
        self,
        character_gid: int,
        limit: int = 50,
        offset: int = 0
    ) -> DiamondHistoryResponse:
        character = await self.repository.get_character_by_gid(character_gid)
        if not character:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Character with GID {character_gid} not found."
            )

        total = await self.repository.count_character_transactions(character_gid)
        txs = await self.repository.list_character_transactions(character_gid, limit=limit, offset=offset)

        return DiamondHistoryResponse(
            character_gid=character_gid,
            current_balance=character.diamonds,
            total_transactions=total,
            transactions=[DiamondTransactionOut.model_validate(t) for t in txs]
        )

async def get_economy_service(session: AsyncSession = Depends(get_db)) -> EconomyService:
    repo = EconomyRepository(session)
    return EconomyService(repo)
