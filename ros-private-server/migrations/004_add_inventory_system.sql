-- Migration 004: Add relational item catalog and player inventory system (Phase 6.2A.3)
-- Description: Introduces relational catalog (items), character inventory slots (inventory_items),
--              and an append-only audit ledger (inventory_transactions).
-- Impact: Non-destructive addition of tables and indexes. Existing accounts, characters, and
--         character appearances JSON data are completely preserved.
-- Note: Base.metadata.create_all handles table creation automatically for new/test databases.

-- =============================================================
-- SQLite Migration Syntax:
-- =============================================================
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    description VARCHAR(512) NOT NULL DEFAULT '',
    item_type VARCHAR(32) NOT NULL,
    icon VARCHAR(255),
    stackable BOOLEAN NOT NULL DEFAULT 0,
    max_stack INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_item_max_stack_positive CHECK (max_stack >= 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_items_item_code ON items(item_code);
CREATE INDEX IF NOT EXISTS ix_items_item_type ON items(item_type);
CREATE INDEX IF NOT EXISTS ix_items_is_active ON items(is_active);

CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_gid INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_character_inventory_item UNIQUE (character_gid, item_id),
    CONSTRAINT chk_inventory_item_quantity_positive CHECK (quantity > 0),
    FOREIGN KEY (character_gid) REFERENCES characters(gid),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE INDEX IF NOT EXISTS ix_inventory_items_character_gid ON inventory_items(character_gid);
CREATE INDEX IF NOT EXISTS ix_inventory_items_item_id ON inventory_items(item_id);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_gid INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    admin_account_id INTEGER NOT NULL,
    operation_type VARCHAR(16) NOT NULL,
    quantity INTEGER NOT NULL,
    quantity_before INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inv_tx_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_inv_tx_quantity_before_non_negative CHECK (quantity_before >= 0),
    CONSTRAINT chk_inv_tx_quantity_after_non_negative CHECK (quantity_after >= 0),
    FOREIGN KEY (character_gid) REFERENCES characters(gid),
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (admin_account_id) REFERENCES accounts(id)
);

CREATE INDEX IF NOT EXISTS ix_inventory_transactions_character_gid ON inventory_transactions(character_gid);
CREATE INDEX IF NOT EXISTS ix_inventory_transactions_item_id ON inventory_transactions(item_id);
CREATE INDEX IF NOT EXISTS ix_inventory_transactions_admin_account_id ON inventory_transactions(admin_account_id);
CREATE INDEX IF NOT EXISTS ix_inventory_transactions_created_at ON inventory_transactions(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_inventory_transactions_idempotency_key ON inventory_transactions(idempotency_key);

-- =============================================================
-- PostgreSQL Migration Syntax:
-- =============================================================
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    item_code VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    description VARCHAR(512) NOT NULL DEFAULT '',
    item_type VARCHAR(32) NOT NULL,
    icon VARCHAR(255),
    stackable BOOLEAN NOT NULL DEFAULT FALSE,
    max_stack INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_item_max_stack_positive CHECK (max_stack >= 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_items_item_code ON items(item_code);
CREATE INDEX IF NOT EXISTS ix_items_item_type ON items(item_type);
CREATE INDEX IF NOT EXISTS ix_items_is_active ON items(is_active);

CREATE TABLE IF NOT EXISTS inventory_items (
    id BIGSERIAL PRIMARY KEY,
    character_gid BIGINT NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_character_inventory_item UNIQUE (character_gid, item_id),
    CONSTRAINT chk_inventory_item_quantity_positive CHECK (quantity > 0),
    FOREIGN KEY (character_gid) REFERENCES characters(gid) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_inventory_items_character_gid ON inventory_items(character_gid);
CREATE INDEX IF NOT EXISTS ix_inventory_items_item_id ON inventory_items(item_id);

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id BIGSERIAL PRIMARY KEY,
    character_gid BIGINT NOT NULL,
    item_id INTEGER NOT NULL,
    admin_account_id INTEGER NOT NULL,
    operation_type VARCHAR(16) NOT NULL,
    quantity INTEGER NOT NULL,
    quantity_before INTEGER NOT NULL,
    quantity_after INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_inv_tx_quantity_positive CHECK (quantity > 0),
    CONSTRAINT chk_inv_tx_quantity_before_non_negative CHECK (quantity_before >= 0),
    CONSTRAINT chk_inv_tx_quantity_after_non_negative CHECK (quantity_after >= 0),
    FOREIGN KEY (character_gid) REFERENCES characters(gid) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE RESTRICT,
    FOREIGN KEY (admin_account_id) REFERENCES accounts(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_inventory_transactions_character_gid ON inventory_transactions(character_gid);
CREATE INDEX IF NOT EXISTS ix_inventory_transactions_item_id ON inventory_transactions(item_id);
CREATE INDEX IF NOT EXISTS ix_inventory_transactions_admin_account_id ON inventory_transactions(admin_account_id);
CREATE INDEX IF NOT EXISTS ix_inventory_transactions_created_at ON inventory_transactions(created_at);
CREATE UNIQUE INDEX IF NOT EXISTS ix_inventory_transactions_idempotency_key ON inventory_transactions(idempotency_key);

-- =============================================================
-- Rollback Instructions:
-- =============================================================
-- DROP TABLE IF EXISTS inventory_transactions;
-- DROP TABLE IF EXISTS inventory_items;
-- DROP TABLE IF EXISTS items;
