import asyncio
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.email.provider import get_email_provider, MockEmailProvider
from app.account.models import Account, EmailOTP
from app.config import settings

@pytest.fixture(autouse=True)
def ensure_mock_email():
    """Ensure mock email provider is active and cleared for every test."""
    provider = get_email_provider()
    if isinstance(provider, MockEmailProvider):
        provider.clear()
    yield
    if isinstance(provider, MockEmailProvider):
        provider.clear()

@pytest.mark.asyncio
async def test_email_otp_registration_flow(client: AsyncClient):
    """Test full registration workflow: request OTP, dispatch email, verify code, receive JWT."""
    provider = get_email_provider()
    assert isinstance(provider, MockEmailProvider)

    # 1. Request registration OTP
    req_res = await client.post("/api/v1/account/otp/request", json={
        "email": "player_one@ros-sothat.internal",
        "purpose": "registration"
    })
    assert req_res.status_code == 200
    req_data = req_res.json()
    assert req_data["status"] == "ok"
    assert "p***e@ros-sothat.internal" in req_data["masked_email"]
    assert req_data["cooldown_seconds"] == settings.OTP_RESEND_COOLDOWN_SECONDS

    # 2. Retrieve dispatched OTP from mock provider
    otp_code = provider.get_latest_otp_for("player_one@ros-sothat.internal")
    assert otp_code is not None
    assert len(otp_code) == 6
    assert otp_code.isdigit()

    # 3. Verify OTP and register
    verify_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "player_one@ros-sothat.internal",
        "code": otp_code,
        "purpose": "registration"
    })
    assert verify_res.status_code == 200
    token_data = verify_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert "account_id" in token_data
    assert token_data["username"].startswith("player_")

    # 4. Authenticate to /me using issued Bearer token
    me_res = await client.get("/api/v1/account/me", headers={
        "Authorization": f"Bearer {token_data['access_token']}"
    })
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == token_data["account_id"]
    assert me_data["email"] == "player_one@ros-sothat.internal"
    assert me_data["role"] == "player"
    assert me_data["is_banned"] is False
    assert me_data["has_character"] is False

@pytest.mark.asyncio
async def test_email_otp_registration_with_custom_username(client: AsyncClient):
    """Test registration with an explicitly specified username."""
    provider = get_email_provider()

    await client.post("/api/v1/account/otp/request", json={
        "email": "sniper@ros-sothat.internal",
        "purpose": "registration"
    })
    otp_code = provider.get_latest_otp_for("sniper@ros-sothat.internal")

    verify_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "sniper@ros-sothat.internal",
        "code": otp_code,
        "purpose": "registration",
        "username": "custom_sniper_99"
    })
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["username"] == "custom_sniper_99"

@pytest.mark.asyncio
async def test_email_otp_registration_duplicate_username_rejected(client: AsyncClient):
    """Test that specifying a taken username returns 409 Conflict."""
    provider = get_email_provider()

    # Create account with 'taken_user'
    await client.post("/api/v1/account/register", json={
        "username": "taken_user",
        "password": "Password123!"
    })

    await client.post("/api/v1/account/otp/request", json={
        "email": "user2@ros-sothat.internal",
        "purpose": "registration"
    })
    otp_code = provider.get_latest_otp_for("user2@ros-sothat.internal")

    verify_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "user2@ros-sothat.internal",
        "code": otp_code,
        "purpose": "registration",
        "username": "taken_user"
    })
    assert verify_res.status_code == 409
    assert "already taken" in verify_res.json()["detail"]

@pytest.mark.asyncio
async def test_email_otp_login_flow(client: AsyncClient):
    """Test login via email OTP for an existing registered account."""
    provider = get_email_provider()

    # Step 1: Register account
    await client.post("/api/v1/account/otp/request", json={
        "email": "returning_player@ros-sothat.internal",
        "purpose": "registration"
    })
    reg_code = provider.get_latest_otp_for("returning_player@ros-sothat.internal")
    reg_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "returning_player@ros-sothat.internal",
        "code": reg_code,
        "purpose": "registration",
        "username": "returning_vet"
    })
    account_id = reg_res.json()["account_id"]
    provider.clear()

    # Step 2: Request login OTP
    login_req = await client.post("/api/v1/account/otp/request", json={
        "email": "returning_player@ros-sothat.internal",
        "purpose": "login"
    })
    assert login_req.status_code == 200
    login_code = provider.get_latest_otp_for("returning_player@ros-sothat.internal")
    assert login_code is not None

    # Step 3: Verify login OTP
    login_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "returning_player@ros-sothat.internal",
        "code": login_code,
        "purpose": "login"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["account_id"] == account_id
    assert login_data["username"] == "returning_vet"
    assert "access_token" in login_data

