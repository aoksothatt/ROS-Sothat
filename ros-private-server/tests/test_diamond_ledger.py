import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select

from app.account.models import Account
from app.player.models import Character
from app.economy.models import DiamondTransaction

@pytest.fixture
async def admin_auth(client: AsyncClient, db_session: AsyncSession) -> dict:
    # 1. Register admin account
    res = await client.post("/api/v1/account/register", json={
        "username": "economy_admin",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 201
    admin_id = res.json()["id"]

    # 2. Promote to admin directly in trusted database
    stmt = update(Account).where(Account.id == admin_id).values(role="admin")
    await db_session.execute(stmt)
    await db_session.commit()

    # 3. Login to retrieve bearer token
    login_res = await client.post("/api/v1/account/login", json={
        "username": "economy_admin",
        "password": "AdminPassword123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "admin_id": admin_id
    }

@pytest.fixture
async def player_auth(client: AsyncClient) -> dict:
    res = await client.post("/api/v1/account/register", json={
        "username": "economy_player",
        "password": "PlayerPassword123!"
    })
    assert res.status_code == 201
    player_id = res.json()["id"]

    login_res = await client.post("/api/v1/account/login", json={
        "username": "economy_player",
        "password": "PlayerPassword123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "account_id": player_id
    }

@pytest.fixture
async def player_character(client: AsyncClient, player_auth: dict) -> dict:
    res = await client.post(
        "/api/v1/player/character",
        headers=player_auth["headers"],
        json={"nickname": "LedgerTester", "char_type": 0}
    )
    assert res.status_code == 201
    return res.json()

@pytest.mark.asyncio
async def test_admin_grant_diamonds_success(
    client: AsyncClient,
    admin_auth: dict,
    player_auth: dict,
    player_character: dict
):
    """Admin successfully grants diamonds, updating balance and appending to ledger."""
    gid = player_character["gid"]
    assert player_character["diamonds"] == 100 # Initial starting diamonds

    grant_payload = {
        "amount": 500,
        "idempotency_key": "grant-test-001",
        "reason": "Event reward distribution"
    }

    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json=grant_payload
    )
    assert res.status_code == 200
    data = res.json()
    assert data["character_gid"] == gid
    assert data["admin_account_id"] == admin_auth["admin_id"]
    assert data["operation_type"] == "GRANT"
    assert data["amount"] == 500
    assert data["balance_before"] == 100
    assert data["balance_after"] == 600
    assert data["idempotency_key"] == "grant-test-001"
    assert data["reason"] == "Event reward distribution"
    assert "id" in data
    assert "created_at" in data

    # Verify character profile shows updated balance
    char_res = await client.get(
        "/api/v1/player/character",
        headers=player_auth["headers"]
    )
    assert char_res.status_code == 200
    assert char_res.json()["diamonds"] == 600

@pytest.mark.asyncio
async def test_admin_deduct_diamonds_success(
    client: AsyncClient,
    admin_auth: dict,
    player_auth: dict,
    player_character: dict
):
    """Admin successfully deducts diamonds within available balance."""
    gid = player_character["gid"]
    assert player_character["diamonds"] == 100

    deduct_payload = {
        "amount": 45,
        "idempotency_key": "deduct-test-001",
        "reason": "Administrative fee adjustment"
    }

    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/deduct",
        headers=admin_auth["headers"],
        json=deduct_payload
    )
    assert res.status_code == 200
    data = res.json()
    assert data["character_gid"] == gid
    assert data["admin_account_id"] == admin_auth["admin_id"]
    assert data["operation_type"] == "DEDUCT"
    assert data["amount"] == 45
    assert data["balance_before"] == 100
    assert data["balance_after"] == 55
    assert data["idempotency_key"] == "deduct-test-001"

    # Verify updated profile balance
    char_res = await client.get(
        "/api/v1/player/character",
        headers=player_auth["headers"]
    )
    assert char_res.status_code == 200
    assert char_res.json()["diamonds"] == 55

@pytest.mark.asyncio
async def test_deduct_exact_balance_to_zero(
    client: AsyncClient,
    admin_auth: dict,
    player_auth: dict,
    player_character: dict
):
    """Deducting exact current balance succeeds and leaves character with 0 diamonds."""
    gid = player_character["gid"]

    deduct_payload = {
        "amount": 100,
        "idempotency_key": "deduct-zero-001",
        "reason": "Full balance reset"
    }

    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/deduct",
        headers=admin_auth["headers"],
        json=deduct_payload
    )
    assert res.status_code == 200
    assert res.json()["balance_after"] == 0

    char_res = await client.get("/api/v1/player/character", headers=player_auth["headers"])
    assert char_res.json()["diamonds"] == 0

@pytest.mark.asyncio
async def test_deduct_insufficient_balance_rejected(
    client: AsyncClient,
    admin_auth: dict,
    player_auth: dict,
    player_character: dict
):
    """Deducting more than current balance fails with HTTP 400 and preserves balance."""
    gid = player_character["gid"]

    deduct_payload = {
        "amount": 101, # 1 more than 100
        "idempotency_key": "deduct-overdraft-001",
        "reason": "Attempted overdraft"
    }

    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/deduct",
        headers=admin_auth["headers"],
        json=deduct_payload
    )
    assert res.status_code == 400
    assert "Insufficient diamond balance" in res.json()["detail"]

    # Verify character balance is completely unchanged
    char_res = await client.get("/api/v1/player/character", headers=player_auth["headers"])
    assert char_res.json()["diamonds"] == 100

