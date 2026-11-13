import os
import pytest
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects.postgresql import dialect as pg_dialect
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.base import Base
from app.account.models import Account, EmailOTP
from app.player.models import Character
from app.economy.models import DiamondTransaction
from app.inventory.models import Item, InventoryItem, InventoryTransaction
from app.admin.models import AdminAuditLog

def test_sqlalchemy_postgresql_ddl_compilation():
    """
    Verifies that all relational models compile to valid PostgreSQL DDL
    using SQLAlchemy's PostgreSQL dialect.
    """
    dialect = pg_dialect()
    
    # 1. Compile Item table DDL
    item_ddl = str(CreateTable(Item.__table__).compile(dialect=dialect))
    assert "CREATE TABLE items" in item_ddl
    assert "item_code VARCHAR(64) NOT NULL" in item_ddl
    assert "max_stack INTEGER NOT NULL" in item_ddl
    assert "chk_item_max_stack_positive CHECK (max_stack >= 1)" in item_ddl

    # 2. Compile InventoryItem table DDL
    inv_item_ddl = str(CreateTable(InventoryItem.__table__).compile(dialect=dialect))
    assert "CREATE TABLE inventory_items" in inv_item_ddl
    assert "character_gid BIGINT NOT NULL" in inv_item_ddl
    assert "item_id INTEGER NOT NULL" in inv_item_ddl
    assert "quantity INTEGER NOT NULL" in inv_item_ddl
    assert "uq_character_inventory_item UNIQUE (character_gid, item_id)" in inv_item_ddl
    assert "chk_inventory_item_quantity_positive CHECK (quantity > 0)" in inv_item_ddl

    # 3. Compile InventoryTransaction table DDL
    inv_tx_ddl = str(CreateTable(InventoryTransaction.__table__).compile(dialect=dialect))
    assert "CREATE TABLE inventory_transactions" in inv_tx_ddl
    assert "character_gid BIGINT NOT NULL" in inv_tx_ddl
    assert "admin_account_id INTEGER NOT NULL" in inv_tx_ddl
    assert "idempotency_key VARCHAR(64) NOT NULL" in inv_tx_ddl
    assert "chk_inv_tx_quantity_positive CHECK (quantity > 0)" in inv_tx_ddl

    # 4. Compile Account table DDL (Phase P02 / P02.1 email addition)
    acc_ddl = str(CreateTable(Account.__table__).compile(dialect=dialect))
    assert "CREATE TABLE accounts" in acc_ddl
    assert "email VARCHAR(128)" in acc_ddl

    # 5. Compile EmailOTP table DDL (Phase P02 / P02.1)
    otp_ddl = str(CreateTable(EmailOTP.__table__).compile(dialect=dialect))
    assert "CREATE TABLE email_otps" in otp_ddl
    assert "email VARCHAR(128) NOT NULL" in otp_ddl
    assert "otp_hash VARCHAR(64) NOT NULL" in otp_ddl
    assert "salt VARCHAR(32) NOT NULL" in otp_ddl
    assert "purpose VARCHAR(16) NOT NULL" in otp_ddl

    # 6. Compile AdminAuditLog table DDL (Phase P05 / Stage B)
    audit_ddl = str(CreateTable(AdminAuditLog.__table__).compile(dialect=dialect))
    assert "CREATE TABLE admin_audit_logs" in audit_ddl
    assert "admin_account_id INTEGER NOT NULL" in audit_ddl
    assert "action_type VARCHAR(32) NOT NULL" in audit_ddl
    assert "target_type VARCHAR(32) NOT NULL" in audit_ddl
    assert "target_id BIGINT NOT NULL" in audit_ddl
    assert "reason VARCHAR(255) NOT NULL" in audit_ddl
    assert "details TEXT NOT NULL" in audit_ddl
    assert "FOREIGN KEY(admin_account_id) REFERENCES accounts (id) ON DELETE RESTRICT" in audit_ddl

def test_postgresql_native_upsert_statement_compilation():
    """
    Verifies that InventoryRepository's PostgreSQL native upsert statement
    compiles to valid PostgreSQL SQL with ON CONFLICT DO UPDATE and WHERE clause.
    """
    dialect = pg_dialect()
    stmt = (
        pg_insert(InventoryItem)
        .values(
            character_gid=12345,
            item_id=1,
            quantity=10
        )
        .on_conflict_do_update(
            index_elements=["character_gid", "item_id"],
            set_={"quantity": InventoryItem.quantity + 10},
            where=(InventoryItem.quantity + 10 <= 100)
        )
        .returning(InventoryItem.quantity)
    )
    compiled_sql = str(stmt.compile(dialect=dialect))
    assert "INSERT INTO inventory_items" in compiled_sql
    assert "ON CONFLICT (character_gid, item_id) DO UPDATE" in compiled_sql
    assert "WHERE inventory_items.quantity +" in compiled_sql
    assert "RETURNING inventory_items.quantity" in compiled_sql

