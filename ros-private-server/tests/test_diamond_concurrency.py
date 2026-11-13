import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine

from app.database.base import Base
from app.account.models import Account
from app.player.models import Character
from app.economy.models import DiamondTransaction
from app.economy.repository import EconomyRepository
from app.economy.service import EconomyService
from app.economy.schemas import DiamondGrantRequest, DiamondDeductRequest

@pytest_asyncio.fixture
async def concurrency_engine():
    """
    Isolated file-based SQLite database for genuine multi-connection concurrency testing.
    Avoids StaticPool connection contention and reflects true database-level lock behavior.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "concurrency_test.db")
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            connect_args={"timeout": 30.0}
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()

@pytest_asyncio.fixture
async def concurrency_setup(concurrency_engine: AsyncEngine) -> dict:
    """Prepares an administrator account and a target player character with 100 diamonds."""
    session_factory = async_sessionmaker(concurrency_engine, expire_on_commit=False)
    async with session_factory() as session:
        admin = Account(
            username="concurrency_admin",
            password_hash="hashed_pw",
            salt="salt_123",
            role="admin"
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        player = Account(
            username="concurrency_player",
            password_hash="hashed_pw",
            salt="salt_456",
            role="player"
        )
        session.add(player)
        await session.commit()
        await session.refresh(player)

        char = Character(
            account_id=player.id,
            nickname="ConcurrencyHero",
            char_type=0,
            diamonds=100
        )
        session.add(char)
        await session.commit()
        await session.refresh(char)

        return {
            "session_factory": session_factory,
            "admin_id": admin.id,
            "character_gid": char.gid,
            "initial_diamonds": 100
        }

@pytest.mark.asyncio
async def test_concurrent_grants_accumulate_safely(concurrency_setup: dict):
    """
    Scenario A: Concurrent grants
    Initial balance: 100.
    Two simultaneous grants of 80.
    Expected final balance: 260.
    Exactly two ledger entries.
    """
    session_factory = concurrency_setup["session_factory"]
    gid = concurrency_setup["character_gid"]
    admin_id = concurrency_setup["admin_id"]

    async def run_grant(amt: int, key: str):
        async with session_factory() as session:
            service = EconomyService(EconomyRepository(session))
            req = DiamondGrantRequest(amount=amt, idempotency_key=key, reason="Concurrent grant test")
            return await service.grant_diamonds(gid, admin_id, req)

    # Execute simultaneous grants with asyncio.gather
    res1, res2 = await asyncio.gather(
        run_grant(80, "conc_grant_01"),
        run_grant(80, "conc_grant_02")
    )

    # Both must succeed
    assert res1.operation_type == "GRANT"
    assert res2.operation_type == "GRANT"
    assert res1.amount == 80
    assert res2.amount == 80

    # Verify final balance is 260 (100 + 80 + 80)
    async with session_factory() as session:
        val = await session.execute(select(Character.diamonds).where(Character.gid == gid))
        assert val.scalar_one() == 260

        tx_stmt = select(DiamondTransaction).where(DiamondTransaction.character_gid == gid)
        txs = list((await session.execute(tx_stmt)).scalars().all())
        assert len(txs) == 2

@pytest.mark.asyncio
async def test_concurrent_deductions_prevent_overdraft(concurrency_setup: dict):
    """
    Scenario B: Concurrent deductions
    Initial balance: 100.
    Two simultaneous deductions of 80.
    Expected: Exactly one succeeds, one fails with 400 Insufficient balance.
    Final balance: 20.
    Exactly one successful ledger entry.
    """
    session_factory = concurrency_setup["session_factory"]
    gid = concurrency_setup["character_gid"]
    admin_id = concurrency_setup["admin_id"]

    async def run_deduct(amt: int, key: str):
        async with session_factory() as session:
            service = EconomyService(EconomyRepository(session))
            req = DiamondDeductRequest(amount=amt, idempotency_key=key, reason="Concurrent deduct test")
            return await service.deduct_diamonds(gid, admin_id, req)

    # Execute simultaneous deductions
    results = await asyncio.gather(
        run_deduct(80, "conc_deduct_01"),
        run_deduct(80, "conc_deduct_02"),
        return_exceptions=True
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert successes[0].balance_after == 20
    assert "Insufficient diamond balance" in failures[0].detail
    assert failures[0].status_code == 400

    # Final balance must be exactly 20
    async with session_factory() as session:
        val = await session.execute(select(Character.diamonds).where(Character.gid == gid))
        assert val.scalar_one() == 20

        tx_stmt = select(DiamondTransaction).where(DiamondTransaction.character_gid == gid)
        txs = list((await session.execute(tx_stmt)).scalars().all())
        assert len(txs) == 1
        assert txs[0].amount == 80
        assert txs[0].balance_after == 20

@pytest.mark.asyncio
async def test_identical_simultaneous_requests(concurrency_setup: dict):
    """
    Scenario C: Identical simultaneous requests
    Send two requests with the same idempotency key and identical parameters simultaneously.
    Expected: Both return identical transaction; exactly one ledger entry and one balance change.
    """
    session_factory = concurrency_setup["session_factory"]
    gid = concurrency_setup["character_gid"]
    admin_id = concurrency_setup["admin_id"]

    async def run_grant(amt: int, key: str):
        async with session_factory() as session:
            service = EconomyService(EconomyRepository(session))
            req = DiamondGrantRequest(amount=amt, idempotency_key=key, reason="Identical race")
            return await service.grant_diamonds(gid, admin_id, req)

    res1, res2 = await asyncio.gather(
        run_grant(50, "same_idemp_key_01"),
        run_grant(50, "same_idemp_key_01")
    )

    # Both requests must resolve to the identical transaction
    assert res1.id == res2.id
    assert res1.amount == 50
    assert res1.balance_after == 150
    assert res2.balance_after == 150

    # Balance incremented only once
    async with session_factory() as session:
        val = await session.execute(select(Character.diamonds).where(Character.gid == gid))
        assert val.scalar_one() == 150

        tx_stmt = select(DiamondTransaction).where(DiamondTransaction.character_gid == gid)
        txs = list((await session.execute(tx_stmt)).scalars().all())
        assert len(txs) == 1

@pytest.mark.asyncio
async def test_conflicting_simultaneous_requests(concurrency_setup: dict):
    """
    Scenario D: Conflicting simultaneous requests
    Same idempotency key but different amounts sent simultaneously.
    Expected: Exactly one accepted transaction (HTTP 200) and one HTTP 409 conflict.
    """
    session_factory = concurrency_setup["session_factory"]
    gid = concurrency_setup["character_gid"]
    admin_id = concurrency_setup["admin_id"]

    async def run_grant(amt: int, key: str):
        async with session_factory() as session:
            service = EconomyService(EconomyRepository(session))
            req = DiamondGrantRequest(amount=amt, idempotency_key=key, reason="Conflicting race")
            return await service.grant_diamonds(gid, admin_id, req)

    results = await asyncio.gather(
        run_grant(50, "conflict_race_key"),
        run_grant(75, "conflict_race_key"),
        return_exceptions=True
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    conflicts = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(conflicts) == 1
    assert conflicts[0].status_code == 409
    assert "Idempotency key" in conflicts[0].detail

    # The accepted transaction is either 50 or 75, balance updated once, unaccepted grant rolled back
    accepted_amount = successes[0].amount
    async with session_factory() as session:
        val = await session.execute(select(Character.diamonds).where(Character.gid == gid))
        assert val.scalar_one() == 100 + accepted_amount

        tx_stmt = select(DiamondTransaction).where(DiamondTransaction.character_gid == gid)
        txs = list((await session.execute(tx_stmt)).scalars().all())
        assert len(txs) == 1

@pytest.mark.asyncio
async def test_rollback_on_ledger_insertion_failure(concurrency_setup: dict):
    """
    Scenario E: Rollback
    Simulate a failure during ledger insertion.
    Verify the balance update is rolled back and the original balance remains untouched.
    """
    session_factory = concurrency_setup["session_factory"]
    gid = concurrency_setup["character_gid"]
    admin_id = concurrency_setup["admin_id"]

    async with session_factory() as session:
        repo = EconomyRepository(session)
        service = EconomyService(repo)

        # Mock repository.create_transaction to simulate mid-transaction failure
        async def failing_create(*args, **kwargs):
            raise RuntimeError("Simulated ledger disk corruption failure")

        repo.create_transaction = failing_create

        with pytest.raises(RuntimeError, match="Simulated ledger disk corruption failure"):
            await service.grant_diamonds(
                gid,
                admin_id,
                DiamondGrantRequest(amount=50, idempotency_key="fail_key_01", reason="Will fail")
            )

    # Balance must remain completely unchanged at 100
    async with session_factory() as session:
        val = await session.execute(select(Character.diamonds).where(Character.gid == gid))
        assert val.scalar_one() == 100

        tx_stmt = select(DiamondTransaction).where(DiamondTransaction.character_gid == gid)
        txs = list((await session.execute(tx_stmt)).scalars().all())
        assert len(txs) == 0

@pytest.mark.asyncio
async def test_mixed_concurrent_operations(concurrency_setup: dict):
    """
    Scenario F: Mixed concurrent operations
    Run multiple grants and deductions simultaneously against one character.
    Verify the final balance strictly equals the sum of successful ledger operations.
    """
    session_factory = concurrency_setup["session_factory"]
    gid = concurrency_setup["character_gid"]
    admin_id = concurrency_setup["admin_id"]

    async def run_grant(amt: int, key: str):
        async with session_factory() as session:
            service = EconomyService(EconomyRepository(session))
            req = DiamondGrantRequest(amount=amt, idempotency_key=key, reason="Mixed grant")
            return await service.grant_diamonds(gid, admin_id, req)

    async def run_deduct(amt: int, key: str):
        async with session_factory() as session:
            service = EconomyService(EconomyRepository(session))
            req = DiamondDeductRequest(amount=amt, idempotency_key=key, reason="Mixed deduct")
            return await service.deduct_diamonds(gid, admin_id, req)

    tasks = [
        run_grant(50, "mixed_g1"),
        run_deduct(30, "mixed_d1"),
        run_grant(100, "mixed_g2"),
        run_deduct(70, "mixed_d2"),
        run_grant(25, "mixed_g3"),
        run_deduct(250, "mixed_d3"),  # Expected to fail due to insufficient balance
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Query final database state
    async with session_factory() as session:
        val = await session.execute(select(Character.diamonds).where(Character.gid == gid))
        final_balance = val.scalar_one()

        tx_stmt = select(DiamondTransaction).where(DiamondTransaction.character_gid == gid)
        txs = list((await session.execute(tx_stmt)).scalars().all())

        # Mathematical reconciliation
        net_ledger_change = sum(
            t.amount if t.operation_type == "GRANT" else -t.amount
            for t in txs
        )
        expected_balance = concurrency_setup["initial_diamonds"] + net_ledger_change

        assert final_balance == expected_balance
        assert final_balance >= 0