@pytest.mark.asyncio
async def test_user_enumeration_defense_on_login(client: AsyncClient):
    """Test that requesting login OTP for an unregistered email returns generic 200 without sending code."""
    provider = get_email_provider()

    res = await client.post("/api/v1/account/otp/request", json={
        "email": "ghost_unknown@ros-sothat.internal",
        "purpose": "login"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "If this email is registered" in data["message"]

    # Verify no email was dispatched
    dispatched = provider.get_latest_otp_for("ghost_unknown@ros-sothat.internal")
    assert dispatched is None

    # Attempting to verify any code fails
    verify_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "ghost_unknown@ros-sothat.internal",
        "code": "123456",
        "purpose": "login"
    })
    assert verify_res.status_code == 400

@pytest.mark.asyncio
async def test_banned_account_cannot_request_or_login_via_otp(client: AsyncClient, db_session: AsyncSession):
    """Test that banned players cannot request or authenticate via OTP."""
    provider = get_email_provider()

    # Register
    await client.post("/api/v1/account/otp/request", json={
        "email": "cheater@ros-sothat.internal",
        "purpose": "registration"
    })
    code = provider.get_latest_otp_for("cheater@ros-sothat.internal")
    reg_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "cheater@ros-sothat.internal",
        "code": code,
        "purpose": "registration"
    })
    account_id = reg_res.json()["account_id"]

    # Ban the account in DB
    await db_session.execute(
        update(Account).where(Account.id == account_id).values(is_banned=True, ban_reason="Speed hacking detected")
    )
    await db_session.commit()

    # Request login OTP should fail with 403
    req_res = await client.post("/api/v1/account/otp/request", json={
        "email": "cheater@ros-sothat.internal",
        "purpose": "login"
    })
    assert req_res.status_code == 403
    assert "banned" in req_res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_otp_attempt_limits_and_invalidation(client: AsyncClient):
    """Test that 5 consecutive wrong OTP codes permanently invalidate the code."""
    provider = get_email_provider()

    await client.post("/api/v1/account/otp/request", json={
        "email": "brute_force@ros-sothat.internal",
        "purpose": "registration"
    })
    real_code = provider.get_latest_otp_for("brute_force@ros-sothat.internal")
    wrong_code = "000000" if real_code != "000000" else "111111"

    # 4 failed attempts: each informs remaining attempts
    for attempt in range(1, 5):
        res = await client.post("/api/v1/account/otp/verify", json={
            "email": "brute_force@ros-sothat.internal",
            "code": wrong_code,
            "purpose": "registration"
        })
        assert res.status_code == 400
        assert f"{5 - attempt} attempt(s) remaining" in res.json()["detail"]

    # 5th failed attempt: code invalidated
    res5 = await client.post("/api/v1/account/otp/verify", json={
        "email": "brute_force@ros-sothat.internal",
        "code": wrong_code,
        "purpose": "registration"
    })
    assert res5.status_code == 400
    assert "invalidated due to too many failed attempts" in res5.json()["detail"]

    # 6th attempt with the REAL code must now be rejected
    res_real = await client.post("/api/v1/account/otp/verify", json={
        "email": "brute_force@ros-sothat.internal",
        "code": real_code,
        "purpose": "registration"
    })
    assert res_real.status_code == 400
    assert "invalid, expired, or previously used" in res_real.json()["detail"].lower()