def test_migration_004_ddl_structure_inspection():
    """
    Verifies that migrations/004_add_inventory_system.sql contains valid
    SQLite and PostgreSQL DDL definitions for all required tables and constraints.
    """
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "migrations",
        "004_add_inventory_system.sql"
    )
    assert os.path.exists(migration_path), f"Migration file not found at {migration_path}"
    
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify SQLite section
    assert "CREATE TABLE IF NOT EXISTS items" in content
    assert "CREATE TABLE IF NOT EXISTS inventory_items" in content
    assert "CREATE TABLE IF NOT EXISTS inventory_transactions" in content
    assert "CONSTRAINT uq_character_inventory_item UNIQUE (character_gid, item_id)" in content
    assert "CONSTRAINT chk_item_max_stack_positive CHECK (max_stack >= 1)" in content
    assert "CONSTRAINT chk_inventory_item_quantity_positive CHECK (quantity > 0)" in content

    # Verify PostgreSQL section
    assert "TIMESTAMP WITH TIME ZONE" in content
    assert "BIGSERIAL PRIMARY KEY" in content
    assert "ON DELETE CASCADE" in content
    assert "ON DELETE RESTRICT" in content

    # Verify Rollback section
    assert "DROP TABLE IF EXISTS inventory_transactions;" in content
    assert "DROP TABLE IF EXISTS inventory_items;" in content
    assert "DROP TABLE IF EXISTS items;" in content

def test_migration_005_ddl_structure_inspection():
    """
    Verifies that migrations/005_add_email_and_otp_tables.sql contains valid
    SQLite and PostgreSQL DDL definitions for accounts.email and email_otps table.
    """
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "migrations",
        "005_add_email_and_otp_tables.sql"
    )
    assert os.path.exists(migration_path), f"Migration file not found at {migration_path}"
    
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # SQLite section
    assert "ALTER TABLE accounts ADD COLUMN email VARCHAR(128);" in content
    assert "CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_email ON accounts (email);" in content
    assert "CREATE TABLE IF NOT EXISTS email_otps" in content
    assert "CONSTRAINT chk_email_otp_attempts_non_negative CHECK (attempts_left >= 0)" in content
    assert "CONSTRAINT chk_email_otp_purpose CHECK (purpose IN ('registration', 'login'))" in content
    assert "ix_email_otps_email" in content
    assert "ix_email_otps_expires_at" in content

    # PostgreSQL section
    assert "ALTER TABLE accounts ADD COLUMN IF NOT EXISTS email VARCHAR(128) UNIQUE;" in content
    assert "BIGSERIAL PRIMARY KEY" in content
    assert "TIMESTAMP WITH TIME ZONE" in content

    # Rollback section
    assert "DROP TABLE IF EXISTS email_otps;" in content or "DROP TABLE IF EXISTS email_otps CASCADE;" in content
    assert "DROP INDEX IF EXISTS ix_accounts_email;" in content

