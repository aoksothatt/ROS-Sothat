import pytest
import time
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.account.models import Account
from app.player.models import Character
from app.economy.models import DiamondTransaction
from app.inventory.models import Item, InventoryItem, InventoryTransaction
from app.admin.models import AdminAuditLog
from app.admin.service import AdminService
from app.account.service import AccountService

# ---------------------------------------------------------------------------
# Test Fixtures & Setup Helpers
# ---------------------------------------------------------------------------

async def create_test_account(
    client: AsyncClient,
    username: str,
    role: str = "player"
) -> dict:
    """Helper to register and configure a test account."""
    pwd = "password123"
    resp = await client.post(
        "/api/v1/account/register",
        json={"username": username, "password": pwd}
    )
    assert resp.status_code == 201
    data = resp.json()
    account_id = data["id"]

    # Login to get bearer token
    login_resp = await client.post(
        "/api/v1/account/login",
        json={"username": username, "password": pwd}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    return {
        "id": account_id,
        "username": username,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"}
    }

async def promote_to_admin(db_session: AsyncSession, account_id: int):
    """Direct database helper to set admin role."""
    acc = await db_session.get(Account, account_id)
    assert acc is not None
    acc.role = "admin"
    await db_session.commit()

# ---------------------------------------------------------------------------
# H1: Authorization Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_dashboard_authorization_enforced(client: AsyncClient, db_session: AsyncSession):
    # 1. Unauthenticated request
    resp = await client.get("/api/v1/admin/dashboard/summary")
    assert resp.status_code == 401
    assert "Missing Bearer" in resp.json()["detail"]

    # 2. Invalid token
    resp = await client.get(
        "/api/v1/admin/dashboard/summary",
        headers={"Authorization": "Bearer invalid.signature.token"}
    )
    assert resp.status_code == 401
    assert "Invalid or expired token" in resp.json()["detail"]

    # 3. Normal player token -> 403 Forbidden
    player = await create_test_account(client, "regular_player_1")
    resp = await client.get("/api/v1/admin/dashboard/summary", headers=player["headers"])
    assert resp.status_code == 403
    assert "Admin privileges required" in resp.json()["detail"]

    resp = await client.get("/api/v1/admin/players", headers=player["headers"])
    assert resp.status_code == 403

    resp = await client.get("/api/v1/admin/audit-logs", headers=player["headers"])
    assert resp.status_code == 403

    # 4. Admin access succeeds
    admin = await create_test_account(client, "super_admin_1")
    await promote_to_admin(db_session, admin["id"])

    resp = await client.get("/api/v1/admin/dashboard/summary", headers=admin["headers"])
    assert resp.status_code == 200
    summary = resp.json()
    assert "total_accounts" in summary
    assert "total_diamonds" in summary

# ---------------------------------------------------------------------------
# H2: Dashboard Summary & Metrics Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_dashboard_summary_metrics(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "summary_admin")
    await promote_to_admin(db_session, admin["id"])

    # Create 2 players, one with character
    p1 = await create_test_account(client, "player_metric_1")
    p2 = await create_test_account(client, "player_metric_2")

    # Create character for p1
    char_resp = await client.post(
        "/api/v1/player/character",
        headers=p1["headers"],
        json={"nickname": "MetricSniper", "char_type": 0}
    )
    assert char_resp.status_code == 201

    # Check summary
    resp = await client.get("/api/v1/admin/dashboard/summary", headers=admin["headers"])
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_accounts"] >= 3
    assert data["active_accounts"] >= 3
    assert data["suspended_accounts"] == 0
    assert data["total_characters"] >= 1
    assert data["total_diamonds"] >= 100  # Default diamonds is 100

# ---------------------------------------------------------------------------
# H3: Player Search & Pagination Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_player_listing_and_search(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "search_admin")
    await promote_to_admin(db_session, admin["id"])

    p_alpha = await create_test_account(client, "alpha_warrior")
    p_beta = await create_test_account(client, "beta_sniper")

    await client.post(
        "/api/v1/player/character",
        headers=p_alpha["headers"],
        json={"nickname": "AlphaGhost", "char_type": 0}
    )

    # 1. List all players
    resp = await client.get("/api/v1/admin/players", headers=admin["headers"])
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 3
    assert len(body["players"]) >= 3

    # 2. Search by username substring
    resp = await client.get("/api/v1/admin/players?q=alpha", headers=admin["headers"])
    assert resp.status_code == 200
    search_body = resp.json()
    assert search_body["total"] == 1
    assert search_body["players"][0]["username"] == "alpha_warrior"
    assert search_body["players"][0]["character_nickname"] == "AlphaGhost"

    # 3. Search by character nickname
    resp = await client.get("/api/v1/admin/players?q=Ghost", headers=admin["headers"])
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["players"][0]["username"] == "alpha_warrior"

    # 4. Pagination limits
    resp = await client.get("/api/v1/admin/players?limit=1&offset=0", headers=admin["headers"])
    assert resp.status_code == 200
    assert len(resp.json()["players"]) == 1

# ---------------------------------------------------------------------------
# H4: Player Detail Inspection Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_player_detail_inspection(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "detail_admin")
    await promote_to_admin(db_session, admin["id"])

    target = await create_test_account(client, "target_player")
    char_resp = await client.post(
        "/api/v1/player/character",
        headers=target["headers"],
        json={"nickname": "TargetLord", "char_type": 1}
    )
    assert char_resp.status_code == 201
    gid = char_resp.json()["gid"]

    # 1. Inspect by Account ID
    resp = await client.get(f"/api/v1/admin/players/{target['id']}", headers=admin["headers"])
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["account_id"] == target["id"]
    assert detail["username"] == "target_player"
    assert detail["character"]["gid"] == gid
    assert detail["character"]["nickname"] == "TargetLord"

    # 2. Inspect by Character GID explicitly
    resp_by_gid = await client.get(f"/api/v1/admin/players/{gid}?lookup=gid", headers=admin["headers"])
    assert resp_by_gid.status_code == 200
    assert resp_by_gid.json()["account_id"] == target["id"]

    # 3. Nonexistent player returns 404
    resp_404 = await client.get("/api/v1/admin/players/999999", headers=admin["headers"])
    assert resp_404.status_code == 404

# ---------------------------------------------------------------------------
# H5: Account Suspension & Reactivation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_player_suspend_and_reactivate(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "moderator_admin")
    await promote_to_admin(db_session, admin["id"])

    suspect = await create_test_account(client, "suspect_player")

    # 1. Admin self-suspension guard
    self_suspend = await client.post(
        f"/api/v1/admin/players/{admin['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Self-test ban"}
    )
    assert self_suspend.status_code == 400
    assert "Cannot suspend your own admin account" in self_suspend.json()["detail"]

    # 2. Suspend suspect player
    suspend_resp = await client.post(
        f"/api/v1/admin/players/{suspect['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Suspected speed hacking"}
    )
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["is_banned"] is True
    assert suspend_resp.json()["ban_reason"] == "Suspected speed hacking"

    # 3. Duplicate suspend rejected
    dup_suspend = await client.post(
        f"/api/v1/admin/players/{suspect['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Another ban reason"}
    )
    assert dup_suspend.status_code == 400
    assert "already suspended" in dup_suspend.json()["detail"]

    # 4. Suspended player is blocked from accessing protected endpoints
    blocked_resp = await client.get("/api/v1/account/me", headers=suspect["headers"])
    assert blocked_resp.status_code == 403
    assert "Account is banned" in blocked_resp.json()["detail"]

    # 5. Reactivate suspect player
    reactivate_resp = await client.post(
        f"/api/v1/admin/players/{suspect['id']}/reactivate",
        headers=admin["headers"],
        json={"reason": "False positive appeal approved"}
    )
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["is_banned"] is False
    assert reactivate_resp.json()["ban_reason"] is None

    # 6. Duplicate reactivate rejected
    dup_reactivate = await client.post(
        f"/api/v1/admin/players/{suspect['id']}/reactivate",
        headers=admin["headers"],
        json={"reason": "Repeated reactivation"}
    )
    assert dup_reactivate.status_code == 400
    assert "already active" in dup_reactivate.json()["detail"]

    # 7. Unbanned player can now access protected endpoints
    unblocked_resp = await client.get("/api/v1/account/me", headers=suspect["headers"])
    assert unblocked_resp.status_code == 200