@pytest.mark.asyncio
async def test_idempotency_exact_replay(
    client: AsyncClient,
    admin_auth: dict,
    player_auth: dict,
    player_character: dict
):
    """Repeating a transaction with identical parameters returns existing record without double-granting."""
    gid = player_character["gid"]

    payload = {
        "amount": 250,
        "idempotency_key": "idemp-grant-replay-001",
        "reason": "Seasonal reward"
    }

    # First request
    res1 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json=payload
    )
    assert res1.status_code == 200
    tx1 = res1.json()
    assert tx1["balance_after"] == 350

    # Second identical request (replay)
    res2 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json=payload
    )
    assert res2.status_code == 200
    tx2 = res2.json()

    # Must return exact same transaction ID and values
    assert tx2["id"] == tx1["id"]
    assert tx2["balance_after"] == 350

    # Ensure player balance was NOT incremented again
    char_res = await client.get("/api/v1/player/character", headers=player_auth["headers"])
    assert char_res.json()["diamonds"] == 350

@pytest.mark.asyncio
async def test_idempotency_conflict_on_mismatched_amount(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict
):
    """Reusing idempotency key with a different amount triggers HTTP 409 Conflict."""
    gid = player_character["gid"]

    res1 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100, "idempotency_key": "conflict-key-001", "reason": "First"}
    )
    assert res1.status_code == 200

    # Attempt reuse with amount 200
    res2 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 200, "idempotency_key": "conflict-key-001", "reason": "Second"}
    )
    assert res2.status_code == 409
    assert "Idempotency key" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_idempotency_conflict_on_mismatched_operation_type(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict
):
    """Reusing idempotency key across different operation types triggers HTTP 409 Conflict."""
    gid = player_character["gid"]

    res1 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 50, "idempotency_key": "conflict-key-op-001", "reason": "Grant"}
    )
    assert res1.status_code == 200

    # Attempt reuse with deduct operation
    res2 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/deduct",
        headers=admin_auth["headers"],
        json={"amount": 50, "idempotency_key": "conflict-key-op-001", "reason": "Deduct"}
    )
    assert res2.status_code == 409
    assert "Idempotency key" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_idempotency_conflict_on_different_character(
    client: AsyncClient,
    admin_auth: dict,
    player_auth: dict,
    player_character: dict
):
    """Reusing idempotency key on a different character triggers HTTP 409 Conflict."""
    # Register second player and character
    res = await client.post("/api/v1/account/register", json={
        "username": "second_player",
        "password": "PlayerPassword123!"
    })
    assert res.status_code == 201
    login_res = await client.post("/api/v1/account/login", json={
        "username": "second_player",
        "password": "PlayerPassword123!"
    })
    token2 = login_res.json()["access_token"]
    char2_res = await client.post(
        "/api/v1/player/character",
        headers={"Authorization": f"Bearer {token2}"},
        json={"nickname": "SecondChar", "char_type": 1}
    )
    gid2 = char2_res.json()["gid"]

    # First grant on character 1
    res1 = await client.post(
        f"/api/v1/admin/characters/{player_character['gid']}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 75, "idempotency_key": "conflict-key-char-001", "reason": "P1"}
    )
    assert res1.status_code == 200

    # Attempt reuse on character 2
    res2 = await client.post(
        f"/api/v1/admin/characters/{gid2}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 75, "idempotency_key": "conflict-key-char-001", "reason": "P2"}
    )
    assert res2.status_code == 409
    assert "Idempotency key" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_amount_validation_rules(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict
):
    """Validation rejects non-positive, zero, or excessively large amounts."""
    gid = player_character["gid"]

    # Zero amount
    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 0, "idempotency_key": "v-zero", "reason": "Zero"}
    )
    assert res.status_code == 422

    # Negative amount
    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": -50, "idempotency_key": "v-neg", "reason": "Neg"}
    )
    assert res.status_code == 422

    # Excessive amount (> 100,000,000)
    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100_000_001, "idempotency_key": "v-excess", "reason": "Excess"}
    )
    assert res.status_code == 422

    # Empty idempotency key
    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100, "idempotency_key": "", "reason": "Empty key"}
    )
    assert res.status_code == 422

    # Whitespace-only idempotency key
    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100, "idempotency_key": "    ", "reason": "Valid reason"}
    )
    assert res.status_code == 422

    # Whitespace-only reason
    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100, "idempotency_key": "v-ws-01", "reason": "   "}
    )
    assert res.status_code == 422

    # Verify trimmed fields
    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 50, "idempotency_key": "  v-trimmed-01  ", "reason": "  Trimmed reason  "}
    )
    assert res.status_code == 200
    assert res.json()["idempotency_key"] == "v-trimmed-01"
    assert res.json()["reason"] == "Trimmed reason"

