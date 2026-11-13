import asyncio
import os
import time
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient

from app.config import settings
from app.main import validate_single_worker_configuration, perform_system_cleanup
from app.lobby.service import LobbyService
from app.room.service import RoomService
from app.matchmaking.service import MatchmakingService
from app.matchmaking.schemas import MatchTicketStatus
from app.room.models import RoomStatus
from app.account.rate_limiter import InMemoryRateLimiter

# 1. Guest registration followed by login using the same device ID
@pytest.mark.asyncio
async def test_guest_registration_and_returning_login(client: AsyncClient):
    device_id = "device_apple_1001"

    # First registration
    r1 = await client.post("/api/v1/account/guest", json={"device_id": device_id})
    assert r1.status_code == 201
    d1 = r1.json()
    account_id = d1["account_id"]
    username = d1["username"]
    token1 = d1["access_token"]

    # Create character for guest
    char_res = await client.post(
        "/api/v1/player/character",
        headers={"Authorization": f"Bearer {token1}"},
        json={"nickname": "GuestHero01", "char_type": 0}
    )
    assert char_res.status_code == 201

    # Second login with SAME device_id
    r2 = await client.post("/api/v1/account/guest", json={"device_id": device_id})
    assert r2.status_code == 201
    d2 = r2.json()
    assert d2["account_id"] == account_id
    assert d2["username"] == username
    token2 = d2["access_token"]

    # Retrieve character using token2 - character must persist!
    char_get = await client.get("/api/v1/player/character", headers={"Authorization": f"Bearer {token2}"})
    assert char_get.status_code == 200
    assert char_get.json()["nickname"] == "GuestHero01"

# 2. Different device IDs creating different accounts
@pytest.mark.asyncio
async def test_different_device_ids_create_different_accounts(client: AsyncClient):
    r1 = await client.post("/api/v1/account/guest", json={"device_id": "device_ios_alpha"})
    r2 = await client.post("/api/v1/account/guest", json={"device_id": "device_ios_beta"})
    assert r1.status_code == 201
    assert r2.status_code == 201

    d1 = r1.json()
    d2 = r2.json()
    assert d1["account_id"] != d2["account_id"]
    assert d1["username"] != d2["username"]