# ---------------------------------------------------------------------------
# H6: Atomic Diamond Management via Admin API
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_diamond_grant_and_deduct_via_player_endpoint(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "banker_admin")
    await promote_to_admin(db_session, admin["id"])

    player = await create_test_account(client, "economy_player")
    char_resp = await client.post(
        "/api/v1/player/character",
        headers=player["headers"],
        json={"nickname": "DiamondViper", "char_type": 0}
    )
    assert char_resp.status_code == 201

    # Initial balance is 100
    # 1. Grant 250 diamonds using account ID
    grant_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/diamonds/grant",
        headers=admin["headers"],
        json={
            "amount": 250,
            "reason": "Bug bounty reward",
            "idempotency_key": "p05-grant-key-001"
        }
    )
    assert grant_resp.status_code == 200
    tx = grant_resp.json()
    assert tx["operation_type"] == "GRANT"
    assert tx["amount"] == 250
    assert tx["balance_before"] == 100
    assert tx["balance_after"] == 350

    # 2. Idempotent replay with same key returns original result
    replay_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/diamonds/grant",
        headers=admin["headers"],
        json={
            "amount": 250,
            "reason": "Bug bounty reward",
            "idempotency_key": "p05-grant-key-001"
        }
    )
    assert replay_resp.status_code == 200
    assert replay_resp.json()["balance_after"] == 350

    # 3. Deduct 150 diamonds
    deduct_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/diamonds/deduct",
        headers=admin["headers"],
        json={
            "amount": 150,
            "reason": "Tournament fee correction",
            "idempotency_key": "p05-deduct-key-001"
        }
    )
    assert deduct_resp.status_code == 200
    tx_deduct = deduct_resp.json()
    assert tx_deduct["balance_before"] == 350
    assert tx_deduct["balance_after"] == 200

    # 4. Overdraft deduction rejected
    overdraft_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/diamonds/deduct",
        headers=admin["headers"],
        json={
            "amount": 999999,
            "reason": "Excessive deduction",
            "idempotency_key": "p05-deduct-fail-001"
        }
    )
    assert overdraft_resp.status_code == 400
    assert "Insufficient diamond balance" in overdraft_resp.json()["detail"]

    # 5. Diamond transaction history endpoint
    hist_resp = await client.get(
        f"/api/v1/admin/players/{player['id']}/diamonds/history",
        headers=admin["headers"]
    )
    assert hist_resp.status_code == 200
    hist = hist_resp.json()
    assert hist["current_balance"] == 200
    assert hist["total_transactions"] >= 2

