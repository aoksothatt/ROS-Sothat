import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.account.models import Account
from app.account.service import AccountService
from app.cli.admin import promote_account

@pytest.fixture
async def sample_player(client: AsyncClient, db_session: AsyncSession) -> Account:
    """Creates a sample player account with a character and returns the DB model."""
    res = await client.post("/api/v1/account/register", json={
        "username": "bootstrap_candidate",
        "password": "InitialCandidatePassword123!"
    })
    assert res.status_code == 201
    account_id = res.json()["id"]

    # Also login and create character to verify character profile integrity
    login_res = await client.post("/api/v1/account/login", json={
        "username": "bootstrap_candidate",
        "password": "InitialCandidatePassword123!"
    })
    token = login_res.json()["access_token"]
    char_res = await client.post(
        "/api/v1/player/character",
        headers={"Authorization": f"Bearer {token}"},
        json={"nickname": "CandidateHero", "char_type": 1}
    )
    assert char_res.status_code == 201

    stmt = select(Account).where(Account.id == account_id)
    acc = (await db_session.execute(stmt)).scalars().first()
    return acc

@pytest.mark.asyncio
async def test_existing_player_successfully_promoted_after_confirmation(
    sample_player: Account,
    db_session: AsyncSession
):
    """Operator types 'y' at interactive prompt; user is elevated to admin."""
    assert sample_player.role == "player"

    # Simulate operator typing 'y'
    prompts_seen = []
    def mock_input(prompt: str) -> str:
        prompts_seen.append(prompt)
        return "y"

    success, msg = await promote_account(
        sample_player.username,
        assume_yes=False,
        session=db_session,
        input_func=mock_input
    )

    assert success is True
    assert "has been promoted to administrator" in msg
    assert len(prompts_seen) == 1
    assert "SECURITY CONFIRMATION" in prompts_seen[0]

    # Re-query account from database
    stmt = select(Account).where(Account.id == sample_player.id)
    refreshed = (await db_session.execute(stmt)).scalars().first()
    assert refreshed.role == "admin"

@pytest.mark.asyncio
async def test_existing_player_promoted_with_assume_yes(
    sample_player: Account,
    db_session: AsyncSession
):
    """Running with assume_yes=True skips interactive prompt and elevates account."""
    success, msg = await promote_account(
        sample_player.username,
        assume_yes=True,
        session=db_session
    )
    assert success is True
    assert "has been promoted to administrator" in msg

    stmt = select(Account).where(Account.id == sample_player.id)
    refreshed = (await db_session.execute(stmt)).scalars().first()
    assert refreshed.role == "admin"

@pytest.mark.asyncio
async def test_promotion_cancelled_by_operator(
    sample_player: Account,
    db_session: AsyncSession
):
    """Operator enters 'n' at interactive prompt; promotion is aborted and role unchanged."""
    assert sample_player.role == "player"

    success, msg = await promote_account(
        sample_player.username,
        assume_yes=False,
        session=db_session,
        input_func=lambda _: "n"
    )

    assert success is False
    assert "cancelled by operator" in msg

    stmt = select(Account).where(Account.id == sample_player.id)
    refreshed = (await db_session.execute(stmt)).scalars().first()
    assert refreshed.role == "player"

@pytest.mark.asyncio
async def test_promotion_cancelled_on_empty_or_eof(
    sample_player: Account,
    db_session: AsyncSession
):
    """Pressing Enter (default N) aborts promotion without modifying database."""
    success, msg = await promote_account(
        sample_player.username,
        assume_yes=False,
        session=db_session,
        input_func=lambda _: ""
    )
    assert success is False
    assert "cancelled by operator" in msg

    # Re-verify database
    stmt = select(Account).where(Account.id == sample_player.id)
    refreshed = (await db_session.execute(stmt)).scalars().first()
    assert refreshed.role == "player"

@pytest.mark.asyncio
async def test_unknown_username_rejected(db_session: AsyncSession):
    """Attempting to promote a non-existent account returns error and creates nothing."""
    success, msg = await promote_account(
        "non_existent_ghost_account",
        assume_yes=True,
        session=db_session
    )
    assert success is False
    assert "does not exist" in msg
    assert "Only existing accounts can be promoted" in msg

@pytest.mark.asyncio
async def test_no_account_created_when_promoting_unknown_user(db_session: AsyncSession):
    """Guarantees that the CLI never creates a new account or sets passwords."""
    count_before = (await db_session.execute(select(func.count(Account.id)))).scalar_one()

    await promote_account("fabricated_user_123", assume_yes=True, session=db_session)

    count_after = (await db_session.execute(select(func.count(Account.id)))).scalar_one()
    assert count_after == count_before

@pytest.mark.asyncio
async def test_already_admin_account_is_idempotent(
    sample_player: Account,
    db_session: AsyncSession
):
    """Promoting an account that is already admin succeeds idempotently without error."""
    # First promotion
    await promote_account(sample_player.username, assume_yes=True, session=db_session)

    # Second promotion
    success, msg = await promote_account(sample_player.username, assume_yes=True, session=db_session)
    assert success is True
    assert "already an administrator" in msg
    assert "No changes applied" in msg

@pytest.mark.asyncio
async def test_cannot_promote_banned_account(
    sample_player: Account,
    db_session: AsyncSession
):
    """Banned accounts cannot be promoted to admin."""
    # Ban the account first
    sample_player.is_banned = True
    sample_player.ban_reason = "Suspicious behavior"
    await db_session.commit()

    success, msg = await promote_account(sample_player.username, assume_yes=True, session=db_session)
    assert success is False
    assert "is banned" in msg
    assert "Cannot promote a banned account" in msg

    stmt = select(Account).where(Account.id == sample_player.id)
    refreshed = (await db_session.execute(stmt)).scalars().first()
    assert refreshed.role == "player"

@pytest.mark.asyncio
async def test_empty_or_whitespace_username_refused(db_session: AsyncSession):
    """Empty or whitespace usernames are rejected before database queries."""
    s1, m1 = await promote_account("", assume_yes=True, session=db_session)
    assert s1 is False
    assert "cannot be empty" in m1

    s2, m2 = await promote_account("   ", assume_yes=True, session=db_session)
    assert s2 is False
    assert "cannot be empty" in m2

@pytest.mark.asyncio
async def test_no_unintended_database_changes(
    sample_player: Account,
    db_session: AsyncSession
):
    """Promotion modifies ONLY the role column; all other credentials and profiles remain untouched."""
    # Snapshot original fields
    orig_pwd_hash = sample_player.password_hash
    orig_salt = sample_player.salt
    orig_created_at = sample_player.created_at
    orig_device_id = sample_player.device_id
    orig_username = sample_player.username

    # Execute promotion
    success, _ = await promote_account(sample_player.username, assume_yes=True, session=db_session)
    assert success is True

    # Re-fetch from database
    stmt = select(Account).where(Account.id == sample_player.id)
    refreshed = (await db_session.execute(stmt)).scalars().first()

    # Invariants: ONLY role changed
    assert refreshed.role == "admin"
    assert refreshed.password_hash == orig_pwd_hash
    assert refreshed.salt == orig_salt
    assert refreshed.created_at == orig_created_at
    assert refreshed.device_id == orig_device_id
    assert refreshed.username == orig_username
    assert refreshed.is_banned is False