@pytest.mark.asyncio
async def test_character_not_found_handling(client: AsyncClient, admin_auth: dict):
    """Operations on non-existent character GID return HTTP 404."""
    non_existent_gid = 999999

    grant_res = await client.post(
        f"/api/v1/admin/characters/{non_existent_gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100, "idempotency_key": "nf-grant-01", "reason": "Test"}
    )
    assert grant_res.status_code == 404

    deduct_res = await client.post(
        f"/api/v1/admin/characters/{non_existent_gid}/diamonds/deduct",
        headers=admin_auth["headers"],
        json={"amount": 50, "idempotency_key": "nf-deduct-01", "reason": "Test"}
    )
    assert deduct_res.status_code == 404

    history_res = await client.get(
        f"/api/v1/admin/characters/{non_existent_gid}/diamonds/history",
        headers=admin_auth["headers"]
    )
    assert history_res.status_code == 404

@pytest.mark.asyncio
async def test_rbac_authorization_enforced(
    client: AsyncClient,
    player_auth: dict,
    player_character: dict
):
    """Unauthenticated users receive 401; non-admin players receive 403."""
    gid = player_character["gid"]

    # 1. Unauthenticated requests -> 401
    res_unauth = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        json={"amount": 100, "idempotency_key": "unauth-01", "reason": "Test"}
    )
    assert res_unauth.status_code == 401

    res_history_unauth = await client.get(f"/api/v1/admin/characters/{gid}/diamonds/history")
    assert res_history_unauth.status_code == 401

    # 2. Player attempting admin grant -> 403
    res_player_grant = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=player_auth["headers"],
        json={"amount": 100, "idempotency_key": "player-cheat-01", "reason": "Test"}
    )
    assert res_player_grant.status_code == 403

    # 3. Player attempting admin deduct -> 403
    res_player_deduct = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/deduct",
        headers=player_auth["headers"],
        json={"amount": 50, "idempotency_key": "player-cheat-02", "reason": "Test"}
    )
    assert res_player_deduct.status_code == 403

    # 4. Player attempting admin history -> 403
    res_player_hist = await client.get(
        f"/api/v1/admin/characters/{gid}/diamonds/history",
        headers=player_auth["headers"]
    )
    assert res_player_hist.status_code == 403

