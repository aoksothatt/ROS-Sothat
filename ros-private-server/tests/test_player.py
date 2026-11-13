import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_character_creation_and_profile(client: AsyncClient, auth_headers: dict):
    # Verify no character initially
    me_before = await client.get("/api/v1/account/me", headers=auth_headers)
    assert me_before.json()["has_character"] is False

    # Attempt to fetch non-existent character
    get_none = await client.get("/api/v1/player/character", headers=auth_headers)
    assert get_none.status_code == 404

    # Create character with invalid nickname
    bad_nick = await client.post(
        "/api/v1/player/character",
        headers=auth_headers,
        json={"nickname": "a", "char_type": 0} # too short
    )
    assert bad_nick.status_code == 422

    # Successfully create character
    create_res = await client.post(
        "/api/v1/player/character",
        headers=auth_headers,
        json={"nickname": "ShadowAgent", "char_type": 1}
    )
    assert create_res.status_code == 201
    char_data = create_res.json()
    assert char_data["nickname"] == "ShadowAgent"
    assert char_data["char_type"] == 1
    assert char_data["level"] == 1
    assert char_data["gold"] == 1000
    assert "appearances" in char_data
    assert "settings" in char_data
    gid = char_data["gid"]

    # Prevent creating second character on same account
    dup_char = await client.post(
        "/api/v1/player/character",
        headers=auth_headers,
        json={"nickname": "ShadowAgent2", "char_type": 0}
    )
    assert dup_char.status_code == 409

    # Retrieve current character
    my_char = await client.get("/api/v1/player/character", headers=auth_headers)
    assert my_char.status_code == 200
    assert my_char.json()["gid"] == gid

    # Retrieve public profile by GID
    pub_profile = await client.get(f"/api/v1/player/{gid}")
    assert pub_profile.status_code == 200
    pub_data = pub_profile.json()
    assert pub_data["nickname"] == "ShadowAgent"
    assert pub_data["level"] == 1

@pytest.mark.asyncio
async def test_duplicate_nickname_across_accounts(client: AsyncClient):
    # User 1
    await client.post("/api/v1/account/register", json={"username": "user_one", "password": "Password123!"})
    login_1 = await client.post("/api/v1/account/login", json={"username": "user_one", "password": "Password123!"})
    h1 = {"Authorization": f"Bearer {login_1.json()['access_token']}"}
    await client.post("/api/v1/player/character", headers=h1, json={"nickname": "ViperSquad", "char_type": 0})

    # User 2 tries to use same nickname
    await client.post("/api/v1/account/register", json={"username": "user_two", "password": "Password123!"})
    login_2 = await client.post("/api/v1/account/login", json={"username": "user_two", "password": "Password123!"})
    h2 = {"Authorization": f"Bearer {login_2.json()['access_token']}"}
    dup_res = await client.post("/api/v1/player/character", headers=h2, json={"nickname": "ViperSquad", "char_type": 1})
    assert dup_res.status_code == 409

@pytest.mark.asyncio
async def test_update_settings_and_appearances(client: AsyncClient, auth_headers_with_character: dict):
    # Update settings
    new_settings = {"fov": 90, "gyroscope": True, "custom_key": "custom_val"}
    up_res = await client.put(
        "/api/v1/player/character/settings",
        headers=auth_headers_with_character,
        json={"settings": new_settings}
    )
    assert up_res.status_code == 200
    assert up_res.json()["settings"]["fov"] == 90
    assert up_res.json()["settings"]["gyroscope"] is True

    # Update appearances
    new_appearances = {"equipped_clothing": [20001, 20002], "active_weapon_skin": 5001}
    app_res = await client.put(
        "/api/v1/player/character/appearances",
        headers=auth_headers_with_character,
        json={"appearances": new_appearances}
    )
    assert app_res.status_code == 200
    assert app_res.json()["appearances"]["active_weapon_skin"] == 5001