# ---------------------------------------------------------------------------
# H7: Inventory Management & Equipped Clothing Safeguard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_inventory_grant_and_equipped_clothing_removal_safety(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "inventory_admin")
    await promote_to_admin(db_session, admin["id"])

    player = await create_test_account(client, "wardrobe_player")
    char_resp = await client.post(
        "/api/v1/player/character",
        headers=player["headers"],
        json={"nickname": "FashionNinja", "char_type": 1}
    )
    assert char_resp.status_code == 201

    # 1. Create a catalog clothing item
    cat_resp = await client.post(
        "/api/v1/admin/items",
        headers=admin["headers"],
        json={
            "item_code": "CLOTH_PARACHUTE_99",
            "name": "Dragon Parachute",
            "description": "Legendary drop glider",
            "item_type": "clothing",
            "stackable": False,
            "max_stack": 1
        }
    )
    assert cat_resp.status_code == 201
    item_id = cat_resp.json()["id"]

    # 2. Grant item to player
    grant_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/inventory/grant",
        headers=admin["headers"],
        json={
            "item_id": item_id,
            "quantity": 1,
            "reason": "Special event reward",
            "idempotency_key": "p05-inv-grant-001"
        }
    )
    assert grant_resp.status_code == 200
    assert grant_resp.json()["quantity_after"] == 1

    # 3. Player equips this item
    equip_resp = await client.put(
        "/api/v1/player/character/appearances",
        headers=player["headers"],
        json={
            "appearances": {
                "equipped_clothing": [10001, item_id],
                "unlocked_items": [10001, item_id],
                "active_weapon_skin": 0
            }
        }
    )
    assert equip_resp.status_code == 200
    assert item_id in equip_resp.json()["appearances"]["equipped_clothing"]

    # 4. Admin removes the item down to 0
    remove_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/inventory/remove",
        headers=admin["headers"],
        json={
            "item_id": item_id,
            "quantity": 1,
            "reason": "Fraudulent claim revoked",
            "idempotency_key": "p05-inv-remove-001"
        }
    )
    assert remove_resp.status_code == 200
    assert remove_resp.json()["quantity_after"] == 0

    # 5. Verify the item was safely unequipped from character appearances!
    detail_resp = await client.get(
        f"/api/v1/admin/players/{player['id']}",
        headers=admin["headers"]
    )
    assert detail_resp.status_code == 200
    updated_char = detail_resp.json()["character"]
    # Item must NOT remain in equipped_clothing
    assert item_id not in updated_char["appearances"]["equipped_clothing"]
    assert 10001 in updated_char["appearances"]["equipped_clothing"]

