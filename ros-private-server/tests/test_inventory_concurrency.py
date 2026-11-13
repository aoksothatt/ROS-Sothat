import asyncio
import os
import tempfile
import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine

from app.database.base import Base
from app.account.models import Account
from app.player.models import Character
from app.economy.models import DiamondTransaction
from app.inventory.models import Item, InventoryItem, InventoryTransaction
from app.inventory.repository import InventoryRepository
from app.inventory.service import InventoryService
from app.inventory.schemas import InventoryGrantRequest, InventoryRemoveRequest

@pytest_asyncio.fixture
async def inventory_concurrency_engine():
    """
    Isolated file-based SQLite database for genuine multi-connection concurrency testing.
    Avoids StaticPool connection contention and reflects true database-level lock behavior.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "inventory_concurrency_test.db")
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            connect_args={"timeout": 30.0}
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()

@pytest_asyncio.fixture
async def inventory_concurrency_setup(inventory_concurrency_engine: AsyncEngine) -> dict:
    """Prepares an administrator account, a player character, and catalog items."""
    session_factory = async_sessionmaker(inventory_concurrency_engine, expire_on_commit=False)
    async with session_factory() as session:
        admin = Account(
            username="inv_conc_admin",
            password_hash="hashed_pw",
            salt="salt_admin",
            role="admin"
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        player = Account(
            username="inv_conc_player",
            password_hash="hashed_pw",
            salt="salt_player",
            role="player"
        )
        session.add(player)
        await session.commit()
        await session.refresh(player)

        char = Character(
            account_id=player.id,
            nickname="InvConcHero",
            char_type=0
        )
        session.add(char)
        await session.commit()
        await session.refresh(char)

        stackable_item = Item(
            item_code="AMMO_556_CONC",
            name="5.56mm Ammo",
            item_type="CONSUMABLE",
            stackable=True,
            max_stack=500
        )
        session.add(stackable_item)

        non_stackable_item = Item(
            item_code="ARMOR_KEVLAR_CONC",
            name="Kevlar Body Armor",
            item_type="CLOTHING",
            stackable=False,
            max_stack=1
        )
        session.add(non_stackable_item)

        await session.commit()
        await session.refresh(stackable_item)
        await session.refresh(non_stackable_item)

        return {
            "session_factory": session_factory,
            "admin_id": admin.id,
            "character_gid": char.gid,
            "ammo_item_id": stackable_item.id,
            "armor_item_id": non_stackable_item.id
        }

# -----------------------------------------------------------------
# 1. Finding TEST-02A: Concurrent Mixed Operations
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_inventory_mixed_operations(inventory_concurrency_setup: dict):
    """
    Finding TEST-02A: Start with known inventory quantity (50).
    Run simultaneous grants (+20, +15, +25) and removals (-10, -20).
    Verify mathematically correct final balance: 50 + 60 - 30 = 80.
    Verify no lost updates, no negative quantities, and accurate transaction records.
    """
    session_factory = inventory_concurrency_setup["session_factory"]
    gid = inventory_concurrency_setup["character_gid"]
    admin_id = inventory_concurrency_setup["admin_id"]
    item_id = inventory_concurrency_setup["ammo_item_id"]

    # 1. Seed initial inventory = 50
    async with session_factory() as session:
        service = InventoryService(InventoryRepository(session))
        seed_tx = await service.grant_inventory(
            gid, admin_id,
            InventoryGrantRequest(item_id=item_id, quantity=50, idempotency_key="seed_ammo", reason="Initial drop")
        )
        assert seed_tx.quantity_after == 50

    # 2. Worker coroutines for simultaneous execution
    async def do_grant(qty: int, key: str):
        async with session_factory() as session:
            service = InventoryService(InventoryRepository(session))
            return await service.grant_inventory(
                gid, admin_id,
                InventoryGrantRequest(item_id=item_id, quantity=qty, idempotency_key=key, reason=f"Grant {qty}")
            )

    async def do_remove(qty: int, key: str):
        async with session_factory() as session:
            service = InventoryService(InventoryRepository(session))
            return await service.remove_inventory(
                gid, admin_id,
                InventoryRemoveRequest(item_id=item_id, quantity=qty, idempotency_key=key, reason=f"Remove {qty}")
            )

    # Execute 3 grants and 2 removals concurrently
    results = await asyncio.gather(
        do_grant(20, "mix_g_1"),
        do_grant(15, "mix_g_2"),
        do_grant(25, "mix_g_3"),
        do_remove(10, "mix_r_1"),
        do_remove(20, "mix_r_2"),
        return_exceptions=True
    )

    # All 5 operations must succeed without exception
    assert all(not isinstance(r, Exception) for r in results), f"Errors in concurrent mixed operations: {results}"

    # 3. Verify final inventory quantity
    async with session_factory() as session:
        slot = (await session.execute(
            select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id)
        )).scalar_one_or_none()
        assert slot is not None
        assert slot.quantity == 80  # 50 + 20 + 15 + 25 - 10 - 20 = 80

        # Verify transaction history entries (1 seed + 5 concurrent = 6)
        tx_count = (await session.execute(
            select(InventoryTransaction).where(InventoryTransaction.character_gid == gid)
        )).scalars().all()
        assert len(tx_count) == 6

# -----------------------------------------------------------------
# 2. Finding TEST-02: Concurrent Grants Exceeding max_stack
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_inventory_grants_exceeding_max_stack(inventory_concurrency_setup: dict):
    """
    Verify that concurrent grants cannot exceed max_stack.
    Initial: 50. max_stack: 70.
    Two simultaneous grants of 15 (50 + 15 + 15 = 80 > 70).
    Exactly one succeeds (+15 -> 65), the second fails with HTTP 400.
    Final balance stays at 65.
    """
    session_factory = inventory_concurrency_setup["session_factory"]
    gid = inventory_concurrency_setup["character_gid"]
    admin_id = inventory_concurrency_setup["admin_id"]

    # Create an item with max_stack = 70
    async with session_factory() as session:
        special_ammo = Item(
            item_code="AMMO_EXPLOSIVE_70",
            name="Explosive Ammo",
            item_type="CONSUMABLE",
            stackable=True,
            max_stack=70
        )
        session.add(special_ammo)
        await session.commit()
        await session.refresh(special_ammo)
        item_id = special_ammo.id

        service = InventoryService(InventoryRepository(session))
        await service.grant_inventory(
            gid, admin_id,
            InventoryGrantRequest(item_id=item_id, quantity=50, idempotency_key="exp_seed", reason="Seed 50")
        )

    async def run_grant(qty: int, key: str):
        async with session_factory() as session:
            service = InventoryService(InventoryRepository(session))
            return await service.grant_inventory(
                gid, admin_id,
                InventoryGrantRequest(item_id=item_id, quantity=qty, idempotency_key=key, reason="Concurrent grant")
            )

    results = await asyncio.gather(
        run_grant(15, "cg_stack_1"),
        run_grant(15, "cg_stack_2"),
        return_exceptions=True
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(failures) == 1, f"Expected 1 failure, got {len(failures)}"
    assert isinstance(failures[0], HTTPException)
    assert failures[0].status_code == 400
    assert "exceed max stack limit" in failures[0].detail

    # Verify final balance is 65
    async with session_factory() as session:
        slot = (await session.execute(
            select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id)
        )).scalar_one_or_none()
        assert slot.quantity == 65

# -----------------------------------------------------------------
# 3. Finding TEST-02: Concurrent Deductions Prevent Overdraft
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_inventory_removals_prevent_overdraft(inventory_concurrency_setup: dict):
    """
    Initial balance: 100.
    Two simultaneous removals of 80.
    Exactly one succeeds (-80 -> 20), second fails with HTTP 400.
    Final balance stays at 20 without overdraft.
    """
    session_factory = inventory_concurrency_setup["session_factory"]
    gid = inventory_concurrency_setup["character_gid"]
    admin_id = inventory_concurrency_setup["admin_id"]
    item_id = inventory_concurrency_setup["ammo_item_id"]

    # Seed 100 items
    async with session_factory() as session:
        service = InventoryService(InventoryRepository(session))
        await service.grant_inventory(
            gid, admin_id,
            InventoryGrantRequest(item_id=item_id, quantity=100, idempotency_key="overdraft_seed", reason="Seed 100")
        )

    async def run_remove(qty: int, key: str):
        async with session_factory() as session:
            service = InventoryService(InventoryRepository(session))
            return await service.remove_inventory(
                gid, admin_id,
                InventoryRemoveRequest(item_id=item_id, quantity=qty, idempotency_key=key, reason="Concurrent remove")
            )

    results = await asyncio.gather(
        run_remove(80, "conc_rem_1"),
        run_remove(80, "conc_rem_2"),
        return_exceptions=True
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], HTTPException)
    assert failures[0].status_code == 400
    assert "Insufficient item quantity" in failures[0].detail

    async with session_factory() as session:
        slot = (await session.execute(
            select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id)
        )).scalar_one_or_none()
        assert slot.quantity == 20

# -----------------------------------------------------------------
# 4. Finding TEST-02B: Concurrent Idempotency
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_inventory_idempotency_identical_requests(inventory_concurrency_setup: dict):
    """
    Finding TEST-02B: Submit 4 identical requests concurrently with the same idempotency key.
    Verify exactly one mutation occurs, all responses refer to the same transaction ID,
    and only one ledger record is created.
    """
    session_factory = inventory_concurrency_setup["session_factory"]
    gid = inventory_concurrency_setup["character_gid"]
    admin_id = inventory_concurrency_setup["admin_id"]
    item_id = inventory_concurrency_setup["ammo_item_id"]

    shared_key = "idemp_identical_race_01"

    async def run_grant():
        async with session_factory() as session:
            service = InventoryService(InventoryRepository(session))
            return await service.grant_inventory(
                gid, admin_id,
                InventoryGrantRequest(item_id=item_id, quantity=25, idempotency_key=shared_key, reason="Identical race")
            )

    # Run 4 identical requests concurrently
    results = await asyncio.gather(
        run_grant(),
        run_grant(),
        run_grant(),
        run_grant(),
        return_exceptions=True
    )

    # All must return successfully
    assert all(not isinstance(r, Exception) for r in results), f"Failures: {results}"

    # All transaction IDs must be identical
    tx_ids = [r.id for r in results]
    assert len(set(tx_ids)) == 1, f"Expected identical transaction ID, got {tx_ids}"

    # Verify inventory quantity increased by only 25 (not 100)
    async with session_factory() as session:
        slot = (await session.execute(
            select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id)
        )).scalar_one_or_none()
        assert slot.quantity == 25

        # Verify only one ledger record exists with this key
        txs = (await session.execute(
            select(InventoryTransaction).where(InventoryTransaction.idempotency_key == shared_key)
        )).scalars().all()
        assert len(txs) == 1

# -----------------------------------------------------------------
# 5. Finding TEST-02C: Conflicting Idempotency Replay
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_conflicting_inventory_idempotency_replay(inventory_concurrency_setup: dict):
    """
    Finding TEST-02C: Reuse an existing idempotency key with different request parameters.
    Verify HTTP 409 Conflict.
    Verify inventory and transaction history remain completely unchanged.
    """
    session_factory = inventory_concurrency_setup["session_factory"]
    gid = inventory_concurrency_setup["character_gid"]
    admin_id = inventory_concurrency_setup["admin_id"]
    item_id = inventory_concurrency_setup["ammo_item_id"]

    key = "conflict_key_replay"

    # 1. Initial successful grant
    async with session_factory() as session:
        service = InventoryService(InventoryRepository(session))
        tx1 = await service.grant_inventory(
            gid, admin_id,
            InventoryGrantRequest(item_id=item_id, quantity=30, idempotency_key=key, reason="Initial grant")
        )
        assert tx1.quantity_after == 30

    # 2. Conflicting replay with different quantity (50 != 30)
    async with session_factory() as session:
        service = InventoryService(InventoryRepository(session))
        with pytest.raises(HTTPException) as exc_info:
            await service.grant_inventory(
                gid, admin_id,
                InventoryGrantRequest(item_id=item_id, quantity=50, idempotency_key=key, reason="Mismatched qty")
            )
        assert exc_info.value.status_code == 409
        assert "already been used with different parameters" in exc_info.value.detail

    # 3. Conflicting replay with different operation (REMOVE instead of GRANT)
    async with session_factory() as session:
        service = InventoryService(InventoryRepository(session))
        with pytest.raises(HTTPException) as exc_info:
            await service.remove_inventory(
                gid, admin_id,
                InventoryRemoveRequest(item_id=item_id, quantity=30, idempotency_key=key, reason="Mismatched op")
            )
        assert exc_info.value.status_code == 409
        assert "already been used with different parameters" in exc_info.value.detail

    # 4. Verify inventory quantity remains exactly 30 and only 1 transaction exists
    async with session_factory() as session:
        slot = (await session.execute(
            select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id)
        )).scalar_one_or_none()
        assert slot.quantity == 30

        txs = (await session.execute(
            select(InventoryTransaction).where(InventoryTransaction.idempotency_key == key)
        )).scalars().all()
        assert len(txs) == 1

# -----------------------------------------------------------------
# 6. Finding TEST-02: Concurrent Removal Down to Zero (Slot Deletion)
# -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_removal_down_to_zero_slot_cleanup(inventory_concurrency_setup: dict):
    """
    Initial balance: 1 (non-stackable armor item).
    Two concurrent removals of 1.
    Exactly one succeeds and deletes the slot; the second fails safely.
    Slot is completely deleted; no CheckConstraint("quantity > 0") violation.
    """
    session_factory = inventory_concurrency_setup["session_factory"]
    gid = inventory_concurrency_setup["character_gid"]
    admin_id = inventory_concurrency_setup["admin_id"]
    item_id = inventory_concurrency_setup["armor_item_id"]

    # 1. Grant 1 armor
    async with session_factory() as session:
        service = InventoryService(InventoryRepository(session))
        await service.grant_inventory(
            gid, admin_id,
            InventoryGrantRequest(item_id=item_id, quantity=1, idempotency_key="armor_grant", reason="Vest loadout")
        )

    # 2. Concurrently remove 1
    async def run_remove(key: str):
        async with session_factory() as session:
            service = InventoryService(InventoryRepository(session))
            return await service.remove_inventory(
                gid, admin_id,
                InventoryRemoveRequest(item_id=item_id, quantity=1, idempotency_key=key, reason="Consume vest")
            )

    results = await asyncio.gather(
        run_remove("rem_zero_1"),
        run_remove("rem_zero_2"),
        return_exceptions=True
    )

    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1
    assert len(failures) == 1
    assert isinstance(failures[0], HTTPException)
    assert failures[0].status_code == 400

    # 3. Verify slot is completely removed from database
    async with session_factory() as session:
        slot = (await session.execute(
            select(InventoryItem).where(InventoryItem.character_gid == gid, InventoryItem.item_id == item_id)
        )).scalar_one_or_none()
        assert slot is None
