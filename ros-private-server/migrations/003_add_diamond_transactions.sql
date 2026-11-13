-- Migration 003: Add diamond_transactions table (Phase 6.2A.2 Diamond Currency Ledger)
-- Description: Introduces an append-only relational ledger for tracking diamond grants and deductions.
-- Impact: Non-destructive addition of table and indexes. Existing accounts and character balances are preserved.
-- Note: Base.metadata.create_all handles table creation automatically for new/test databases.

-- =============================================================
-- SQLite Migration Syntax:
-- =============================================================
CREATE TABLE IF NOT EXISTS diamond_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_gid INTEGER NOT NULL,
    admin_account_id INTEGER NOT NULL,
    operation_type VARCHAR(16) NOT NULL,
    amount BIGINT NOT NULL,
    balance_before BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_diamond_tx_amount_positive CHECK (amount > 0),
    CONSTRAINT chk_diamond_tx_balance_before_non_negative CHECK (balance_before >= 0),
    CONSTRAINT chk_diamond_tx_balance_after_non_negative CHECK (balance_after >= 0),
    FOREIGN KEY (character_gid) REFERENCES characters(gid),
    FOREIGN KEY (admin_account_id) REFERENCES accounts(id)
);

CREATE INDEX IF NOT EXISTS ix_diamond_transactions_id ON diamond_transactions(id);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_character_gid ON diamond_transactions(character_gid);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_admin_account_id ON diamond_transactions(admin_account_id);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_idempotency_key ON diamond_transactions(idempotency_key);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_created_at ON diamond_transactions(created_at);

-- =============================================================
-- PostgreSQL Migration Syntax:
-- =============================================================
CREATE TABLE IF NOT EXISTS diamond_transactions (
    id BIGSERIAL PRIMARY KEY,
    character_gid BIGINT NOT NULL,
    admin_account_id INTEGER NOT NULL,
    operation_type VARCHAR(16) NOT NULL,
    amount BIGINT NOT NULL,
    balance_before BIGINT NOT NULL,
    balance_after BIGINT NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    reason VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_diamond_tx_amount_positive CHECK (amount > 0),
    CONSTRAINT chk_diamond_tx_balance_before_non_negative CHECK (balance_before >= 0),
    CONSTRAINT chk_diamond_tx_balance_after_non_negative CHECK (balance_after >= 0),
    FOREIGN KEY (character_gid) REFERENCES characters(gid) ON DELETE CASCADE,
    FOREIGN KEY (admin_account_id) REFERENCES accounts(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_diamond_transactions_id ON diamond_transactions(id);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_character_gid ON diamond_transactions(character_gid);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_admin_account_id ON diamond_transactions(admin_account_id);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_idempotency_key ON diamond_transactions(idempotency_key);
CREATE INDEX IF NOT EXISTS ix_diamond_transactions_created_at ON diamond_transactions(created_at);

-- Optional PostgreSQL check constraint on characters table:
-- ALTER TABLE characters ADD CONSTRAINT chk_character_diamonds_non_negative CHECK (diamonds >= 0);

-- =============================================================
-- Rollback Instructions:
-- =============================================================
-- DROP TABLE IF EXISTS diamond_transactions;
-- (PostgreSQL only) ALTER TABLE characters DROP CONSTRAINT IF EXISTS chk_character_diamonds_non_negative;
