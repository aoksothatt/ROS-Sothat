import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_lobby_lifecycle(client: AsyncClient, auth_headers_with_character: dict):
    # Enter lobby
    enter_res = await client.post("/api/v1/lobby/enter", headers=auth_headers_with_character)
    assert enter_res.status_code == 200
    enter_data = enter_res.json()
    assert enter_data["nickname"] == "GhostRider"
    assert enter_data["status"] == "idle"

    # Verify visible in online listing
    online_res = await client.get("/api/v1/lobby/online")
    assert online_res.status_code == 200
    online_data = online_res.json()
    assert online_data["total_online"] >= 1
    nicknames = [p["nickname"] for p in online_data["players"]]
    assert "GhostRider" in nicknames

    # Send heartbeat
    hb_res = await client.post("/api/v1/lobby/heartbeat", headers=auth_headers_with_character)
    assert hb_res.status_code == 200
    assert hb_res.json()["acknowledged"] is True

    # Leave lobby
    leave_res = await client.post("/api/v1/lobby/leave", headers=auth_headers_with_character)
    assert leave_res.status_code == 200

    # Verify no longer in online listing
    online_after = await client.get("/api/v1/lobby/online")
    assert "GhostRider" not in [p["nickname"] for p in online_after.json()["players"]]

@pytest.mark.asyncio
async def test_lobby_entry_without_character(client: AsyncClient):
    # Register an account without character
    await client.post("/api/v1/account/register", json={"username": "no_char_user", "password": "Password123!"})
    login = await client.post("/api/v1/account/login", json={"username": "no_char_user", "password": "Password123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.post("/api/v1/lobby/enter", headers=headers)
    assert res.status_code == 400
