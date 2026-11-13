import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.account.service import AccountService
from app.account.models import Account
from app.player.models import Character
from app.inventory.models import Item, InventoryItem
from app.economy.models import DiamondTransaction

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_anonymous_cannot_access_player_dashboard_endpoints(client: AsyncClient):
    # GET /character
    res = await client.get("/api/v1/player/character")
    assert res.status_code == 401

    # GET /character/inventory
    res = await client.get("/api/v1/player/character/inventory")
    assert res.status_code == 401

    # GET /character/diamonds/history
    res = await client.get("/api/v1/player/character/diamonds/history")
    assert res.status_code == 401

@pytest.mark.asyncio
async def test_authenticated_player_dashboard_flow(client: AsyncClient, db_session: AsyncSession):
    # 1. Register player account
    reg_res = await client.post("/api/v1/account/register", json={
        "username": "DashHero",
        "password": "Password123!"
    })
    assert reg_res.status_code == 201

    # Login to obtain Bearer token
    login_res = await client.post("/api/v1/account/login", json={
        "username": "DashHero",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Before creating character, /character returns 404
    no_char_res = await client.get("/api/v1/player/character", headers=headers)
    assert no_char_res.status_code == 404

    # Create character
    create_char_res = await client.post("/api/v1/player/character", headers=headers, json={
        "nickname": "DashHero_RoS",
        "char_type": 0
    })
    assert create_char_res.status_code == 201
    char_data = create_char_res.json()
    assert char_data["nickname"] == "DashHero_RoS"
    assert char_data["diamonds"] == 100
    assert char_data["gold"] == 1000
    assert "stats" in char_data
    assert char_data["stats"]["total_matches"] == 0

    # 2. Retrieve character via GET /character
    char_res = await client.get("/api/v1/player/character", headers=headers)
    assert char_res.status_code == 200
    assert char_res.json()["nickname"] == "DashHero_RoS"
    assert char_res.json()["diamonds"] == 100

    # 3. Retrieve diamond wallet history
    history_res = await client.get("/api/v1/player/character/diamonds/history", headers=headers)
    assert history_res.status_code == 200
    wallet_data = history_res.json()
    assert wallet_data["current_balance"] == 100
    assert wallet_data["total_transactions"] == 0
    assert wallet_data["transactions"] == []

    # 4. Retrieve inventory
    inv_res = await client.get("/api/v1/player/character/inventory", headers=headers)
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["total_items"] == 0
    assert inv_data["items"] == []

@pytest.mark.asyncio
async def test_cross_account_isolation(client: AsyncClient, db_session: AsyncSession):
    # Create Player 1
    await client.post("/api/v1/account/register", json={"username": "PlayerOne", "password": "Password123!"})
    login1 = await client.post("/api/v1/account/login", json={"username": "PlayerOne", "password": "Password123!"})
    token1 = login1.json()["access_token"]
    h1 = {"Authorization": f"Bearer {token1}"}
    await client.post("/api/v1/player/character", headers=h1, json={"nickname": "One_Hero", "char_type": 0})

    # Create Player 2
    await client.post("/api/v1/account/register", json={"username": "PlayerTwo", "password": "Password123!"})
    login2 = await client.post("/api/v1/account/login", json={"username": "PlayerTwo", "password": "Password123!"})
    token2 = login2.json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}
    await client.post("/api/v1/player/character", headers=h2, json={"nickname": "Two_Hero", "char_type": 1})

    # Player 1 requests profile -> gets Player 1's data only
    p1_profile = await client.get("/api/v1/player/character", headers=h1)
    assert p1_profile.json()["nickname"] == "One_Hero"

    # Player 2 requests profile -> gets Player 2's data only
    p2_profile = await client.get("/api/v1/player/character", headers=h2)
    assert p2_profile.json()["nickname"] == "Two_Hero"
