import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.account.models import Account
from app.account.service import AccountService
from app.database.session import get_db

@pytest.fixture
async def regular_player_token(client: AsyncClient) -> str:
    res = await client.post("/api/v1/account/register", json={
        "username": "ordinary_player",
        "password": "PlayerPassword123!"
    })
    assert res.status_code == 201
    
    login_res = await client.post("/api/v1/account/login", json={
        "username": "ordinary_player",
        "password": "PlayerPassword123!"
    })
    assert login_res.status_code == 200
    return login_res.json()["access_token"]

@pytest.fixture
async def admin_token(client: AsyncClient, db_session: AsyncSession) -> str:
    # 1. Register account
    res = await client.post("/api/v1/account/register", json={
        "username": "system_admin",
        "password": "AdminPassword123!"
    })
    assert res.status_code == 201
    admin_id = res.json()["id"]

    # 2. Promote to admin directly in trusted database
    stmt = update(Account).where(Account.id == admin_id).values(role="admin")
    await db_session.execute(stmt)
    await db_session.commit()

    # 3. Login to get token
    login_res = await client.post("/api/v1/account/login", json={
        "username": "system_admin",
        "password": "AdminPassword123!"
    })
    assert login_res.status_code == 200
    return login_res.json()["access_token"]

@pytest.mark.asyncio
async def test_unauthenticated_access_rejected(client: AsyncClient):
    """Requests without Authorization header must be rejected with 401."""
    res = await client.get("/api/v1/admin/me")
    assert res.status_code == 401
    assert "detail" in res.json()
    assert "WWW-Authenticate" in res.headers

