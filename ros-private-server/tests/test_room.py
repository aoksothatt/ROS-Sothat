import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_room_management(client: AsyncClient, auth_headers_with_character: dict):
    # Ensure in lobby
    await client.post("/api/v1/lobby/enter", headers=auth_headers_with_character)

    # 1. Create a password-protected room
    create_res = await client.post(
        "/api/v1/room/create",
        headers=auth_headers_with_character,
        json={
            "name": "Delta Base Alpha",
            "map_id": 1,
            "capacity": 2,
            "team_mode": 2,
            "is_public": True,
            "password": "secret_room_pass"
        }
    )
    assert create_res.status_code == 201
    room = create_res.json()
    room_id = room["room_id"]
    assert room["name"] == "Delta Base Alpha"
    assert room["has_password"] is True
    assert room["current_players"] == 1
    assert room["status"] == "waiting"

    # 2. List rooms
    list_res = await client.get("/api/v1/room/list")
    assert list_res.status_code == 200
    rooms = list_res.json()["rooms"]
    assert any(r["room_id"] == room_id for r in rooms)

    # 3. Create Player 2 and join room
    await client.post("/api/v1/account/register", json={"username": "recruit_p2", "password": "Password123!"})
    login_p2 = await client.post("/api/v1/account/login", json={"username": "recruit_p2", "password": "Password123!"})
    h2 = {"Authorization": f"Bearer {login_p2.json()['access_token']}"}
    await client.post("/api/v1/player/character", headers=h2, json={"nickname": "BravoTwo", "char_type": 1})
    await client.post("/api/v1/lobby/enter", headers=h2)

    # Failed join: Wrong password
    bad_join = await client.post(f"/api/v1/room/{room_id}/join", headers=h2, json={"password": "wrong"})
    assert bad_join.status_code == 403

    # Success join: Correct password
    join_res = await client.post(f"/api/v1/room/{room_id}/join", headers=h2, json={"password": "secret_room_pass"})
    assert join_res.status_code == 200
    assert join_res.json()["current_players"] == 2

    # 4. Attempt to start before player 2 is ready should fail
    fail_start = await client.post(f"/api/v1/room/{room_id}/start", headers=auth_headers_with_character)
    assert fail_start.status_code == 400

    # 5. Player 2 toggles ready
    ready_res = await client.post(f"/api/v1/room/{room_id}/ready?is_ready=true", headers=h2)
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"

    # 6. Non-host cannot start match
    non_host_start = await client.post(f"/api/v1/room/{room_id}/start", headers=h2)
    assert non_host_start.status_code == 403

    # 7. Host starts match
    start_res = await client.post(f"/api/v1/room/{room_id}/start", headers=auth_headers_with_character)
    assert start_res.status_code == 200
    start_data = start_res.json()
    assert start_data["status"] == "playing"
    assert "match_token" in start_data
    assert start_data["battle_server_ip"] == "127.0.0.1"
    assert start_data["player_count"] == 2

    # 8. Both leave
    await client.post(f"/api/v1/room/{room_id}/leave", headers=h2)
    await client.post(f"/api/v1/room/{room_id}/leave", headers=auth_headers_with_character)

    # Room is closed when empty
    after_leave = await client.get(f"/api/v1/room/{room_id}")
    assert after_leave.status_code == 404