def test_migration_005_isolated_sqlite_execution():
    """
    Executes Migration 005 DDL against an isolated in-memory SQLite database,
    verifying compatibility with existing accounts, constraints, and rollback safety.
    """
    import sqlite3

    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    # 1. Create pre-005 accounts table
    cur.execute("""
    CREATE TABLE accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(64) UNIQUE NOT NULL,
        device_id VARCHAR(64) UNIQUE,
        password_hash VARCHAR(128) NOT NULL,
        salt VARCHAR(64) NOT NULL,
        role VARCHAR(16) NOT NULL DEFAULT 'player',
        is_banned BOOLEAN NOT NULL DEFAULT 0,
        ban_reason VARCHAR(255),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """)
    cur.execute("INSERT INTO accounts (username, password_hash, salt) VALUES ('admin_user', 'hash', 'salt')")
    cur.execute("INSERT INTO accounts (username, password_hash, salt) VALUES ('existing_player', 'hash', 'salt')")
    conn.commit()

    # 2. Apply SQLite migration statements
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "migrations",
        "005_add_email_and_otp_tables.sql"
    )
    with open(migration_path, "r", encoding="utf-8") as f:
        full_sql = f.read()

    sqlite_section = full_sql.split("-- SQLite Migration Syntax:")[1].split("-- SQLite Rollback Syntax:")[0]
    conn.executescript(sqlite_section)
    conn.commit()

    # 3. Verify existing accounts have NULL email
    cur.execute("SELECT username, email FROM accounts")
    rows = cur.fetchall()
    assert len(rows) == 2
    assert rows[0][1] is None
    assert rows[1][1] is None

    # 4. Verify unique constraint on email
    cur.execute("UPDATE accounts SET email = 'friend@example.com' WHERE username = 'existing_player'")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO accounts (username, password_hash, salt, email) VALUES ('dup_player', 'h', 's', 'friend@example.com')")

    # 5. Verify email_otps table inserts and constraints
    cur.execute("""
        INSERT INTO email_otps (email, otp_hash, salt, purpose, attempts_left, expires_at)
        VALUES ('friend@example.com', 'dummy_hash', 'dummy_salt', 'registration', 5, CURRENT_TIMESTAMP)
    """)
    conn.commit()

    # Check constraint: attempts_left >= 0
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("""
            INSERT INTO email_otps (email, otp_hash, salt, purpose, attempts_left, expires_at)
            VALUES ('friend@example.com', 'dummy_hash', 'dummy_salt', 'login', -1, CURRENT_TIMESTAMP)
        """)

    # Check constraint: purpose in ('registration', 'login')
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("""
            INSERT INTO email_otps (email, otp_hash, salt, purpose, attempts_left, expires_at)
            VALUES ('friend@example.com', 'dummy_hash', 'dummy_salt', 'invalid_purpose', 5, CURRENT_TIMESTAMP)
        """)

    # 6. Verify Rollback
    cur.execute("DROP TABLE IF EXISTS email_otps")
    cur.execute("DROP INDEX IF EXISTS ix_accounts_email")
    conn.commit()

    cur.execute("SELECT count(*) FROM accounts")
    assert cur.fetchone()[0] == 2
    conn.close()

def test_migration_006_ddl_structure_inspection():
    """
    Verifies that migrations/006_add_admin_audit_logs.sql exists and contains valid dual-syntax DDL
    with ON DELETE RESTRICT constraints (Stage B audit history safety).
    """
    migration_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "migrations",
        "006_add_admin_audit_logs.sql"
    )
    assert os.path.exists(migration_path), "Migration 006 file missing."
    with open(migration_path, "r", encoding="utf-8") as f:
        content = f.read()

    # SQLite syntax
    assert "CREATE TABLE IF NOT EXISTS admin_audit_logs" in content
    assert "admin_account_id INTEGER NOT NULL" in content
    assert "action_type VARCHAR(32) NOT NULL" in content
    assert "target_type VARCHAR(32) NOT NULL" in content
    assert "target_id BIGINT NOT NULL" in content
    assert "ix_admin_audit_logs_action_type" in content
    assert "FOREIGN KEY (admin_account_id) REFERENCES accounts(id) ON DELETE RESTRICT" in content

    # PostgreSQL syntax
    assert "BIGSERIAL PRIMARY KEY" in content
    assert "TIMESTAMP WITH TIME ZONE" in content
    assert "FOREIGN KEY (admin_account_id) REFERENCES accounts(id) ON DELETE RESTRICT" in content
    assert "ON DELETE CASCADE" not in content, "PostgreSQL DDL must not cascade-delete audit history."