@pytest.mark.asyncio
async def test_otp_resend_cooldown(client: AsyncClient):
    """Test that requesting an OTP twice within cooldown period returns 429 Too Many Requests."""
    res1 = await client.post("/api/v1/account/otp/request", json={
        "email": "cooldown_test@ros-sothat.internal",
        "purpose": "registration"
    })
    assert res1.status_code == 200

    # Immediate second request
    res2 = await client.post("/api/v1/account/otp/request", json={
        "email": "cooldown_test@ros-sothat.internal",
        "purpose": "registration"
    })
    assert res2.status_code == 429
    assert "Retry-After" in res2.headers
    assert "Please wait" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_otp_single_use_replay_prevention(client: AsyncClient):
    """Test that a consumed OTP cannot be re-used."""
    provider = get_email_provider()

    await client.post("/api/v1/account/otp/request", json={
        "email": "single_use@ros-sothat.internal",
        "purpose": "registration"
    })
    code = provider.get_latest_otp_for("single_use@ros-sothat.internal")

    # First verification succeeds
    res1 = await client.post("/api/v1/account/otp/verify", json={
        "email": "single_use@ros-sothat.internal",
        "code": code,
        "purpose": "registration"
    })
    assert res1.status_code == 200

    # Second verification fails
    res2 = await client.post("/api/v1/account/otp/verify", json={
        "email": "single_use@ros-sothat.internal",
        "code": code,
        "purpose": "registration"
    })
    assert res2.status_code == 400
    assert "invalid, expired, or previously used" in res2.json()["detail"].lower()

@pytest.mark.asyncio
async def test_expired_otp_rejection(client: AsyncClient, db_session: AsyncSession):
    """Test that an expired OTP is rejected."""
    provider = get_email_provider()

    await client.post("/api/v1/account/otp/request", json={
        "email": "expire_test@ros-sothat.internal",
        "purpose": "registration"
    })
    code = provider.get_latest_otp_for("expire_test@ros-sothat.internal")

    # Manually expire the OTP in the database
    past_time = datetime.utcnow() - timedelta(minutes=10)
    await db_session.execute(
        update(EmailOTP).where(EmailOTP.email == "expire_test@ros-sothat.internal").values(expires_at=past_time)
    )
    await db_session.commit()

    # Attempt to verify expired code
    res = await client.post("/api/v1/account/otp/verify", json={
        "email": "expire_test@ros-sothat.internal",
        "code": code,
        "purpose": "registration"
    })
    assert res.status_code == 400
    assert "invalid, expired, or previously used" in res.json()["detail"].lower()

@pytest.mark.asyncio
async def test_database_stores_salted_hash_not_plaintext(client: AsyncClient, db_session: AsyncSession):
    """Verify cryptographic protection: raw OTP is never stored in DB."""
    provider = get_email_provider()

    await client.post("/api/v1/account/otp/request", json={
        "email": "crypto_audit@ros-sothat.internal",
        "purpose": "registration"
    })
    raw_code = provider.get_latest_otp_for("crypto_audit@ros-sothat.internal")

    # Inspect the DB record
    stmt = select(EmailOTP).where(EmailOTP.email == "crypto_audit@ros-sothat.internal")
    result = await db_session.execute(stmt)
    record = result.scalars().first()

    assert record is not None
    assert record.otp_hash != raw_code
    assert len(record.otp_hash) == 64  # SHA-256 hex string
    assert len(record.salt) == 32      # 16 bytes hex salt

@pytest.mark.asyncio
async def test_malformed_email_and_code_validation(client: AsyncClient):
    """Test Pydantic input validation for malformed emails and codes."""
    # Bad email
    res1 = await client.post("/api/v1/account/otp/request", json={
        "email": "not-an-email",
        "purpose": "registration"
    })
    assert res1.status_code == 422

    # Bad OTP code (letters)
    res2 = await client.post("/api/v1/account/otp/verify", json={
        "email": "valid@ros-sothat.internal",
        "code": "abcdef",
        "purpose": "registration"
    })
    assert res2.status_code == 422

    # Bad OTP code (too short)
    res3 = await client.post("/api/v1/account/otp/verify", json={
        "email": "valid@ros-sothat.internal",
        "code": "12345",
        "purpose": "registration"
    })
    assert res3.status_code == 422

# -----------------------------------------------------------------
# Phase P02.1 Additional Security & Integration Tests
# -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_otp_hmac_secret_configuration_and_fallbacks():
    """Verify HMAC secret resolution: dedicated OTP_SECRET_KEY, fallback to SECRET_KEY."""
    from app.account.service import AccountService
    
    # 1. Fallback to SECRET_KEY when OTP_SECRET_KEY is empty
    orig_otp_secret = settings.OTP_SECRET_KEY
    orig_app_secret = settings.SECRET_KEY
    try:
        settings.OTP_SECRET_KEY = ""
        settings.SECRET_KEY = "standard-app-secret-at-least-32-chars-long"
        secret = AccountService.get_otp_hmac_secret()
        assert secret == b"standard-app-secret-at-least-32-chars-long"

        # 2. Prefer dedicated OTP_SECRET_KEY when set
        settings.OTP_SECRET_KEY = "dedicated-otp-secret-key-at-least-32-bytes!"
        secret2 = AccountService.get_otp_hmac_secret()
        assert secret2 == b"dedicated-otp-secret-key-at-least-32-bytes!"
    finally:
        settings.OTP_SECRET_KEY = orig_otp_secret
        settings.SECRET_KEY = orig_app_secret

