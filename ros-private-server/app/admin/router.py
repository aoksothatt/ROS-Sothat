from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.account.models import Account
from app.account.schemas import AccountOut, RoleUpdateRequest, BanUpdateRequest
from app.account.service import AccountService, get_account_service, get_current_admin
from app.economy.schemas import (
    DiamondGrantRequest,
    DiamondDeductRequest,
    DiamondTransactionOut,
    DiamondHistoryResponse,
)
from app.economy.service import EconomyService, get_economy_service
from app.inventory.schemas import (
    ItemCreate,
    ItemUpdate,
    ItemOut,
    InventoryGrantRequest,
    InventoryRemoveRequest,
    CharacterInventoryResponse,
    InventoryTransactionOut,
    InventoryHistoryResponse,
)
from app.inventory.service import InventoryService, get_inventory_service
from app.lobby.service import LobbyService
from app.room.service import RoomService
from app.matchmaking.service import MatchmakingService
from app.admin.schemas import (
    AdminDashboardSummary,
    AdminPlayerSummary,
    AdminPlayerListResponse,
    AdminPlayerDetail,
    SuspendRequest,
    ReactivateRequest,
    AdminAuditLogListResponse,
)
from app.admin.service import AdminService, get_admin_service

router = APIRouter(prefix="/admin", tags=["Admin & Moderation"])

# -------------------------------------------------------------
# Admin Profile & Session
# -------------------------------------------------------------
@router.get("/me", response_model=AccountOut)
async def get_admin_profile(
    admin: Account = Depends(get_current_admin)
):
    """Verify admin privileges and retrieve current admin account details."""
    return AccountOut(
        id=admin.id,
        username=admin.username,
        email=admin.email,
        role=admin.role,
        is_banned=admin.is_banned,
        created_at=admin.created_at,
        last_login=admin.last_login,
        has_character=admin.character is not None
    )