@pytest.mark.asyncio
async def test_banned_admin_rejected(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict,
    db_session: AsyncSession
):
    """Banned admin account is rejected with HTTP 403."""
    gid = player_character["gid"]

    # Ban the admin account in database
    stmt = update(Account).where(Account.id == admin_auth["admin_id"]).values(is_banned=True, ban_reason="Compromised")
    await db_session.execute(stmt)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100, "idempotency_key": "banned-admin-01", "reason": "Test"}
    )
    assert res.status_code == 403
    assert "banned" in res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_diamond_history_ordering_and_pagination(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict
):
    """History endpoint correctly orders newest transactions first and paginates results."""
    gid = player_character["gid"]

    # Initial balance: 100
    # Step 1: Grant 50 -> balance 150
    res1 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 50, "idempotency_key": "hist-01", "reason": "First grant"}
    )
    assert res1.status_code == 200

    # Step 2: Deduct 20 -> balance 130
    res2 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/deduct",
        headers=admin_auth["headers"],
        json={"amount": 20, "idempotency_key": "hist-02", "reason": "Second deduct"}
    )
    assert res2.status_code == 200

    # Step 3: Grant 100 -> balance 230
    res3 = await client.post(
        f"/api/v1/admin/characters/{gid}/diamonds/grant",
        headers=admin_auth["headers"],
        json={"amount": 100, "idempotency_key": "hist-03", "reason": "Third grant"}
    )
    assert res3.status_code == 200

    # Query full history
    res_all = await client.get(
        f"/api/v1/admin/characters/{gid}/diamonds/history",
        headers=admin_auth["headers"]
    )
    assert res_all.status_code == 200
    data = res_all.json()
    assert data["character_gid"] == gid
    assert data["current_balance"] == 230
    assert data["total_transactions"] == 3
    txs = data["transactions"]
    assert len(txs) == 3

    # Check newest-first ordering
    assert txs[0]["operation_type"] == "GRANT"
    assert txs[0]["amount"] == 100
    assert txs[0]["balance_after"] == 230

    assert txs[1]["operation_type"] == "DEDUCT"
    assert txs[1]["amount"] == 20
    assert txs[1]["balance_after"] == 130

    assert txs[2]["operation_type"] == "GRANT"
    assert txs[2]["amount"] == 50
    assert txs[2]["balance_after"] == 150

    # Pagination: limit=2, offset=0
    res_page1 = await client.get(
        f"/api/v1/admin/characters/{gid}/diamonds/history?limit=2&offset=0",
        headers=admin_auth["headers"]
    )
    assert res_page1.status_code == 200
    p1_data = res_page1.json()
    assert len(p1_data["transactions"]) == 2
    assert p1_data["transactions"][0]["amount"] == 100
    assert p1_data["transactions"][1]["amount"] == 20

    # Pagination: limit=2, offset=2
    res_page2 = await client.get(
        f"/api/v1/admin/characters/{gid}/diamonds/history?limit=2&offset=2",
        headers=admin_auth["headers"]
    )
    assert res_page2.status_code == 200
    p2_data = res_page2.json()
    assert len(p2_data["transactions"]) == 1
    assert p2_data["transactions"][0]["amount"] == 50

@pytest.mark.asyncio
async def test_ledger_sum_matches_character_balance(
    client: AsyncClient,
    admin_auth: dict,
    player_character: dict,
    db_session: AsyncSession
):
    """Verify that ledger transaction history mathematically reconciles to character balance."""
    gid = player_character["gid"]
    initial_balance = player_character["diamonds"] # 100

    # Execute varied grants and deductions
    ops = [
        ("grant", 150),
        ("grant", 300),
        ("deduct", 75),
        ("grant", 50),
        ("deduct", 125)
    ]

    for idx, (op, amt) in enumerate(ops):
        res = await client.post(
            f"/api/v1/admin/characters/{gid}/diamonds/{op}",
            headers=admin_auth["headers"],
            json={"amount": amt, "idempotency_key": f"reconcile-{idx}", "reason": f"Op {idx}"}
        )
        assert res.status_code == 200

    # Query database ledger directly
    stmt = select(DiamondTransaction).where(DiamondTransaction.character_gid == gid)
    res_txs = await db_session.execute(stmt)
    txs = list(res_txs.scalars().all())
    assert len(txs) == len(ops)

    net_change = sum(t.amount if t.operation_type == "GRANT" else -t.amount for t in txs)
    expected_balance = initial_balance + net_change

    char_stmt = select(Character).where(Character.gid == gid)
    res_char = await db_session.execute(char_stmt)
    char = res_char.scalars().first()
    assert char.diamonds == expected_balance
    assert char.diamonds == (100 + 150 + 300 - 75 + 50 - 125) # 400

@pytest.mark.asyncio
async def test_database_check_constraint_rejects_negative_character_diamonds(
    db_session: AsyncSession,
    player_auth: dict
):
    """Ensure database-level check constraint rejects negative diamond values."""
    from sqlalchemy.exc import IntegrityError

    invalid_char = Character(
        account_id=player_auth["account_id"],
        nickname="NegativeTester",
        char_type=0,
        diamonds=-50 # Violates chk_character_diamonds_non_negative
    )
    db_session.add(invalid_char)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_database_check_constraint_rejects_non_positive_transaction_amount(
    db_session: AsyncSession,
    admin_auth: dict,
    player_character: dict
):
    """Ensure database-level check constraint rejects non-positive transaction amounts."""
    from sqlalchemy.exc import IntegrityError

    invalid_tx = DiamondTransaction(
        character_gid=player_character["gid"],
        admin_account_id=admin_auth["admin_id"],
        operation_type="GRANT",
        amount=0, # Violates chk_diamond_tx_amount_positive
        balance_before=100,
        balance_after=100,
        idempotency_key="chk-tx-zero",
        reason="Invalid zero amount"
    )
    db_session.add(invalid_tx)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