# 3. Concurrent guest registration using the same device ID
@pytest.mark.asyncio
async def test_concurrent_guest_registration_same_device_id(client: AsyncClient):
    device_id = "device_concurrent_99"

    # Send 2 simultaneous registration requests with same device_id
    resp1, resp2 = await asyncio.gather(
        client.post("/api/v1/account/guest", json={"device_id": device_id}),
        client.post("/api/v1/account/guest", json={"device_id": device_id})
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    d1 = resp1.json()
    d2 = resp2.json()
    assert d1["account_id"] == d2["account_id"]
    assert d1["username"] == d2["username"]

# 4. Single-worker deployment safeguard
def test_single_worker_deployment_safeguard():
    # Normal execution: does not raise
    validate_single_worker_configuration(max_allowed=1)

    # Set multi-worker environment variable
    os.environ["WEB_CONCURRENCY"] = "4"
    try:
        with pytest.raises(RuntimeError) as exc_info:
            validate_single_worker_configuration(max_allowed=1)
        assert "Unsupported multi-worker configuration detected" in str(exc_info.value)
    finally:
        del os.environ["WEB_CONCURRENCY"]

# 5. Disconnected player cleanup from rooms
@pytest.mark.asyncio
async def test_disconnected_player_cleanup_from_rooms(client: AsyncClient, auth_headers_with_character: dict):
    # Enter lobby
    enter_res = await client.post("/api/v1/lobby/enter", headers=auth_headers_with_character)
    assert enter_res.status_code == 200
    gid = enter_res.json()["gid"]

    # Create room
    create_res = await client.post(
        "/api/v1/room/create",
        headers=auth_headers_with_character,
        json={"name": "RoomToTimeout", "capacity": 4, "team_mode": 4}
    )
    assert create_res.status_code == 201
    room_id = create_res.json()["room_id"]

    room_service = RoomService.get_instance()
    assert room_id in room_service._rooms

    # Simulate heartbeat timeout by setting last_heartbeat far in the past
    lobby_service = LobbyService.get_instance()
    lobby_service._presences[gid].last_heartbeat = time.time() - 120

    # Trigger cleanup
    stale = lobby_service.cleanup_stale_presences()
    assert gid in stale

    # Room was empty after host timed out, so room must be closed/deleted
    assert room_id not in room_service._rooms

# 6. Disconnected player cleanup from matchmaking
@pytest.mark.asyncio
async def test_disconnected_player_cleanup_from_matchmaking(client: AsyncClient, auth_headers_with_character: dict):
    # Enter lobby & queue
    await client.post("/api/v1/lobby/enter", headers=auth_headers_with_character)
    q_res = await client.post(
        "/api/v1/matchmaking/queue",
        headers=auth_headers_with_character,
        json={"match_mode": "solo", "region": "asia"}
    )
    assert q_res.status_code == 201
    ticket_id = q_res.json()["ticket_id"]
    gid = q_res.json()["gid"]

    mm_service = MatchmakingService.get_instance()
    assert ticket_id in mm_service._tickets
    assert gid in mm_service._player_tickets

    # Simulate heartbeat timeout
    lobby_service = LobbyService.get_instance()
    lobby_service._presences[gid].last_heartbeat = time.time() - 120

    # Trigger cleanup
    lobby_service.cleanup_stale_presences()

    # Ticket should be transitioned to TIMEOUT and player removed from queue
    assert gid not in mm_service._player_tickets
    assert mm_service._tickets[ticket_id].status == MatchTicketStatus.TIMEOUT

# 7. Expired ticket cleanup
@pytest.mark.asyncio
async def test_expired_ticket_cleanup(client: AsyncClient, auth_headers_with_character: dict):
    await client.post("/api/v1/lobby/enter", headers=auth_headers_with_character)
    q_res = await client.post(
        "/api/v1/matchmaking/queue",
        headers=auth_headers_with_character,
        json={"match_mode": "solo", "region": "asia"}
    )
    ticket_id = q_res.json()["ticket_id"]

    mm_service = MatchmakingService.get_instance()
    # Cancel ticket
    await client.post(f"/api/v1/matchmaking/cancel/{ticket_id}", headers=auth_headers_with_character)
    assert mm_service._tickets[ticket_id].status == MatchTicketStatus.CANCELLED

    # Artificially age the ticket beyond TTL (e.g. 400 seconds ago)
    mm_service._tickets[ticket_id].queued_at = datetime.utcnow() - timedelta(seconds=400)

    # Run ticket cleanup with TTL=300
    pruned = mm_service.cleanup_expired_tickets(ttl_seconds=300)
    assert pruned >= 1
    assert ticket_id not in mm_service._tickets

# 8. Expired room cleanup
def test_expired_room_cleanup():
    room_service = RoomService.get_instance()
    from app.room.models import Room, RoomStatus

    # Create dummy closed room
    room_service._rooms["room_closed_99"] = Room(
        room_id="room_closed_99",
        name="Old Room",
        host_gid=999,
        status=RoomStatus.CLOSED
    )

    pruned = room_service.cleanup_stale_rooms()
    assert pruned >= 1
    assert "room_closed_99" not in room_service._rooms

# 9. Active rooms and valid tickets surviving cleanup
@pytest.mark.asyncio
async def test_active_rooms_and_valid_tickets_surviving_cleanup(client: AsyncClient, auth_headers_with_character: dict):
    # Active lobby entry
    await client.post("/api/v1/lobby/enter", headers=auth_headers_with_character)

    # Active room
    room_res = await client.post(
        "/api/v1/room/create",
        headers=auth_headers_with_character,
        json={"name": "ActiveRoom", "capacity": 4, "team_mode": 4}
    )
    room_id = room_res.json()["room_id"]

    # Run system cleanup
    cleanup_result = perform_system_cleanup()

    # Room must survive!
    room_service = RoomService.get_instance()
    assert room_id in room_service._rooms
    assert room_service._rooms[room_id].status == RoomStatus.WAITING

# 10. Oversized and malformed appearance/settings payload rejection
@pytest.mark.asyncio
async def test_oversized_and_malformed_appearance_settings_payload_rejection(
    client: AsyncClient,
    auth_headers_with_character: dict
):
    # 1. Oversized settings (> 16 KB)
    huge_settings = {"key": "A" * 20000}
    r1 = await client.put(
        "/api/v1/player/character/settings",
        headers=auth_headers_with_character,
        json={"settings": huge_settings}
    )
    assert r1.status_code == 422

    # 2. Malformed settings: invalid key name
    r2 = await client.put(
        "/api/v1/player/character/settings",
        headers=auth_headers_with_character,
        json={"settings": {"invalid!key@name": 123}}
    )
    assert r2.status_code == 422

    # 3. Oversized appearances: list with > 50 elements
    r3 = await client.put(
        "/api/v1/player/character/appearances",
        headers=auth_headers_with_character,
        json={"appearances": {"equipped_clothing": list(range(100))}}
    )
    assert r3.status_code == 422

    # 4. Malformed appearances: negative integer
    r4 = await client.put(
        "/api/v1/player/character/appearances",
        headers=auth_headers_with_character,
        json={"appearances": {"active_weapon_skin": -5}}
    )
    assert r4.status_code == 422

# 11. Login rate limiting
@pytest.mark.asyncio
async def test_login_rate_limiting(client: AsyncClient):
    InMemoryRateLimiter.get_instance().reset()

    # Max allowed attempts is 5 per window (configured in settings)
    for i in range(settings.RATE_LIMIT_LOGIN_MAX_REQUESTS):
        res = await client.post("/api/v1/account/login", json={
            "username": f"user_attempt_{i}",
            "password": "WrongPassword!"
        })
        # Should return 401 Unauthorized for bad password
        assert res.status_code == 401

    # Next attempt should be rate limited with HTTP 429
    blocked = await client.post("/api/v1/account/login", json={
        "username": "user_attempt_extra",
        "password": "WrongPassword!"
    })
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers

# 12. Registration rate limiting
@pytest.mark.asyncio
async def test_registration_rate_limiting(client: AsyncClient):
    InMemoryRateLimiter.get_instance().reset()

    # Max allowed is 3 per window
    for i in range(settings.RATE_LIMIT_REGISTER_MAX_REQUESTS):
        res = await client.post("/api/v1/account/register", json={
            "username": f"reg_user_{i}",
            "password": "Password123!"
        })
        assert res.status_code == 201

    # 4th request must be rate limited with HTTP 429
    blocked = await client.post("/api/v1/account/register", json={
        "username": "reg_user_overflow",
        "password": "Password123!"
    })
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
