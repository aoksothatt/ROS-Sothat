import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.lobby.service import LobbyService
from app.room.service import RoomService
from app.matchmaking.service import MatchmakingService
from app.account.rate_limiter import InMemoryRateLimiter

# Use in-memory SQLite with StaticPool by default; supports isolated PostgreSQL via TEST_POSTGRES_URL
TEST_DATABASE_URL = os.getenv("TEST_POSTGRES_URL") or os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

if "sqlite" in TEST_DATABASE_URL:
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
else:
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        future=True
    )

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    import app.account.models
    import app.player.models
    import app.economy.models
    import app.inventory.models
    import app.admin.models
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(autouse=True)
async def reset_services():
    # Reset in-memory singletons before each test
    LobbyService._instance = None
    RoomService._instance = None
    MatchmakingService._instance = None
    InMemoryRateLimiter._instance = None
    yield

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestAsyncSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        async with TestAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    # Helper to register and return auth headers
    res = await client.post("/api/v1/account/register", json={
        "username": "test_operator",
        "password": "Password123!"
    })
    assert res.status_code == 201
    
    login_res = await client.post("/api/v1/account/login", json={
        "username": "test_operator",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def auth_headers_with_character(client: AsyncClient, auth_headers: dict) -> dict:
    # Create character for the test user
    char_res = await client.post(
        "/api/v1/player/character",
        headers=auth_headers,
        json={"nickname": "GhostRider", "char_type": 0}
    )
    assert char_res.status_code == 201
    return auth_headers
