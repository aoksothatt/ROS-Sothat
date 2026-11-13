import asyncio
import os
import tempfile
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database.base import Base
from app.account.models import Account
from app.player.models import Character
from app.inventory.models import Item, InventoryItem, InventoryTransaction
from app.inventory.repository import InventoryRepository
from app.inventory.service import InventoryService
from app.inventory.schemas import InventoryGrantRequest, InventoryRemoveRequest

@pytest.fixture
async def admin_auth(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Creates and authenticates an admin account."""
    res = await client.post("/api/v1/account/register", json={
        "username": "inv_admin",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 201
    admin_id = res.json()["id"]

    stmt = update(Account).where(Account.id == admin_id).values(role="admin")
    await db_session.execute(stmt)
    await db_session.commit()

    login_res = await client.post("/api/v1/account/login", json={
        "username": "inv_admin",
        "password": "AdminPassword123!"
    })
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "admin_id": admin_id
    }

@pytest.fixture
async def player_auth(client: AsyncClient) -> dict:
    """Creates and authenticates a normal player account."""
    res = await client.post("/api/v1/account/register", json={
        "username": "inv_player",
        "password": "PlayerPassword123!"
    })
    assert res.status_code == 201
    player_id = res.json()["id"]

    login_res = await client.post("/api/v1/account/login", json={
        "username": "inv_player",
        "password": "PlayerPassword123!"
    })
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "account_id": player_id
    }

@pytest.fixture
async def player_character(client: AsyncClient, player_auth: dict) -> dict:
    """Creates a character profile for the test player."""
    res = await client.post(
        "/api/v1/player/character",
        headers=player_auth["headers"],
        json={"nickname": "InvExplorer", "char_type": 0}
    )
    assert res.status_code == 201
    return res.json()

# -----------------------------------------------------------------
# 1. Catalog Tests
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_admin_create_and_manage_catalog_items(
    client: AsyncClient,
    admin_auth: dict
):
    """Admin creates items, updates them, and lists catalog with filters."""
    # 1. Create a non-stackable weapon skin
    res_skin = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "WEAP_M4A1_CYBER",
            "name": "M4A1 Cyberpunk Edition",
            "description": "High-tech neon finish rifle skin",
            "item_type": "WEAPON_SKIN",
            "icon": "icons/weapons/m4a1_cyber.png",
            "stackable": False,
            "max_stack": 1,
            "is_active": True
        }
    )
    assert res_skin.status_code == 201
    skin_data = res_skin.json()
    assert skin_data["item_code"] == "WEAP_M4A1_CYBER"
    assert skin_data["stackable"] is False
    assert skin_data["max_stack"] == 1

    # 2. Duplicate item_code rejected with 409
    res_dup = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "WEAP_M4A1_CYBER",
            "name": "Duplicate Item",
            "item_type": "WEAPON_SKIN"
        }
    )
    assert res_dup.status_code == 409

    # 3. Create a stackable consumable
    res_med = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "CONS_MEDKIT_ADV",
            "name": "Advanced First Aid Kit",
            "description": "Restores 75 HP over 5 seconds",
            "item_type": "CONSUMABLE",
            "stackable": True,
            "max_stack": 10,
            "is_active": True
        }
    )
    assert res_med.status_code == 201
    med_id = res_med.json()["id"]

    # 4. Patch update item
    patch_res = await client.patch(
        f"/api/v1/admin/items/{med_id}",
        headers=admin_auth["headers"],
        json={"name": "Military MedKit", "max_stack": 15}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Military MedKit"
    assert patch_res.json()["max_stack"] == 15

    # 5. List items with type filter
    list_res = await client.get(
        "/api/v1/admin/items?item_type=CONSUMABLE",
        headers=admin_auth["headers"]
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["item_code"] == "CONS_MEDKIT_ADV"

# -----------------------------------------------------------------
# 2. Security & RBAC Tests
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_inventory_rbac_protection(
    client: AsyncClient,
    player_auth: dict,
    player_character: dict
):
    """Unauthenticated users receive 401; players receive 403 on admin endpoints."""
    gid = player_character["gid"]

    # Unauthenticated
    assert (await client.get("/api/v1/admin/items")).status_code == 401
    assert (await client.post("/api/v1/admin/items", json={})).status_code == 401
    assert (await client.get(f"/api/v1/admin/characters/{gid}/inventory")).status_code == 401
    assert (await client.post(f"/api/v1/admin/characters/{gid}/inventory/grant", json={})).status_code == 401
    assert (await client.post(f"/api/v1/admin/characters/{gid}/inventory/remove", json={})).status_code == 401

    # Normal player attempting admin endpoints -> 403
    assert (await client.get("/api/v1/admin/items", headers=player_auth["headers"])).status_code == 403
    assert (await client.get(f"/api/v1/admin/characters/{gid}/inventory", headers=player_auth["headers"])).status_code == 403
    assert (await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=player_auth["headers"],
        json={"item_id": 1, "quantity": 1, "idempotency_key": "k", "reason": "r"}
    )).status_code == 403

    # Player can view their own inventory via player route
    own_inv_res = await client.get("/api/v1/player/character/inventory", headers=player_auth["headers"])
    assert own_inv_res.status_code == 200
    assert own_inv_res.json()["character_gid"] == gid
    assert own_inv_res.json()["total_items"] == 0

# -----------------------------------------------------------------
# 3. Grant & Removal Lifecycle Tests
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_inventory_grant_and_remove_flow(
    client: AsyncClient,
    admin_auth: dict,
    player_auth: dict,
    player_character: dict
):
    """Admin grants non-stackable and stackable items, and removes items down to zero."""
    gid = player_character["gid"]

    # 1. Create items
    res_skin = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "CLOTH_TACTICAL_VEST",
            "name": "Tactical Armor Vest",
            "item_type": "CLOTHING",
            "stackable": False,
            "max_stack": 1
        }
    )
    vest_id = res_skin.json()["id"]

    res_ammo = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "AMMO_556_CRATE",
            "name": "5.56mm Ammo Box",
            "item_type": "CONSUMABLE",
            "stackable": True,
            "max_stack": 100
        }
    )
    ammo_id = res_ammo.json()["id"]

    # 2. Grant non-stackable item
    g_vest = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": vest_id,
            "quantity": 1,
            "idempotency_key": "grant_vest_01",
            "reason": "Starter loadout vest"
        }
    )
    assert g_vest.status_code == 200
    assert g_vest.json()["quantity_before"] == 0
    assert g_vest.json()["quantity_after"] == 1
    assert g_vest.json()["operation_type"] == "GRANT"

    # 3. Attempting to grant non-stackable item again fails with 400
    g_vest_dup = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": vest_id,
            "quantity": 1,
            "idempotency_key": "grant_vest_dup",
            "reason": "Duplicate attempt"
        }
    )
    assert g_vest_dup.status_code == 400
    assert "already owns it" in g_vest_dup.json()["detail"]

    # 4. Grant stackable ammo
    g_ammo1 = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": ammo_id,
            "quantity": 40,
            "idempotency_key": "grant_ammo_01",
            "reason": "Ammo drop"
        }
    )
    assert g_ammo1.status_code == 200
    assert g_ammo1.json()["quantity_before"] == 0
    assert g_ammo1.json()["quantity_after"] == 40

    # 5. Grant more stackable ammo into same slot
    g_ammo2 = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": ammo_id,
            "quantity": 50,
            "idempotency_key": "grant_ammo_02",
            "reason": "Second ammo drop"
        }
    )
    assert g_ammo2.status_code == 200
    assert g_ammo2.json()["quantity_before"] == 40
    assert g_ammo2.json()["quantity_after"] == 90

    # 6. Exceeding max stack (current 90 + 20 > 100) fails with 400
    g_ammo_overflow = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": ammo_id,
            "quantity": 20,
            "idempotency_key": "grant_ammo_overflow",
            "reason": "Overflow attempt"
        }
    )
    assert g_ammo_overflow.status_code == 400
    assert "exceed max stack limit" in g_ammo_overflow.json()["detail"]

    # 7. Player inspects own inventory
    p_inv = await client.get("/api/v1/player/character/inventory", headers=player_auth["headers"])
    assert p_inv.status_code == 200
    slots = p_inv.json()["items"]
    assert len(slots) == 2

    # 8. Remove partial ammo (remove 30 of 90)
    r_ammo1 = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/remove",
        headers=admin_auth["headers"],
        json={
            "item_id": ammo_id,
            "quantity": 30,
            "idempotency_key": "rem_ammo_01",
            "reason": "Expended ammo"
        }
    )
    assert r_ammo1.status_code == 200
    assert r_ammo1.json()["quantity_before"] == 90
    assert r_ammo1.json()["quantity_after"] == 60
    assert r_ammo1.json()["operation_type"] == "REMOVE"

    # 9. Overdraft removal fails with 400
    r_ammo_over = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/remove",
        headers=admin_auth["headers"],
        json={
            "item_id": ammo_id,
            "quantity": 61,
            "idempotency_key": "rem_ammo_over",
            "reason": "Overdraft attempt"
        }
    )
    assert r_ammo_over.status_code == 400
    assert "Insufficient item quantity" in r_ammo_over.json()["detail"]

    # 10. Remove all remaining ammo down to zero (slot deleted)
    r_ammo2 = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/remove",
        headers=admin_auth["headers"],
        json={
            "item_id": ammo_id,
            "quantity": 60,
            "idempotency_key": "rem_ammo_02",
            "reason": "Consume all"
        }
    )
    assert r_ammo2.status_code == 200
    assert r_ammo2.json()["quantity_after"] == 0

    # Verify character inventory now only has the vest
    p_inv_after = await client.get("/api/v1/player/character/inventory", headers=player_auth["headers"])
    assert len(p_inv_after.json()["items"]) == 1
    assert p_inv_after.json()["items"][0]["item_id"] == vest_id

# -----------------------------------------------------------------
# 4. Idempotency & Validation Tests
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_inventory_idempotency_and_validation(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict
):
    """Exact replays return identical records; conflicting replays return 409."""
    gid = player_character["gid"]

    item_res = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "CONS_ENERGY_DRINK",
            "name": "Energy Drink",
            "item_type": "CONSUMABLE",
            "stackable": True,
            "max_stack": 50
        }
    )
    item_id = item_res.json()["id"]

    # 1. First grant
    res1 = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": item_id,
            "quantity": 10,
            "idempotency_key": "idemp_inv_01",
            "reason": "Energy refill"
        }
    )
    assert res1.status_code == 200
    tx1 = res1.json()

    # 2. Replay with exact same parameters -> 200 OK, same tx id
    res2 = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": item_id,
            "quantity": 10,
            "idempotency_key": "idemp_inv_01",
            "reason": "Energy refill"
        }
    )
    assert res2.status_code == 200
    assert res2.json()["id"] == tx1["id"]
    assert res2.json()["quantity_after"] == 10

    # 3. Conflicting replay with different quantity -> 409 Conflict
    res_conflict = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": item_id,
            "quantity": 20,
            "idempotency_key": "idemp_inv_01",
            "reason": "Different quantity"
        }
    )
    assert res_conflict.status_code == 409

    # 4. Whitespace-only reason rejected with 422
    res_ws = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={
            "item_id": item_id,
            "quantity": 5,
            "idempotency_key": "idemp_ws",
            "reason": "   "
        }
    )
    assert res_ws.status_code == 422

# -----------------------------------------------------------------
# 5. Concurrency & Rollback Tests
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_inventory_grants_and_removals():
    """
    Test multi-connection concurrency using isolated file-based SQLite database.
    Verifies that simultaneous operations accumulate safely and overdrafts are rejected.
    """
    db_path = os.path.join(tempfile.gettempdir(), f"inv_conc_{os.getpid()}.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 30.0})
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        # Setup accounts and item
        async with session_factory() as s:
            admin = Account(username="admin_c", password_hash="x", salt="y", role="admin")
            s.add(admin)
            await s.commit()
            char = Character(account_id=admin.id, nickname="ConcPlayer", char_type=0)
            s.add(char)
            await s.commit()
            item = Item(item_code="AMMO_BOX", name="Ammo Box", item_type="CONSUMABLE", stackable=True, max_stack=500)
            s.add(item)
            await s.commit()
            gid = char.gid
            item_id = item.id
            admin_id = admin.id

        # 1. Concurrent Grants
        async def grant(amt: int, key: str):
            async with session_factory() as s:
                svc = InventoryService(InventoryRepository(s))
                return await svc.grant_inventory(
                    gid,
                    admin_id,
                    InventoryGrantRequest(item_id=item_id, quantity=amt, idempotency_key=key, reason="Concurrent grant")
                )

        # Execute two grants of 50 in parallel
        g_res = await asyncio.gather(grant(50, "cg_1"), grant(50, "cg_2"), return_exceptions=True)
        assert all(not isinstance(r, Exception) for r in g_res)

        async with session_factory() as s:
            slot = (await s.execute(select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id))).scalars().first()
            assert slot.quantity == 100

        # 2. Concurrent Deductions (prevent overdraft)
        async def remove(amt: int, key: str):
            async with session_factory() as s:
                svc = InventoryService(InventoryRepository(s))
                return await svc.remove_inventory(
                    gid,
                    admin_id,
                    InventoryRemoveRequest(item_id=item_id, quantity=amt, idempotency_key=key, reason="Concurrent remove")
                )

        # Current quantity is 100; attempt two simultaneous removals of 80
        r_res = await asyncio.gather(remove(80, "cr_1"), remove(80, "cr_2"), return_exceptions=True)
        successes = [r for r in r_res if not isinstance(r, Exception)]
        failures = [r for r in r_res if isinstance(r, Exception)]
        assert len(successes) == 1
        assert len(failures) == 1

        async with session_factory() as s:
            slot_after = (await s.execute(select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id))).scalars().first()
            assert slot_after.quantity == 20
    finally:
        await engine.dispose()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

# -----------------------------------------------------------------
# 6. History, Pagination & Rollback Tests
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_inventory_history_ordering_and_pagination(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict
):
    """History endpoint correctly orders newest transactions first and paginates."""
    gid = player_character["gid"]

    item_res = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "CONS_BANDAGE_PACK",
            "name": "Bandage Pack",
            "item_type": "CONSUMABLE",
            "stackable": True,
            "max_stack": 20
        }
    )
    item_id = item_res.json()["id"]

    # 1. Grant 5
    await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={"item_id": item_id, "quantity": 5, "idempotency_key": "h_1", "reason": "First"}
    )
    # 2. Grant 10
    await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={"item_id": item_id, "quantity": 10, "idempotency_key": "h_2", "reason": "Second"}
    )
    # 3. Remove 4
    await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/remove",
        headers=admin_auth["headers"],
        json={"item_id": item_id, "quantity": 4, "idempotency_key": "h_3", "reason": "Third"}
    )

    # Full history
    hist_res = await client.get(
        f"/api/v1/admin/characters/{gid}/inventory/history",
        headers=admin_auth["headers"]
    )
    assert hist_res.status_code == 200
    data = hist_res.json()
    assert data["character_gid"] == gid
    assert data["total_transactions"] == 3
    txs = data["transactions"]
    assert len(txs) == 3

    # Newest first
    assert txs[0]["operation_type"] == "REMOVE"
    assert txs[0]["quantity"] == 4
    assert txs[1]["operation_type"] == "GRANT"
    assert txs[1]["quantity"] == 10
    assert txs[2]["operation_type"] == "GRANT"
    assert txs[2]["quantity"] == 5

    # Pagination: limit=2, offset=0
    p1 = await client.get(
        f"/api/v1/admin/characters/{gid}/inventory/history?limit=2&offset=0",
        headers=admin_auth["headers"]
    )
    assert len(p1.json()["transactions"]) == 2
    assert p1.json()["transactions"][0]["quantity"] == 4

    # Pagination: limit=2, offset=2
    p2 = await client.get(
        f"/api/v1/admin/characters/{gid}/inventory/history?limit=2&offset=2",
        headers=admin_auth["headers"]
    )
    assert len(p2.json()["transactions"]) == 1
    assert p2.json()["transactions"][0]["quantity"] == 5

@pytest.mark.asyncio
async def test_invalid_item_or_character_ids_rejected(
    client: AsyncClient,
    admin_auth: dict
):
    """Operations referencing non-existent characters or items return HTTP 404."""
    non_existent = 999999

    # Character 404
    g_res = await client.post(
        f"/api/v1/admin/characters/{non_existent}/inventory/grant",
        headers=admin_auth["headers"],
        json={"item_id": 1, "quantity": 1, "idempotency_key": "nf_1", "reason": "Test"}
    )
    assert g_res.status_code == 404

    # Item 404
    # First create a valid character
    reg = await client.post("/api/v1/account/register", json={"username": "nf_user", "password": "Password123!"})
    login = await client.post("/api/v1/account/login", json={"username": "nf_user", "password": "Password123!"})
    c_res = await client.post(
        "/api/v1/player/character",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        json={"nickname": "NFCharacter", "char_type": 0}
    )
    gid = c_res.json()["gid"]

    item_nf = await client.post(
        f"/api/v1/admin/characters/{gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={"item_id": non_existent, "quantity": 1, "idempotency_key": "nf_2", "reason": "Test"}
    )
    assert item_nf.status_code == 404

@pytest.mark.asyncio
async def test_database_check_constraints_prevent_invalid_inventory_records(
    db_session: AsyncSession
):
    """Database constraints reject invalid stack limits and negative quantities."""
    from sqlalchemy.exc import IntegrityError

    # 1. Item max_stack < 1
    invalid_item = Item(
        item_code="INVALID_STACK",
        name="Invalid",
        item_type="CONSUMABLE",
        max_stack=0  # Violates chk_item_max_stack_positive
    )
    db_session.add(invalid_item)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

# -----------------------------------------------------------------
# 7. Finding CAT-01: Catalog max_stack Reduction Safety Tests
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_catalog_max_stack_reduction_safety(
    client: AsyncClient,
    admin_auth: dict
):
    """
    Finding CAT-01: Verify that lowering max_stack is rejected with HTTP 409
    if active player inventories hold quantities exceeding the proposed limit,
    leaving catalog and inventory quantities completely untouched.
    """
    # 1. Create a stackable item with max_stack = 50
    res_item = await client.post(
        "/api/v1/admin/items",
        headers=admin_auth["headers"],
        json={
            "item_code": "CONS_MED_PACK_SAFE",
            "name": "Standard Medical Pack",
            "description": "Restores health",
            "item_type": "CONSUMABLE",
            "stackable": True,
            "max_stack": 50
        }
    )
    assert res_item.status_code == 201
    item_id = res_item.json()["id"]

    # 2. Setup two player accounts with characters
    # Player 1
    p1_reg = await client.post("/api/v1/account/register", json={"username": "cat_player1", "password": "Password123!"})
    p1_login = await client.post("/api/v1/account/login", json={"username": "cat_player1", "password": "Password123!"})
    p1_headers = {"Authorization": f"Bearer {p1_login.json()['access_token']}"}
    p1_char = await client.post("/api/v1/player/character", headers=p1_headers, json={"nickname": "CatHero1", "char_type": 0})
    p1_gid = p1_char.json()["gid"]

    # Player 2
    p2_reg = await client.post("/api/v1/account/register", json={"username": "cat_player2", "password": "Password123!"})
    p2_login = await client.post("/api/v1/account/login", json={"username": "cat_player2", "password": "Password123!"})
    p2_headers = {"Authorization": f"Bearer {p2_login.json()['access_token']}"}
    p2_char = await client.post("/api/v1/player/character", headers=p2_headers, json={"nickname": "CatHero2", "char_type": 0})
    p2_gid = p2_char.json()["gid"]

    # 3. Grant 35 items to Player 1 and 20 items to Player 2
    g1 = await client.post(
        f"/api/v1/admin/characters/{p1_gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={"item_id": item_id, "quantity": 35, "idempotency_key": "cat_g1", "reason": "P1 initial"}
    )
    assert g1.status_code == 200

    g2 = await client.post(
        f"/api/v1/admin/characters/{p2_gid}/inventory/grant",
        headers=admin_auth["headers"],
        json={"item_id": item_id, "quantity": 20, "idempotency_key": "cat_g2", "reason": "P2 initial"}
    )
    assert g2.status_code == 200

    # 4. Attempt to lower max_stack to 30 (fails because Player 1 holds 35 > 30)
    unsafe_patch = await client.patch(
        f"/api/v1/admin/items/{item_id}",
        headers=admin_auth["headers"],
        json={"max_stack": 30}
    )
    assert unsafe_patch.status_code == 409
    error_detail = unsafe_patch.json()["detail"]
    assert "existing player inventory contains stacks up to 35" in error_detail
    assert "Cannot reduce max_stack to 30" in error_detail

    # 5. Verify catalog and player inventories remain unchanged
    cat_check = await client.get(
        f"/api/v1/admin/items?item_type=CONSUMABLE",
        headers=admin_auth["headers"]
    )
    item_in_catalog = next(it for it in cat_check.json() if it["id"] == item_id)
    assert item_in_catalog["max_stack"] == 50

    p1_inv = await client.get("/api/v1/player/character/inventory", headers=p1_headers)
    assert p1_inv.json()["items"][0]["quantity"] == 35

    p2_inv = await client.get("/api/v1/player/character/inventory", headers=p2_headers)
    assert p2_inv.json()["items"][0]["quantity"] == 20

    # 6. Lowering max_stack to 40 (succeeds because 40 >= max_held 35)
    safe_patch = await client.patch(
        f"/api/v1/admin/items/{item_id}",
        headers=admin_auth["headers"],
        json={"max_stack": 40}
    )
    assert safe_patch.status_code == 200
    assert safe_patch.json()["max_stack"] == 40

    # 7. Raising max_stack to 100 (succeeds)
    raise_patch = await client.patch(
        f"/api/v1/admin/items/{item_id}",
        headers=admin_auth["headers"],
        json={"max_stack": 100}
    )
    assert raise_patch.status_code == 200
    assert raise_patch.json()["max_stack"] == 100

    # 8. Updating unrelated catalog fields without changing max_stack
    unrelated_patch = await client.patch(
        f"/api/v1/admin/items/{item_id}",
        headers=admin_auth["headers"],
        json={"name": "Tactical Field Medic Kit", "description": "Enhanced trauma kit"}
    )
    assert unrelated_patch.status_code == 200
    assert unrelated_patch.json()["name"] == "Tactical Field Medic Kit"
    assert unrelated_patch.json()["description"] == "Enhanced trauma kit"
    assert unrelated_patch.json()["max_stack"] == 100

