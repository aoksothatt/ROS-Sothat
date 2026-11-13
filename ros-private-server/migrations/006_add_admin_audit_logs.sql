-- Migration 006: Add admin_audit_logs table (Phase P05 Secure Admin Dashboard)
-- Description: Introduces a persistent, append-only administrative audit log for tracking
-- sensitive actions: diamond grants/deductions, inventory modifications, account bans/unbans, and role changes.
-- Impact: Non-destructive addition of table and indexes. Existing accounts, characters, and transactions are preserved.
-- Note: Base.metadata.create_all handles table creation automatically for new/test databases.

-- =============================================================
-- SQLite Migration Syntax:
-- =============================================================
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

CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_id ON admin_audit_logs(id);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_admin_account_id ON admin_audit_logs(admin_account_id);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_action_type ON admin_audit_logs(action_type);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_target_id ON admin_audit_logs(target_id);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_created_at ON admin_audit_logs(created_at);

-- =============================================================
-- PostgreSQL Migration Syntax:
-- =============================================================
CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    admin_account_id INTEGER NOT NULL,
    action_type VARCHAR(32) NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    target_id BIGINT NOT NULL,
    reason VARCHAR(255) NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_account_id) REFERENCES accounts(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_id ON admin_audit_logs(id);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_admin_account_id ON admin_audit_logs(admin_account_id);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_action_type ON admin_audit_logs(action_type);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_target_id ON admin_audit_logs(target_id);
CREATE INDEX IF NOT EXISTS ix_admin_audit_logs_created_at ON admin_audit_logs(created_at);
