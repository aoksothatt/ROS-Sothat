-- Migration 005: Add email column and email_otps table (Phase P02: Email OTP Integration)
-- Description: Enables passwordless authentication and registration via 6-digit email OTPs.
-- Impact: Non-destructive addition of nullable column to accounts, unique index, and new email_otps table.
-- Note: Base.metadata.create_all handles table creation automatically for new/test databases.

-- =============================================================
-- SQLite Migration Syntax:
-- =============================================================

-- 1. Add email column to existing accounts table
ALTER TABLE accounts ADD COLUMN email VARCHAR(128);
CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_email ON accounts (email);

-- 2. Create email_otps table
CREATE TABLE IF NOT EXISTS email_otps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(128) NOT NULL,
    otp_hash VARCHAR(64) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    purpose VARCHAR(16) NOT NULL,
    attempts_left INTEGER NOT NULL DEFAULT 5,
    is_used BOOLEAN NOT NULL DEFAULT 0,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_email_otp_attempts_non_negative CHECK (attempts_left >= 0),
    CONSTRAINT chk_email_otp_purpose CHECK (purpose IN ('registration', 'login'))
);

CREATE INDEX IF NOT EXISTS ix_email_otps_id ON email_otps(id);
CREATE INDEX IF NOT EXISTS ix_email_otps_email ON email_otps(email);
CREATE INDEX IF NOT EXISTS ix_email_otps_expires_at ON email_otps(expires_at);
CREATE INDEX IF NOT EXISTS ix_email_otps_created_at ON email_otps(created_at);

-- =============================================================
-- SQLite Rollback Syntax:
-- =============================================================
-- DROP TABLE IF EXISTS email_otps;
-- DROP INDEX IF EXISTS ix_accounts_email;

-- =============================================================
-- PostgreSQL Migration Syntax:
-- =============================================================

-- 1. Add email column to existing accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS email VARCHAR(128) UNIQUE;
CREATE INDEX IF NOT EXISTS ix_accounts_email ON accounts (email);

-- 2. Create email_otps table
CREATE TABLE IF NOT EXISTS email_otps (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(128) NOT NULL,
    otp_hash VARCHAR(64) NOT NULL,
    salt VARCHAR(32) NOT NULL,
    purpose VARCHAR(16) NOT NULL,
    attempts_left INTEGER NOT NULL DEFAULT 5,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_email_otp_attempts_non_negative CHECK (attempts_left >= 0),
    CONSTRAINT chk_email_otp_purpose CHECK (purpose IN ('registration', 'login'))
);

CREATE INDEX IF NOT EXISTS ix_email_otps_id ON email_otps(id);
CREATE INDEX IF NOT EXISTS ix_email_otps_email ON email_otps(email);
CREATE INDEX IF NOT EXISTS ix_email_otps_expires_at ON email_otps(expires_at);
CREATE INDEX IF NOT EXISTS ix_email_otps_created_at ON email_otps(created_at);

-- =============================================================
-- PostgreSQL Rollback Syntax:
-- =============================================================
-- DROP TABLE IF EXISTS email_otps CASCADE;
-- DROP INDEX IF EXISTS ix_accounts_email;
-- ALTER TABLE accounts DROP COLUMN IF EXISTS email;