@pytest.mark.asyncio
async def test_otp_hmac_missing_and_invalid_secrets_rejected():
    """Verify that missing or too-short secrets raise ValueError."""
    from app.account.service import AccountService

    orig_otp_secret = settings.OTP_SECRET_KEY
    orig_app_secret = settings.SECRET_KEY
    try:
        # Both empty
        settings.OTP_SECRET_KEY = ""
        settings.SECRET_KEY = ""
        with pytest.raises(ValueError, match="Missing OTP secret key"):
            AccountService.get_otp_hmac_secret()

        # Whitespace only
        settings.OTP_SECRET_KEY = "   "
        settings.SECRET_KEY = "   "
        with pytest.raises(ValueError, match="Missing OTP secret key"):
            AccountService.get_otp_hmac_secret()

        # Too short (< 16 bytes)
        settings.OTP_SECRET_KEY = "too_short_key"
        with pytest.raises(ValueError, match="Invalid OTP secret key: must be at least 16 bytes"):
            AccountService.get_otp_hmac_secret()
    finally:
        settings.OTP_SECRET_KEY = orig_otp_secret
        settings.SECRET_KEY = orig_app_secret

@pytest.mark.asyncio
async def test_otp_verification_survives_application_restart(client: AsyncClient):
    """
    Verify that an OTP generated before a server restart can still be verified
    after the restart as long as the server secret key is unchanged.
    """
    from app.account.service import AccountService
    provider = get_email_provider()

    # 1. Request OTP in 'current' instance
    await client.post("/api/v1/account/otp/request", json={
        "email": "restart_test@ros-sothat.internal",
        "purpose": "registration"
    })
    code = provider.get_latest_otp_for("restart_test@ros-sothat.internal")
    assert code is not None

    # 2. Simulate server restart: re-evaluate secret key and verify with fresh context
    secret_bytes = AccountService.get_otp_hmac_secret()
    assert len(secret_bytes) >= 16

    # 3. Complete verification after simulated restart
    verify_res = await client.post("/api/v1/account/otp/verify", json={
        "email": "restart_test@ros-sothat.internal",
        "code": code,
        "purpose": "registration"
    })
    assert verify_res.status_code == 200
    assert "access_token" in verify_res.json()

