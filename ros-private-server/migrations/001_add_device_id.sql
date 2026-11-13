-- Migration 001: Add device_id to accounts table (SEC-02 Remediation)
-- Description: Enables guest account persistence across client reconnects by hardware device ID.
-- Impact: Non-destructive addition of nullable column and unique index.
-- Note: Do NOT apply destructively. For new installations, Base.metadata.create_all handles this automatically.

-- SQLite Migration Syntax:
-- -------------------------------------------------------------
-- ALTER TABLE accounts ADD COLUMN device_id VARCHAR(64);
-- CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_device_id ON accounts (device_id);

-- PostgreSQL Migration Syntax:
-- -------------------------------------------------------------
-- ALTER TABLE accounts ADD COLUMN IF NOT EXISTS device_id VARCHAR(64) UNIQUE;
-- CREATE INDEX IF NOT EXISTS ix_accounts_device_id ON accounts (device_id);