# ---------------------------------------------------------------------------
# H8: Administrator Audit Logs Tracking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_audit_logs_tracking(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "auditor_admin")
    await promote_to_admin(db_session, admin["id"])

    player = await create_test_account(client, "audited_player")

    # Perform suspend action to generate audit log
    await client.post(
        f"/api/v1/admin/players/{player['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Suspended for audit testing"}
    )

    # Query audit logs
    logs_resp = await client.get(
        "/api/v1/admin/audit-logs",
        headers=admin["headers"]
    )
    assert logs_resp.status_code == 200
    logs_body = logs_resp.json()
    assert logs_body["total"] >= 1
    assert len(logs_body["logs"]) >= 1

    # Filter by action_type
    filtered_resp = await client.get(
        "/api/v1/admin/audit-logs?action_type=ACCOUNT_SUSPEND",
        headers=admin["headers"]
    )
    assert filtered_resp.status_code == 200
    for entry in filtered_resp.json()["logs"]:
        assert entry["action_type"] == "ACCOUNT_SUSPEND"
        assert "audit testing" in entry["reason"]
        assert entry["admin_account_id"] == admin["id"]

# ---------------------------------------------------------------------------
# H9: Audit Log Referential Retention & Immutability (Stage B)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_audit_log_referential_retention(client: AsyncClient, db_session: AsyncSession):
    admin = await create_test_account(client, "retention_admin")
    await promote_to_admin(db_session, admin["id"])

    player = await create_test_account(client, "retention_player")

    # 1. Create audit records via admin operations (suspend and reactivate)
    susp_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/suspend",
        headers=admin["headers"],
        json={"reason": "Audit retention verification"}
    )
    assert susp_resp.status_code == 200

    react_resp = await client.post(
        f"/api/v1/admin/players/{player['id']}/reactivate",
        headers=admin["headers"],
        json={"reason": "Appeal accepted"}
    )
    assert react_resp.status_code == 200

    # 2. Verify audit logs exist
    logs_resp = await client.get(
        f"/api/v1/admin/audit-logs?admin_id={admin['id']}",
        headers=admin["headers"]
    )
    assert logs_resp.status_code == 200
    assert logs_resp.json()["total"] == 2

    # 3. Confirm API layer provides zero deletion endpoints
    del_resp = await client.delete("/api/v1/admin/audit-logs")
    assert del_resp.status_code in (404, 405)

    del_account_resp = await client.delete(f"/api/v1/admin/accounts/{admin['id']}")
    assert del_account_resp.status_code in (404, 405)

    del_player_resp = await client.delete(f"/api/v1/admin/players/{player['id']}")
    assert del_player_resp.status_code in (404, 405)

    # 4. Verify existing audit history remains completely readable
    hist_resp = await client.get("/api/v1/admin/audit-logs", headers=admin["headers"])
    assert hist_resp.status_code == 200
    assert any(log["admin_account_id"] == admin["id"] for log in hist_resp.json()["logs"])

    # 5. Verify new audit records can still be inserted normally
    audit_service = AdminService(db_session)
    await audit_service.record_audit_log(
        admin_account_id=admin["id"],
        action_type="ROLE_CHANGE",
        target_type="account",
        target_id=player["id"],
        reason="Manual role elevation",
        details={"new_role": "admin"}
    )
    await db_session.commit()

    # Total audit logs for this admin is now 3
    updated_logs = await client.get(
        f"/api/v1/admin/audit-logs?admin_id={admin['id']}",
        headers=admin["headers"]
    )
    assert updated_logs.status_code == 200
    assert updated_logs.json()["total"] == 3

    # 6. Verify admin permissions and role protections remain unchanged
    unauth_resp = await client.get("/api/v1/admin/audit-logs")
    assert unauth_resp.status_code == 401
