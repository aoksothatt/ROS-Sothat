import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert "version" in data

@pytest.mark.asyncio
async def test_account_register_and_login(client: AsyncClient):
    # Register
    reg_res = await client.post("/api/v1/account/register", json={
        "username": "sniper_elite",
        "password": "SecurePassword99!"
    })
    assert reg_res.status_code == 201
    account_data = reg_res.json()
    assert account_data["username"] == "sniper_elite"
    assert account_data["is_banned"] is False
    assert account_data["has_character"] is False

    # Duplicate registration should fail
    dup_res = await client.post("/api/v1/account/register", json={
        "username": "sniper_elite",
        "password": "AnotherPassword123!"
    })
    assert dup_res.status_code == 409

    # Successful login
    login_res = await client.post("/api/v1/account/login", json={
        "username": "sniper_elite",
        "password": "SecurePassword99!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["username"] == "sniper_elite"

    # Failed login with wrong password
    bad_login = await client.post("/api/v1/account/login", json={
        "username": "sniper_elite",
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

@pytest.mark.asyncio
async def test_guest_login(client: AsyncClient):
    res = await client.post("/api/v1/account/guest", json={
        "device_id": "test_device_uuid_123"
    })
    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["username"].startswith("guest_")

@pytest.mark.asyncio
async def test_authenticated_me_endpoint(client: AsyncClient, auth_headers: dict):
    res = await client.get("/api/v1/account/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["username"] == "test_operator"

    # Test without header
    unauth = await client.get("/api/v1/account/me")
    assert unauth.status_code == 401
