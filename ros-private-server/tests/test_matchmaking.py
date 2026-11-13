import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_matchmaking_queue_and_cancel(client: AsyncClient, auth_headers_with_character: dict):
    # Ensure in lobby
    await client.post("/api/v1/lobby/enter", headers=auth_headers_with_character)

    # 1. Enqueue
    queue_res = await client.post(
        "/api/v1/matchmaking/queue",
        headers=auth_headers_with_character,
        json={"match_mode": "squad", "region": "asia"}
    )
    assert queue_res.status_code == 201
    ticket = queue_res.json()
    ticket_id = ticket["ticket_id"]
    assert ticket["status"] == "queued"

    # 2. Check status
    status_res = await client.get(f"/api/v1/matchmaking/ticket/{ticket_id}", headers=auth_headers_with_character)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "queued"

    # 3. Cancel ticket
    cancel_res = await client.post(f"/api/v1/matchmaking/cancel/{ticket_id}", headers=auth_headers_with_character)
    assert cancel_res.status_code == 200

    # 4. Check status after cancel
    status_after = await client.get(f"/api/v1/matchmaking/ticket/{ticket_id}", headers=auth_headers_with_character)
    assert status_after.json()["status"] == "cancelled"

@pytest.mark.asyncio
async def test_matchmaking_pairing(client: AsyncClient):
    # Setup Player A
    await client.post("/api/v1/account/register", json={"username": "match_p1", "password": "Password123!"})
    l1 = await client.post("/api/v1/account/login", json={"username": "match_p1", "password": "Password123!"})
    h1 = {"Authorization": f"Bearer {l1.json()['access_token']}"}
    await client.post("/api/v1/player/character", headers=h1, json={"nickname": "StrikerA", "char_type": 0})
    await client.post("/api/v1/lobby/enter", headers=h1)

    # Setup Player B
    await client.post("/api/v1/account/register", json={"username": "match_p2", "password": "Password123!"})
    l2 = await client.post("/api/v1/account/login", json={"username": "match_p2", "password": "Password123!"})
    h2 = {"Authorization": f"Bearer {l2.json()['access_token']}"}
    await client.post("/api/v1/player/character", headers=h2, json={"nickname": "StrikerB", "char_type": 1})
    await client.post("/api/v1/lobby/enter", headers=h2)

    # 1. Player A queues for Solo in US region
    q1 = await client.post("/api/v1/matchmaking/queue", headers=h1, json={"match_mode": "solo", "region": "us"})
    t1_id = q1.json()["ticket_id"]

    # Ticket 1 should be queued (threshold is 2)
    s1_before = await client.get(f"/api/v1/matchmaking/ticket/{t1_id}", headers=h1)
    assert s1_before.json()["status"] == "queued"

    # 2. Player B queues for Solo in US region (triggers threshold >= 2)
    q2 = await client.post("/api/v1/matchmaking/queue", headers=h2, json={"match_mode": "solo", "region": "us"})
    t2_id = q2.json()["ticket_id"]

    # 3. Both tickets should now be MATCHED
    s1_after = await client.get(f"/api/v1/matchmaking/ticket/{t1_id}", headers=h1)
    assert s1_after.json()["status"] == "matched"
    assert "match_token" in s1_after.json()
    assert s1_after.json()["battle_server_ip"] == "127.0.0.1"
    assert "StrikerB" in s1_after.json()["assigned_players"]

    s2_after = await client.get(f"/api/v1/matchmaking/ticket/{t2_id}", headers=h2)
    assert s2_after.json()["status"] == "matched"
    assert s2_after.json()["match_id"] == s1_after.json()["match_id"]