@pytest.mark.asyncio
async def test_invalid_bearer_token_rejected(client: AsyncClient):
    """Malformed or invalid tokens must be rejected with 401."""
    res = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": "Bearer invalid.token.garbage"}
    )
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_expired_token_rejected(client: AsyncClient):
    """Tokens with exp in the past must be rejected with 401."""
    # Craft an expired token (exp = 1000)
    import json, base64, hmac, hashlib
    from app.config import settings

    payload = {"sub": 1, "username": "admin", "exp": 1000}
    raw = json.dumps(payload, separators=(',', ':')).encode("utf-8")
    b64_p = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    sig = hmac.new(settings.SECRET_KEY.encode(), b64_p.encode(), hashlib.sha256).digest()
    b64_s = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    expired_token = f"{b64_p}.{b64_s}"

    res = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_player_attempting_admin_access_rejected(client: AsyncClient, regular_player_token: str):
    """Ordinary player accounts must be rejected with 403 Forbidden."""
    res = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "Admin privileges required."

    # Test other admin endpoints with player token
    stats_res = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert stats_res.status_code == 403

    list_res = await client.get(
        "/api/v1/admin/accounts",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert list_res.status_code == 403

@pytest.mark.asyncio
async def test_admin_accessing_protected_routes(client: AsyncClient, admin_token: str):
    """Admin users must successfully access protected admin endpoints."""
    res = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "system_admin"
    assert data["role"] == "admin"
    assert data["is_banned"] is False

    # Stats route
    stats_res = await client.get(
        "/api/v1/admin/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "active_lobby_presences" in stats_data
    assert "active_rooms" in stats_data
    assert "queued_matchmaking_tickets" in stats_data

    # Accounts list
    acc_res = await client.get(
        "/api/v1/admin/accounts",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert acc_res.status_code == 200
    accounts = acc_res.json()
    assert len(accounts) >= 1
    assert any(a["username"] == "system_admin" and a["role"] == "admin" for a in accounts)

@pytest.mark.asyncio
async def test_registration_cannot_create_admin(client: AsyncClient):
    """Passing role in registration must be rejected by schema validation (extra forbidden)."""
    # Attempting to supply role="admin" during registration
    res = await client.post("/api/v1/account/register", json={
        "username": "wannabe_admin",
        "password": "Password123!",
        "role": "admin"
    })
    # extra="forbid" rejects extra fields with 422
    assert res.status_code == 422

    # Normal registration must always default to 'player'
    clean_res = await client.post("/api/v1/account/register", json={
        "username": "wannabe_admin",
        "password": "Password123!"
    })
    assert clean_res.status_code == 201
    account_data = clean_res.json()
    assert account_data["role"] == "player"

@pytest.mark.asyncio
async def test_player_apis_cannot_change_own_role(client: AsyncClient, regular_player_token: str):
    """Public /me and /player APIs must not allow role escalation."""
    # /me is a GET endpoint; ensure PATCH / PUT are not accepted
    patch_me = await client.patch(
        "/api/v1/account/me",
        headers={"Authorization": f"Bearer {regular_player_token}"},
        json={"role": "admin"}
    )
    assert patch_me.status_code in (404, 405)

    # Player settings cannot escalate account role
    # Create character first
    await client.post(
        "/api/v1/player/character",
        headers={"Authorization": f"Bearer {regular_player_token}"},
        json={"nickname": "TestPlayerChar", "char_type": 0}
    )
    settings_res = await client.put(
        "/api/v1/player/character/settings",
        headers={"Authorization": f"Bearer {regular_player_token}"},
        json={"settings": {"role": "admin", "fov": 90}}
    )
    assert settings_res.status_code == 200

    # Verify Account role remains "player"
    me_res = await client.get(
        "/api/v1/account/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "player"

@pytest.mark.asyncio
async def test_server_side_role_verification_dynamically_enforced(
    client: AsyncClient,
    regular_player_token: str,
    db_session: AsyncSession
):
    """
    Role check must query fresh database state.
    Promoting player in DB instantly grants admin access without needing a new token.
    Demoting in DB instantly revokes access.
    """
    # 1. Player token rejected
    r1 = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert r1.status_code == 403

    # 2. Promote in DB
    stmt = update(Account).where(Account.username == "ordinary_player").values(role="admin")
    await db_session.execute(stmt)
    await db_session.commit()

    # 3. Same token now accepted
    r2 = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert r2.status_code == 200
    assert r2.json()["role"] == "admin"

    # 4. Demote back in DB
    stmt2 = update(Account).where(Account.username == "ordinary_player").values(role="player")
    await db_session.execute(stmt2)
    await db_session.commit()

    # 5. Same token now rejected again
    r3 = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert r3.status_code == 403

@pytest.mark.asyncio
async def test_admin_can_promote_and_demote_accounts(
    client: AsyncClient,
    admin_token: str,
    regular_player_token: str
):
    """Admin can promote another player to admin and demote them back."""
    # Get regular player account id
    p_me = await client.get(
        "/api/v1/account/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    target_id = p_me.json()["id"]

    # Admin promotes target
    promote_res = await client.post(
        f"/api/v1/admin/accounts/{target_id}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "admin"}
    )
    assert promote_res.status_code == 200
    assert promote_res.json()["role"] == "admin"

    # Promoted user can now access admin endpoint
    target_admin_check = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert target_admin_check.status_code == 200

    # Admin demotes target back to player
    demote_res = await client.post(
        f"/api/v1/admin/accounts/{target_id}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "player"}
    )
    assert demote_res.status_code == 200
    assert demote_res.json()["role"] == "player"

    # Target now forbidden again
    target_forbidden_check = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert target_forbidden_check.status_code == 403

@pytest.mark.asyncio
async def test_admin_self_protection_guards(client: AsyncClient, admin_token: str):
    """Admin cannot demote or ban themselves."""
    admin_me = await client.get(
        "/api/v1/admin/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    admin_id = admin_me.json()["id"]

    # Attempt self-demotion
    demote_res = await client.post(
        f"/api/v1/admin/accounts/{admin_id}/role",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role": "player"}
    )
    assert demote_res.status_code == 400
    assert "Cannot revoke your own admin privileges" in demote_res.json()["detail"]

    # Attempt self-ban
    ban_res = await client.post(
        f"/api/v1/admin/accounts/{admin_id}/ban",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_banned": True, "ban_reason": "Testing self ban"}
    )
    assert ban_res.status_code == 400
    assert "Cannot ban your own admin account" in ban_res.json()["detail"]

@pytest.mark.asyncio
async def test_admin_moderation_ban_and_unban(
    client: AsyncClient,
    admin_token: str,
    regular_player_token: str
):
    """Admin can ban a player, locking them out of authentication and APIs."""
    p_me = await client.get(
        "/api/v1/account/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    target_id = p_me.json()["id"]

    # Admin bans target
    ban_res = await client.post(
        f"/api/v1/admin/accounts/{target_id}/ban",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_banned": True, "ban_reason": "Rule violation"}
    )
    assert ban_res.status_code == 200
    assert ban_res.json()["is_banned"] is True

    # Target player token is now rejected with 403
    p_check = await client.get(
        "/api/v1/account/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert p_check.status_code == 403
    assert "banned" in p_check.json()["detail"].lower()

    # Admin unbans target
    unban_res = await client.post(
        f"/api/v1/admin/accounts/{target_id}/ban",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_banned": False}
    )
    assert unban_res.status_code == 200
    assert unban_res.json()["is_banned"] is False

    # Target player token is now active again
    p_check2 = await client.get(
        "/api/v1/account/me",
        headers={"Authorization": f"Bearer {regular_player_token}"}
    )
    assert p_check2.status_code == 200