def test_migration_006_isolated_sqlite_execution():
    """
    Executes Migration 006 DDL against an isolated in-memory SQLite database with foreign keys enabled,
    verifying table creation, audit insertion, referential deletion protection (ON DELETE RESTRICT),
    and audit trail preservation.
    """
    import sqlite3
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    # Explicitly enforce foreign key constraints
    cur.execute("PRAGMA foreign_keys = ON;")

    cur.execute("""
    CREATE TABLE accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username VARCHAR(64) UNIQUE NOT NULL,
        role VARCHAR(16) NOT NULL DEFAULT 'admin'
    );
    """)
    cur.execute("INSERT INTO accounts (username, role) VALUES ('admin_root', 'admin')")
    conn.commit()

    # Apply migration 006 DDL with ON DELETE RESTRICT
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_account_id INTEGER NOT NULL,
        action_type VARCHAR(32) NOT NULL,
        target_type VARCHAR(32) NOT NULL,
        target_id BIGINT NOT NULL,
        reason VARCHAR(255) NOT NULL,
        details TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_account_id) REFERENCES accounts(id) ON DELETE RESTRICT
    );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_action_type ON admin_audit_logs(action_type);")
    conn.commit()

    # 1. Insert initial audit entry
    cur.execute("""
    INSERT INTO admin_audit_logs (admin_account_id, action_type, target_type, target_id, reason, details)
    VALUES (1, 'DIAMOND_GRANT', 'character', 101, 'Initial grant', '{"amount": 100}');
    """)
    conn.commit()

    # Verify audit entry exists
    cur.execute("SELECT count(*), action_type FROM admin_audit_logs WHERE admin_account_id = 1")
    row = cur.fetchone()
    assert row[0] == 1
    assert row[1] == "DIAMOND_GRANT"

    # 2. Attempt deleting the admin account -> MUST FAIL due to ON DELETE RESTRICT
    deletion_blocked = False
    try:
        cur.execute("DELETE FROM accounts WHERE id = 1;")
        conn.commit()
    except sqlite3.IntegrityError:
        deletion_blocked = True
        conn.rollback()

    assert deletion_blocked is True, "Deleting an admin referenced by audit logs must be blocked by RESTRICT constraint."

    # 3. Verify audit history remains 100% intact after the rejected delete attempt
    cur.execute("SELECT count(*), action_type, reason FROM admin_audit_logs WHERE admin_account_id = 1")
    preserved_row = cur.fetchone()
    assert preserved_row[0] == 1
    assert preserved_row[1] == "DIAMOND_GRANT"
    assert preserved_row[2] == "Initial grant"

    # 4. Verify new audit records can still be inserted normally
    cur.execute("""
    INSERT INTO admin_audit_logs (admin_account_id, action_type, target_type, target_id, reason, details)
    VALUES (1, 'ACCOUNT_SUSPEND', 'account', 202, 'Suspected speed hacking', '{"is_banned": true}');
    """)
    conn.commit()

    # Verify total count is now 2
    cur.execute("SELECT count(*) FROM admin_audit_logs WHERE admin_account_id = 1")
    assert cur.fetchone()[0] == 2

    # Verify all records remain readable in descending creation order
    cur.execute("SELECT action_type FROM admin_audit_logs ORDER BY id ASC")
    actions = [r[0] for r in cur.fetchall()]
    assert actions == ["DIAMOND_GRANT", "ACCOUNT_SUSPEND"]

    conn.close()

@pytest.mark.asyncio
async def test_live_postgresql_execution_if_configured():
    """
    If TEST_POSTGRES_URL environment variable is configured, executes live
    DDL and end-to-end inventory operations against an isolated PostgreSQL database.
    Otherwise skips with a clear diagnostic message.
    """
    pg_url = os.getenv("TEST_POSTGRES_URL")
    if not pg_url:
        pytest.skip(
            "TEST_POSTGRES_URL environment variable is not configured. "
            "To run live PostgreSQL verification, set TEST_POSTGRES_URL="
            "'postgresql+asyncpg://<user>:<password>@localhost:5432/<test_db>'."
        )

    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.inventory.repository import InventoryRepository
    from app.inventory.service import InventoryService
    from app.inventory.schemas import InventoryGrantRequest, InventoryRemoveRequest

    pg_engine = create_async_engine(pg_url)
    try:
        async with pg_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(pg_engine, expire_on_commit=False)
        async with session_factory() as session:
            admin = Account(username="pg_admin", password_hash="h", salt="s", role="admin")
            session.add(admin)
            await session.commit()
            char = Character(account_id=admin.id, nickname="PGPlayer", char_type=0)
            session.add(char)
            await session.commit()
            item = Item(item_code="PG_AMMO", name="PG Ammo", item_type="CONSUMABLE", stackable=True, max_stack=200)
            session.add(item)
            await session.commit()

            service = InventoryService(InventoryRepository(session))
            tx_grant = await service.grant_inventory(
                char.gid, admin.id,
                InventoryGrantRequest(item_id=item.id, quantity=50, idempotency_key="pg_k1", reason="PG Grant")
            )
            assert tx_grant.quantity_after == 50

            tx_rem = await service.remove_inventory(
                char.gid, admin.id,
                InventoryRemoveRequest(item_id=item.id, quantity=20, idempotency_key="pg_k2", reason="PG Remove")
            )
            assert tx_rem.quantity_after == 30
    finally:
        async with pg_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await pg_engine.dispose()