# -------------------------------------------------------------
# Dashboard Summary & System Stats
# -------------------------------------------------------------
@router.get("/dashboard/summary", response_model=AdminDashboardSummary)
async def get_admin_dashboard_summary(
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Retrieve comprehensive dashboard overview metrics and recent audit activity (Admin only)."""
    return await admin_service.get_dashboard_summary()

@router.get("/stats")
async def get_system_stats(
    admin: Account = Depends(get_current_admin)
):
    """Retrieve aggregate server operational stats (Admin only)."""
    lobby_svc = LobbyService.get_instance()
    room_svc = RoomService.get_instance()
    match_svc = MatchmakingService.get_instance()

    return {
        "active_lobby_presences": len(lobby_svc._presences) if hasattr(lobby_svc, "_presences") else 0,
        "active_rooms": len(room_svc._rooms) if hasattr(room_svc, "_rooms") else 0,
        "queued_matchmaking_tickets": len(match_svc._tickets) if hasattr(match_svc, "_tickets") else 0
    }

# -------------------------------------------------------------
# Player Account Management
# -------------------------------------------------------------
@router.get("/players", response_model=AdminPlayerListResponse)
async def list_players(
    q: Optional[str] = Query(None, description="Search term for username, email, or character nickname"),
    is_banned: Optional[bool] = Query(None, description="Filter by account status (true for suspended, false for active)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    """List registered players with search, filtering, and pagination (Admin only)."""
    return await admin_service.list_players(
        query=q,
        is_banned=is_banned,
        limit=limit,
        offset=offset
    )

@router.get("/players/{player_id}", response_model=AdminPlayerDetail)
async def get_player_detail(
    player_id: int,
    lookup: Optional[str] = Query(None, description="Lookup mode: 'account' or 'gid'"),
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Retrieve complete player detail by Account ID or Character GID (Admin only)."""
    return await admin_service.get_player_detail(player_id, lookup_type=lookup)

@router.post("/players/{player_id}/suspend", response_model=AdminPlayerSummary)
async def suspend_player_endpoint(
    player_id: int,
    req: SuspendRequest,
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Suspend a player account with a mandatory reason and audit record (Admin only)."""
    return await admin_service.suspend_player(
        player_id=player_id,
        admin_account=admin,
        req=req
    )

@router.post("/players/{player_id}/reactivate", response_model=AdminPlayerSummary)
async def reactivate_player_endpoint(
    player_id: int,
    req: ReactivateRequest,
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Reactivate a suspended player account with an audit record (Admin only)."""
    return await admin_service.reactivate_player(
        player_id=player_id,
        admin_account=admin,
        req=req
    )

# -------------------------------------------------------------
# Player Diamonds Management (Player ID / GID routing)
# -------------------------------------------------------------
@router.post("/players/{player_id}/diamonds/grant", response_model=DiamondTransactionOut)
async def grant_player_diamonds(
    player_id: int,
    req: DiamondGrantRequest,
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Grant diamonds to a player's character ledger atomically (Admin only)."""
    gid = await admin_service.resolve_character_gid(player_id)
    return await economy_service.grant_diamonds(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

@router.post("/players/{player_id}/diamonds/deduct", response_model=DiamondTransactionOut)
async def deduct_player_diamonds(
    player_id: int,
    req: DiamondDeductRequest,
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Deduct diamonds from a player's character ledger atomically (Admin only)."""
    gid = await admin_service.resolve_character_gid(player_id)
    return await economy_service.deduct_diamonds(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

@router.get("/players/{player_id}/diamonds/history", response_model=DiamondHistoryResponse)
async def get_player_diamond_history(
    player_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Retrieve diamond transaction ledger history for a player (Admin only)."""
    gid = await admin_service.resolve_character_gid(player_id)
    return await economy_service.get_character_history(
        character_gid=gid,
        limit=limit,
        offset=offset
    )

# -------------------------------------------------------------
# Player Inventory Management (Player ID / GID routing)
# -------------------------------------------------------------
@router.get("/players/{player_id}/inventory", response_model=CharacterInventoryResponse)
async def get_player_inventory(
    player_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Retrieve all inventory items held by a player (Admin only)."""
    gid = await admin_service.resolve_character_gid(player_id)
    return await inventory_service.get_character_inventory(
        character_gid=gid,
        limit=limit,
        offset=offset
    )

@router.post("/players/{player_id}/inventory/grant", response_model=InventoryTransactionOut)
async def grant_player_inventory(
    player_id: int,
    req: InventoryGrantRequest,
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Grant an item to a player's character inventory atomically (Admin only)."""
    gid = await admin_service.resolve_character_gid(player_id)
    return await inventory_service.grant_inventory(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

@router.post("/players/{player_id}/inventory/remove", response_model=InventoryTransactionOut)
async def remove_player_inventory(
    player_id: int,
    req: InventoryRemoveRequest,
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service),
    inventory_service: InventoryService = Depends(get_inventory_service)
):
    """Remove an item from a player's character inventory atomically with equipped check (Admin only)."""
    gid = await admin_service.resolve_character_gid(player_id)
    return await inventory_service.remove_inventory(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

# -------------------------------------------------------------
# Administrator Audit Logs
# -------------------------------------------------------------
@router.get("/audit-logs", response_model=AdminAuditLogListResponse)
async def list_admin_audit_logs(
    admin_id: Optional[int] = Query(None, description="Filter by admin account ID"),
    target_id: Optional[int] = Query(None, description="Filter by target account ID or character GID"),
    action_type: Optional[str] = Query(None, description="Filter by action type (e.g. DIAMOND_GRANT, ACCOUNT_SUSPEND)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    admin_service: AdminService = Depends(get_admin_service)
):
    """Retrieve persistent administrator audit logs with optional filters and pagination (Admin only)."""
    return await admin_service.list_audit_logs(
        admin_id=admin_id,
        target_id=target_id,
        action_type=action_type,
        limit=limit,
        offset=offset
    )

# -------------------------------------------------------------
# Legacy / Existing Endpoints (Preserved for 100% Backward Compatibility)
# -------------------------------------------------------------
@router.get("/accounts", response_model=List[AccountOut])
async def list_accounts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    service: AccountService = Depends(get_account_service)
):
    """List registered accounts with pagination (Admin only)."""
    accounts = await service.repository.list_accounts(limit=limit, offset=offset)
    return [
        AccountOut(
            id=acc.id,
            username=acc.username,
            email=acc.email,
            role=acc.role,
            is_banned=acc.is_banned,
            created_at=acc.created_at,
            last_login=acc.last_login,
            has_character=acc.character is not None
        )
        for acc in accounts
    ]

@router.post("/accounts/{account_id}/role", response_model=AccountOut)
async def update_account_role(
    account_id: int,
    req: RoleUpdateRequest,
    admin: Account = Depends(get_current_admin),
    service: AccountService = Depends(get_account_service)
):
    """Change an account's role ('player' or 'admin'). Admin only."""
    clean_role = req.role.strip().lower()
    if clean_role not in ("player", "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{req.role}'. Supported roles: 'player', 'admin'."
        )

    # Self-demotion guard
    if admin.id == account_id and clean_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke your own admin privileges."
        )

    target = await service.repository.get_by_id(account_id, load_character=True)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found."
        )

    old_role = target.role
    updated = await service.repository.update_role(account_id, clean_role)

    # Record audit log
    admin_service = AdminService(service.repository.session)
    await admin_service.record_audit_log(
        admin_account_id=admin.id,
        action_type="ROLE_CHANGE",
        target_type="account",
        target_id=account_id,
        reason=f"Role changed from {old_role} to {clean_role}",
        details={"old_role": old_role, "new_role": clean_role, "username": target.username}
    )
    await service.repository.session.commit()

    return AccountOut(
        id=updated.id,
        username=updated.username,
        email=updated.email,
        role=updated.role,
        is_banned=updated.is_banned,
        created_at=updated.created_at,
        last_login=updated.last_login,
        has_character=updated.character is not None
    )

@router.post("/accounts/{account_id}/ban", response_model=AccountOut)
async def update_account_ban(
    account_id: int,
    req: BanUpdateRequest,
    admin: Account = Depends(get_current_admin),
    service: AccountService = Depends(get_account_service)
):
    """Ban or unban a player account. Admin only."""
    # Self-ban guard
    if admin.id == account_id and req.is_banned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot ban your own admin account."
        )

    target = await service.repository.get_by_id(account_id, load_character=True)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found."
        )

    updated = await service.repository.set_banned(account_id, req.is_banned, req.ban_reason)

    # Record audit log
    action_type = "ACCOUNT_SUSPEND" if req.is_banned else "ACCOUNT_REACTIVATE"
    admin_service = AdminService(service.repository.session)
    await admin_service.record_audit_log(
        admin_account_id=admin.id,
        action_type=action_type,
        target_type="account",
        target_id=account_id,
        reason=req.ban_reason or ("Account banned" if req.is_banned else "Account unbanned"),
        details={"is_banned": req.is_banned, "username": target.username}
    )
    await service.repository.session.commit()

    return AccountOut(
        id=updated.id,
        username=updated.username,
        email=updated.email,
        role=updated.role,
        is_banned=updated.is_banned,
        created_at=updated.created_at,
        last_login=updated.last_login,
        has_character=updated.character is not None
    )

@router.post("/characters/{gid}/diamonds/grant", response_model=DiamondTransactionOut)
async def grant_character_diamonds(
    gid: int,
    req: DiamondGrantRequest,
    admin: Account = Depends(get_current_admin),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Grant diamonds to a character ledger atomically (Admin only)."""
    return await economy_service.grant_diamonds(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

@router.post("/characters/{gid}/diamonds/deduct", response_model=DiamondTransactionOut)
async def deduct_character_diamonds(
    gid: int,
    req: DiamondDeductRequest,
    admin: Account = Depends(get_current_admin),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Deduct diamonds from a character ledger atomically (Admin only)."""
    return await economy_service.deduct_diamonds(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

@router.get("/characters/{gid}/diamonds/history", response_model=DiamondHistoryResponse)
async def get_character_diamond_history(
    gid: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Retrieve diamond transaction ledger history for a character (Admin only)."""
    return await economy_service.get_character_history(
        character_gid=gid,
        limit=limit,
        offset=offset
    )

@router.get("/items", response_model=List[ItemOut])
async def list_catalog_items(
    item_type: Optional[str] = Query(None, description="Filter by item type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    service: InventoryService = Depends(get_inventory_service)
):
    """List catalog items with optional filtering and pagination (Admin only)."""
    return await service.list_items(
        item_type=item_type,
        is_active=is_active,
        limit=limit,
        offset=offset
    )

@router.post("/items", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_catalog_item(
    req: ItemCreate,
    admin: Account = Depends(get_current_admin),
    service: InventoryService = Depends(get_inventory_service)
):
    """Create a new item in the relational catalog (Admin only)."""
    return await service.create_item(req)

@router.patch("/items/{item_id}", response_model=ItemOut)
async def update_catalog_item(
    item_id: int,
    req: ItemUpdate,
    admin: Account = Depends(get_current_admin),
    service: InventoryService = Depends(get_inventory_service)
):
    """Update catalog item attributes or activation state (Admin only)."""
    return await service.update_item(item_id, req)

@router.get("/characters/{gid}/inventory", response_model=CharacterInventoryResponse)
async def get_character_inventory(
    gid: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    service: InventoryService = Depends(get_inventory_service)
):
    """Retrieve all inventory items held by a character (Admin only)."""
    return await service.get_character_inventory(
        character_gid=gid,
        limit=limit,
        offset=offset
    )

@router.post("/characters/{gid}/inventory/grant", response_model=InventoryTransactionOut)
async def grant_character_inventory(
    gid: int,
    req: InventoryGrantRequest,
    admin: Account = Depends(get_current_admin),
    service: InventoryService = Depends(get_inventory_service)
):
    """Grant an item to a character's inventory atomically (Admin only)."""
    return await service.grant_inventory(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

@router.post("/characters/{gid}/inventory/remove", response_model=InventoryTransactionOut)
async def remove_character_inventory(
    gid: int,
    req: InventoryRemoveRequest,
    admin: Account = Depends(get_current_admin),
    service: InventoryService = Depends(get_inventory_service)
):
    """Remove an item from a character's inventory atomically (Admin only)."""
    return await service.remove_inventory(
        character_gid=gid,
        admin_account_id=admin.id,
        req=req
    )

@router.get("/characters/{gid}/inventory/history", response_model=InventoryHistoryResponse)
async def get_character_inventory_history(
    gid: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: Account = Depends(get_current_admin),
    service: InventoryService = Depends(get_inventory_service)
):
    """Retrieve audit transaction history for character inventory changes (Admin only)."""
    return await service.get_inventory_history(
        character_gid=gid,
        limit=limit,
        offset=offset
    )