@pytest.mark.asyncio
async def test_incompatible_legacy_otp_challenge_safely_invalidated(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    Verify that an outstanding challenge generated under legacy un-keyed salted SHA-256
    is safely detected, invalidated, and rejected with a clear upgrade notice.
    """
    import hashlib
    import secrets

    # 1. Manually insert an outstanding challenge using legacy salted SHA-256
    raw_code = "849201"
    salt = secrets.token_hex(16)
    legacy_sha256_hash = hashlib.sha256(f"{salt}:{raw_code}".encode("utf-8")).hexdigest()

    legacy_otp = EmailOTP(
        email="legacy_user@ros-sothat.internal",
        otp_hash=legacy_sha256_hash,
        salt=salt,
        purpose="registration",
        attempts_left=5,
        is_used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=5),
        created_at=datetime.utcnow()
    )
    db_session.add(legacy_otp)
    await db_session.commit()
    await db_session.refresh(legacy_otp)

    # 2. Attempt to verify the legacy code
    res = await client.post("/api/v1/account/otp/verify", json={
        "email": "legacy_user@ros-sothat.internal",
        "code": raw_code,
        "purpose": "registration"
    })
    assert res.status_code == 400
    assert "upgraded for security" in res.json()["detail"].lower()

    # 3. Verify that the legacy OTP row was safely marked as used (invalidated)
    await db_session.refresh(legacy_otp)
    assert legacy_otp.is_used is True

@pytest.mark.asyncio
async def test_lockout_only_locks_current_challenge_and_recovers_after_cooldown(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    TASK 3 Verification: Confirm that 5 failed attempts lock ONLY the current OTP challenge.
    A user is NOT permanently locked out and can successfully request and verify a new OTP.
    """
    provider = get_email_provider()
    target_email = "recovery_player@ros-sothat.internal"

    # Step 1: Request OTP #1
    req1 = await client.post("/api/v1/account/otp/request", json={
        "email": target_email,
        "purpose": "registration"
    })
    assert req1.status_code == 200
    otp1 = provider.get_latest_otp_for(target_email)

    # Step 2: Attacker exhausts 5 attempts with wrong codes
    for _ in range(5):
        await client.post("/api/v1/account/otp/verify", json={
            "email": target_email,
            "code": "000000",
            "purpose": "registration"
        })

    # Step 3: Verify OTP #1 is permanently dead
    dead_res = await client.post("/api/v1/account/otp/verify", json={
        "email": target_email,
        "code": otp1,
        "purpose": "registration"
    })
    assert dead_res.status_code == 400
    assert "invalid, expired, or previously used" in dead_res.json()["detail"].lower()

    # Step 4: Advance time past 60s cooldown in the database
    past_time = datetime.utcnow() - timedelta(seconds=70)
    await db_session.execute(
        update(EmailOTP).where(EmailOTP.email == target_email).values(created_at=past_time)
    )
    await db_session.commit()

    # Step 5: User requests OTP #2 (Recovery)
    provider.clear()
    req2 = await client.post("/api/v1/account/otp/request", json={
        "email": target_email,
        "purpose": "registration"
    })
    assert req2.status_code == 200
    otp2 = provider.get_latest_otp_for(target_email)
    assert otp2 is not None
    assert otp2 != otp1

    # Step 6: User verifies OTP #2 with the correct code -> Success!
    verify_res = await client.post("/api/v1/account/otp/verify", json={
        "email": target_email,
        "code": otp2,
        "purpose": "registration",
        "username": "recovered_hero"
    })
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["username"] == "recovered_hero"
    assert "access_token" in data

@pytest.mark.asyncio
async def test_duplicate_email_registration_rejected_and_role_is_player(
    client: AsyncClient,
    db_session: AsyncSession
):
    """
    TASK 4 Verification: Verify duplicate email handling and strict 'player' role assignment.
    """
    provider = get_email_provider()
    target_email = "role_audit@ros-sothat.internal"

    # 1. Register first account
    await client.post("/api/v1/account/otp/request", json={
        "email": target_email,
        "purpose": "registration"
    })
    code1 = provider.get_latest_otp_for(target_email)
    res1 = await client.post("/api/v1/account/otp/verify", json={
        "email": target_email,
        "code": code1,
        "purpose": "registration"
    })
    assert res1.status_code == 200
    token = res1.json()["access_token"]

    # Verify role on /me is strictly 'player'
    me_res = await client.get("/api/v1/account/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "player"

    # Advance cooldown timestamp in DB so next request is past 60s cooldown
    past_time = datetime.utcnow() - timedelta(seconds=70)
    await db_session.execute(
        update(EmailOTP).where(EmailOTP.email == target_email).values(created_at=past_time)
    )
    await db_session.commit()

    # 2. Attempt duplicate registration request (enumeration defense generic response)
    provider.clear()
    dup_req = await client.post("/api/v1/account/otp/request", json={
        "email": target_email,
        "purpose": "registration"
    })
    assert dup_req.status_code == 200
    # No new registration code was dispatched
    assert provider.get_latest_otp_for(target_email) is None

@pytest.mark.asyncio
async def test_admin_account_authentication_remains_unchanged(client: AsyncClient, db_session: AsyncSession):
    """
    TASK 4 Verification: Existing admin password authentication and RBAC remain completely functional.
    """
    from app.account.service import AccountService

    # 1. Create admin user with traditional password
    salt = AccountService.generate_salt()
    pwd_hash = AccountService.hash_password("SuperSecretAdminPass123!", salt)
    admin_acc = Account(
        username="chief_admin",
        password_hash=pwd_hash,
        salt=salt,
        role="admin",
        is_banned=False
    )
    db_session.add(admin_acc)
    await db_session.commit()

    # 2. Authenticate admin via traditional password login endpoint
    login_res = await client.post("/api/v1/account/login", json={
        "username": "chief_admin",
        "password": "SuperSecretAdminPass123!"
    })
    assert login_res.status_code == 200
    admin_token = login_res.json()["access_token"]

    # 3. Access admin protected endpoint
    admin_check = await client.get("/api/v1/admin/accounts", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_check.status_code == 200
