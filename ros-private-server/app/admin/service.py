import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status, Depends
from sqlalchemy import select, func, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.session import get_db
from app.account.models import Account
from app.player.models import Character
from app.economy.models import DiamondTransaction
from app.inventory.models import Item, InventoryItem, InventoryTransaction
from app.admin.models import AdminAuditLog
from app.admin.schemas import (
    AdminAuditLogOut,
    AdminAuditLogListResponse,
    AdminDashboardSummary,
    AdminPlayerSummary,
    AdminPlayerListResponse,
    AdminPlayerDetail,
    SuspendRequest,
    ReactivateRequest,
)
from app.lobby.service import LobbyService
from app.room.service import RoomService
from app.matchmaking.service import MatchmakingService

class AdminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------------------------------------------
    # Audit Logging Core Helpers
    # ---------------------------------------------------------
    async def record_audit_log(
        self,
        admin_account_id: int,
        action_type: str,
        target_type: str,
        target_id: int,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ) -> AdminAuditLog:
        """
        Record an immutable administrative audit log within the current database transaction.
        """
        log_entry = AdminAuditLog(
            admin_account_id=admin_account_id,
            action_type=action_type,
            target_type=target_type,
            target_id=target_id,
            reason=reason.strip(),
            details=json.dumps(details or {}),
            created_at=datetime.utcnow()
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def list_audit_logs(
        self,
        admin_id: Optional[int] = None,
        target_id: Optional[int] = None,
        action_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> AdminAuditLogListResponse:
        stmt = select(AdminAuditLog).options(selectinload(AdminAuditLog.admin_account))
        count_stmt = select(func.count(AdminAuditLog.id))

        if admin_id is not None:
            stmt = stmt.where(AdminAuditLog.admin_account_id == admin_id)
            count_stmt = count_stmt.where(AdminAuditLog.admin_account_id == admin_id)
        if target_id is not None:
            stmt = stmt.where(AdminAuditLog.target_id == target_id)
            count_stmt = count_stmt.where(AdminAuditLog.target_id == target_id)
        if action_type:
            clean_action = action_type.strip().upper()
            stmt = stmt.where(AdminAuditLog.action_type == clean_action)
            count_stmt = count_stmt.where(AdminAuditLog.action_type == clean_action)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(desc(AdminAuditLog.created_at)).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        records = res.scalars().all()

        logs_out = []
        for r in records:
            det = {}
            if r.details:
                try:
                    det = json.loads(r.details)
                except Exception:
                    det = {"raw": r.details}
            logs_out.append(AdminAuditLogOut(
                id=r.id,
                admin_account_id=r.admin_account_id,
                admin_username=r.admin_account.username if r.admin_account else None,
                action_type=r.action_type,
                target_type=r.target_type,
                target_id=r.target_id,
                reason=r.reason,
                details=det,
                created_at=r.created_at
            ))

        return AdminAuditLogListResponse(
            total=total,
            limit=limit,
            offset=offset,
            logs=logs_out
        )

    # ---------------------------------------------------------
    # Dashboard Overview & Aggregate Metrics
    # ---------------------------------------------------------
    async def get_dashboard_summary(self) -> AdminDashboardSummary:
        # Accounts counts
        tot_acc_res = await self.session.execute(select(func.count(Account.id)))
        total_accounts = tot_acc_res.scalar() or 0

        act_acc_res = await self.session.execute(select(func.count(Account.id)).where(Account.is_banned == False))
        active_accounts = act_acc_res.scalar() or 0

        susp_acc_res = await self.session.execute(select(func.count(Account.id)).where(Account.is_banned == True))
        suspended_accounts = susp_acc_res.scalar() or 0

        # Characters & Diamond counts
        tot_char_res = await self.session.execute(select(func.count(Character.gid)))
        total_characters = tot_char_res.scalar() or 0

        tot_dia_res = await self.session.execute(select(func.coalesce(func.sum(Character.diamonds), 0)))
        total_diamonds = tot_dia_res.scalar() or 0

        # Inventory counts
        tot_inv_res = await self.session.execute(select(func.coalesce(func.sum(InventoryItem.quantity), 0)))
        total_inventory_items = tot_inv_res.scalar() or 0

        # In-memory services
        lobby_svc = LobbyService.get_instance()
        room_svc = RoomService.get_instance()
        match_svc = MatchmakingService.get_instance()

        active_lobby = len(lobby_svc._presences) if hasattr(lobby_svc, "_presences") else 0
        active_rooms = len(room_svc._rooms) if hasattr(room_svc, "_rooms") else 0
        queued_tickets = len(match_svc._tickets) if hasattr(match_svc, "_tickets") else 0

        # Recent 8 audit logs
        recent_logs_resp = await self.list_audit_logs(limit=8, offset=0)

        return AdminDashboardSummary(
            total_accounts=total_accounts,
            active_accounts=active_accounts,
            suspended_accounts=suspended_accounts,
            total_characters=total_characters,
            total_diamonds=total_diamonds,
            total_inventory_items=total_inventory_items,
            active_lobby_presences=active_lobby,
            active_rooms=active_rooms,
            queued_matchmaking_tickets=queued_tickets,
            recent_activity=recent_logs_resp.logs
        )

    # ---------------------------------------------------------
    # Player Management Operations
    # ---------------------------------------------------------
    async def list_players(
        self,
        query: Optional[str] = None,
        is_banned: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> AdminPlayerListResponse:
        stmt = (
            select(Account)
            .outerjoin(Character, Account.id == Character.account_id)
            .options(selectinload(Account.character))
        )
        count_stmt = (
            select(func.count(Account.id))
            .outerjoin(Character, Account.id == Character.account_id)
        )

        filters = []
        if is_banned is not None:
            filters.append(Account.is_banned == is_banned)

        if query and query.strip():
            term = f"%{query.strip().lower()}%"
            # Match account id if numeric, or username, email, or character nickname
            try:
                acc_id_candidate = int(query.strip())
                numeric_filter = (Account.id == acc_id_candidate) | (Character.gid == acc_id_candidate)
            except ValueError:
                numeric_filter = None

            text_filter = (
                func.lower(Account.username).like(term)
                | func.lower(Account.email).like(term)
                | func.lower(Character.nickname).like(term)
            )

            if numeric_filter is not None:
                filters.append(numeric_filter | text_filter)
            else:
                filters.append(text_filter)

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar() or 0

        stmt = stmt.order_by(Account.id.asc()).limit(limit).offset(offset)
        res = await self.session.execute(stmt)
        accounts = res.scalars().all()

        players_out = []
        for acc in accounts:
            char = acc.character
            players_out.append(AdminPlayerSummary(
                account_id=acc.id,
                username=acc.username,
                email=acc.email,
                role=acc.role,
                is_banned=acc.is_banned,
                ban_reason=acc.ban_reason,
                created_at=acc.created_at,
                last_login=acc.last_login,
                character_gid=char.gid if char else None,
                character_nickname=char.nickname if char else None,
                character_level=char.level if char else None,
                diamonds=char.diamonds if char else None
            ))

        return AdminPlayerListResponse(
            total=total,
            limit=limit,
            offset=offset,
            players=players_out
        )

    async def get_player_detail(self, player_id: int, lookup_type: Optional[str] = None) -> AdminPlayerDetail:
        """
        Inspect player by Account ID or Character GID.
        """
        acc = None
        c = None
        if lookup_type == "gid":
            stmt_char = select(Character).options(selectinload(Character.account)).where(Character.gid == player_id)
            res_char = await self.session.execute(stmt_char)
            c = res_char.scalars().first()
            if c and c.account:
                acc = c.account
        else:
            # Try matching by Account ID first
            stmt = select(Account).options(selectinload(Account.character)).where(Account.id == player_id)
            res = await self.session.execute(stmt)
            acc = res.scalars().first()
            if acc:
                c = acc.character
            else:
                # Try matching by Character GID
                stmt_char = select(Character).options(selectinload(Character.account)).where(Character.gid == player_id)
                res_char = await self.session.execute(stmt_char)
                c = res_char.scalars().first()
                if c and c.account:
                    acc = c.account

        if not acc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player with ID/GID {player_id} not found."
            )

        char_data = None
        inv_data = []
        recent_txs = []

        if c:
            char_data = {
                "gid": c.gid,
                "nickname": c.nickname,
                "char_type": c.char_type,
                "level": c.level,
                "exp": c.exp,
                "gold": c.gold,
                "diamonds": c.diamonds,
                "appearances": c.appearances,
                "settings": c.settings,
                "stats": c.stats,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            }

            # Fetch inventory items
            inv_stmt = (
                select(InventoryItem)
                .options(selectinload(InventoryItem.item))
                .where(InventoryItem.character_gid == c.gid)
                .order_by(InventoryItem.id.asc())
            )
            inv_res = await self.session.execute(inv_stmt)
            for item_slot in inv_res.scalars().all():
                inv_data.append({
                    "id": item_slot.id,
                    "item_id": item_slot.item_id,
                    "quantity": item_slot.quantity,
                    "item_name": item_slot.item.name if item_slot.item else f"Item #{item_slot.item_id}",
                    "item_type": item_slot.item.item_type if item_slot.item else "unknown",
                    "stackable": item_slot.item.stackable if item_slot.item else False,
                    "max_stack": item_slot.item.max_stack if item_slot.item else 1,
                    "is_active": item_slot.item.is_active if item_slot.item else True
                })

            # Fetch recent diamond transactions
            tx_stmt = (
                select(DiamondTransaction)
                .where(DiamondTransaction.character_gid == c.gid)
                .order_by(desc(DiamondTransaction.created_at))
                .limit(10)
            )
            tx_res = await self.session.execute(tx_stmt)
            for t in tx_res.scalars().all():
                recent_txs.append({
                    "id": t.id,
                    "operation_type": t.operation_type,
                    "amount": t.amount,
                    "balance_before": t.balance_before,
                    "balance_after": t.balance_after,
                    "reason": t.reason,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                })

        # Fetch recent audit logs targeting this account or character
        target_ids = [acc.id]
        if c:
            target_ids.append(c.gid)

        audit_stmt = (
            select(AdminAuditLog)
            .options(selectinload(AdminAuditLog.admin_account))
            .where(AdminAuditLog.target_id.in_(target_ids))
            .order_by(desc(AdminAuditLog.created_at))
            .limit(10)
        )
        audit_res = await self.session.execute(audit_stmt)
        recent_audits = []
        for r in audit_res.scalars().all():
            det = {}
            if r.details:
                try:
                    det = json.loads(r.details)
                except Exception:
                    det = {"raw": r.details}
            recent_audits.append(AdminAuditLogOut(
                id=r.id,
                admin_account_id=r.admin_account_id,
                admin_username=r.admin_account.username if r.admin_account else None,
                action_type=r.action_type,
                target_type=r.target_type,
                target_id=r.target_id,
                reason=r.reason,
                details=det,
                created_at=r.created_at
            ))

        return AdminPlayerDetail(
            account_id=acc.id,
            username=acc.username,
            email=acc.email,
            role=acc.role,
            is_banned=acc.is_banned,
            ban_reason=acc.ban_reason,
            created_at=acc.created_at,
            last_login=acc.last_login,
            character=char_data,
            inventory_items=inv_data,
            recent_diamond_transactions=recent_txs,
            recent_audit_logs=recent_audits
        )

    # ---------------------------------------------------------
    # Account Suspend & Reactivate
    # ---------------------------------------------------------
    async def suspend_player(
        self,
        player_id: int,
        admin_account: Account,
        req: SuspendRequest
    ) -> AdminPlayerSummary:
        # Resolve target account
        acc = await self.resolve_account(player_id)

        # Self-suspension guard
        if admin_account.id == acc.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot suspend your own admin account."
            )

        # Prevent redundant suspension
        if acc.is_banned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is already suspended."
            )

        acc.is_banned = True
        acc.ban_reason = req.reason.strip()

        # Record audit log
        await self.record_audit_log(
            admin_account_id=admin_account.id,
            action_type="ACCOUNT_SUSPEND",
            target_type="account",
            target_id=acc.id,
            reason=req.reason.strip(),
            details={"previous_state": "active", "username": acc.username}
        )

        await self.session.commit()
        await self.session.refresh(acc)

        char = acc.character
        return AdminPlayerSummary(
            account_id=acc.id,
            username=acc.username,
            email=acc.email,
            role=acc.role,
            is_banned=acc.is_banned,
            ban_reason=acc.ban_reason,
            created_at=acc.created_at,
            last_login=acc.last_login,
            character_gid=char.gid if char else None,
            character_nickname=char.nickname if char else None,
            character_level=char.level if char else None,
            diamonds=char.diamonds if char else None
        )

    async def reactivate_player(
        self,
        player_id: int,
        admin_account: Account,
        req: ReactivateRequest
    ) -> AdminPlayerSummary:
        acc = await self.resolve_account(player_id)

        if not acc.is_banned:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is already active."
            )

        prev_reason = acc.ban_reason
        acc.is_banned = False
        acc.ban_reason = None

        await self.record_audit_log(
            admin_account_id=admin_account.id,
            action_type="ACCOUNT_REACTIVATE",
            target_type="account",
            target_id=acc.id,
            reason=req.reason.strip(),
            details={"previous_state": "suspended", "previous_reason": prev_reason, "username": acc.username}
        )

        await self.session.commit()
        await self.session.refresh(acc)

        char = acc.character
        return AdminPlayerSummary(
            account_id=acc.id,
            username=acc.username,
            email=acc.email,
            role=acc.role,
            is_banned=acc.is_banned,
            ban_reason=acc.ban_reason,
            created_at=acc.created_at,
            last_login=acc.last_login,
            character_gid=char.gid if char else None,
            character_nickname=char.nickname if char else None,
            character_level=char.level if char else None,
            diamonds=char.diamonds if char else None
        )

    async def resolve_account(self, player_id: int) -> Account:
        stmt = select(Account).options(selectinload(Account.character)).where(Account.id == player_id)
        res = await self.session.execute(stmt)
        acc = res.scalars().first()
        if not acc:
            stmt_char = select(Character).options(selectinload(Character.account)).where(Character.gid == player_id)
            res_char = await self.session.execute(stmt_char)
            char_obj = res_char.scalars().first()
            if char_obj and char_obj.account:
                acc = char_obj.account
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Player with ID/GID {player_id} not found."
                )
        return acc

    async def resolve_character_gid(self, player_id: int) -> int:
        stmt_char = select(Character.gid).where(Character.gid == player_id)
        res_char = await self.session.execute(stmt_char)
        gid = res_char.scalar()
        if gid is not None:
            return gid

        stmt_acc = select(Character.gid).where(Character.account_id == player_id)
        res_acc = await self.session.execute(stmt_acc)
        gid = res_acc.scalar()
        if gid is not None:
            return gid

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No character profile found for player ID {player_id}."
        )

# Dependency injection
async def get_admin_service(session: AsyncSession = Depends(get_db)) -> AdminService:
    return AdminService(session)
