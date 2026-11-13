import pytest
from httpx import AsyncClient
from app.email.provider import get_email_provider, MockEmailProvider
from app.account.service import AccountService
from app.account.models import Account
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.fixture(autouse=True)
def clean_mock_email():
    provider = get_email_provider()
    if isinstance(provider, MockEmailProvider):
        provider.clear()
    yield
    if isinstance(provider, MockEmailProvider):
        provider.clear()

@pytest.mark.asyncio
async def test_website_e2e_registration_and_profile_flow(client: AsyncClient):
    """
    Website Integration Test 1-5:
    Simulates the frontend website registration flow:
    1. Website requests OTP
    2. Mock email provider captures code
    3. Website submits code to verify endpoint
    4. JWT session token is returned
    5. Website accesses /account/me to populate dashboard
    """
    provider = get_email_provider()
    assert isinstance(provider, MockEmailProvider)
    player_email = "web_player@ros-sothat.internal"

    # Step 1: Request OTP from website
    req_res = await client.post("/api/v1/account/otp/request", json={
        "email": player_email,
        "purpose": "registration"
    })
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert req_data["status"] == "ok"
    assert "w***r@ros-sothat.internal" in req_data["masked_email"]

    # Step 2: Retrieve code from development email provider
    code = provider.get_latest_otp_for(player_email)
    assert code is not None
    assert len(code) == 6

    # Step 3 & 4: Verify code and receive JWT Bearer token
    verify_res = await client.post("/api/v1/account/otp/verify", json={
        "email": player_email,
        "code": code,
        "purpose": "registration",
        "username": "WebOperator99"
    })
    assert verify_res.status_code == 200
    token_data = verify_res.json()
    assert "access_token" in token_data
    assert token_data["username"] == "WebOperator99"
    bearer_token = token_data["access_token"]

    # Step 5: Dashboard accesses /account/me with Bearer token
    me_res = await client.get("/api/v1/account/me", headers={
        "Authorization": f"Bearer {bearer_token}"
    })
    assert me_res.status_code == 200
    profile = me_res.json()
    assert profile["id"] == token_data["account_id"]
    assert profile["username"] == "WebOperator99"
    assert profile["email"] == player_email
    assert profile["role"] == "player"
    assert profile["is_banned"] is False
    assert profile["has_character"] is False

@pytest.mark.asyncio
async def test_website_e2e_login_flow(client: AsyncClient):
    """
    Website Integration Test 6:
    Existing registered player logs in via OTP through website.
    """
    provider = get_email_provider()
    player_email = "veteran@ros-sothat.internal"

    # Register initial account
    await client.post("/api/v1/account/otp/request", json={
        "email": player_email,
        "purpose": "registration"
    })
    reg_code = provider.get_latest_otp_for(player_email)
    await client.post("/api/v1/account/otp/verify", json={
        "email": player_email,
        "code": reg_code,
        "purpose": "registration",
        "username": "IslandVet"
    })
    provider.clear()

    # Login flow
    login_req = await client.post("/api/v1/account/otp/request", json={
        "email": player_email,
        "purpose": "login"
    })
    assert login_req.status_code == 200
    login_code = provider.get_latest_otp_for(player_email)
    assert login_code is not None

    login_verify = await client.post("/api/v1/account/otp/verify", json={
        "email": player_email,
        "code": login_code,
        "purpose": "login"
    })
    assert login_verify.status_code == 200
    assert "access_token" in login_verify.json()

@pytest.mark.asyncio
async def test_website_invalid_token_rejected_on_protected_endpoints(client: AsyncClient):
    """
    Website Integration Test 7 & 8:
    Invalid or forged token rejected with HTTP 401 on protected /account/me endpoint.
    """
    unauth_res = await client.get("/api/v1/account/me", headers={
        "Authorization": "Bearer forged.invalid.token"
    })
    assert unauth_res.status_code == 401
    assert "WWW-Authenticate" in unauth_res.headers

@pytest.mark.asyncio
async def test_website_admin_password_login_works_and_grants_access(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Website Integration Test 9:
    Admin password login option in LoginPage.vue authenticates and grants admin access.
    """
    salt = AccountService.generate_salt()
    pwd_hash = AccountService.hash_password("RootAdminPassword99!", salt)
    admin_acc = Account(
        username="web_super_admin",
        password_hash=pwd_hash,
        salt=salt,
        role="admin",
        is_banned=False
    )
    db_session.add(admin_acc)
    await db_session.commit()

    # Website admin form submission
    res = await client.post("/api/v1/account/login", json={
        "username": "web_super_admin",
        "password": "RootAdminPassword99!"
    })
    assert res.status_code == 200
    token = res.json()["access_token"]

    # Verify profile on /account/me reports role='admin'
    me_res = await client.get("/api/v1/account/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "admin"

@pytest.mark.asyncio
async def test_cors_preflight_and_headers_for_website(client: AsyncClient):
    """
    Verifies CORS headers allow requests from Vite development origin (http://127.0.0.1:5173).
    """
    headers = {
        "Origin": "http://127.0.0.1:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"
    }
    res = await client.options("/api/v1/account/otp/request", headers=headers)
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers
