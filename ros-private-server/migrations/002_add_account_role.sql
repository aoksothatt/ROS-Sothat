-- Migration 002: Add role column to accounts table (Phase 6.2A.1 Admin RBAC)
-- Description: Introduces role-based access control with 'player' and 'admin' roles.
-- Default: 'player'
-- Impact: Non-destructive addition of column with server-enforced default.
-- Note: Do NOT apply destructively. Base.metadata.create_all handles this automatically for in-memory and new databases.

-- SQLite Migration Syntax:
-- -------------------------------------------------------------
-- ALTER TABLE accounts ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'player';

-- PostgreSQL Migration Syntax:
-- -------------------------------------------------------------
-- ALTER TABLE accounts ADD COLUMN IF NOT EXISTS role VARCHAR(16) NOT NULL DEFAULT 'player';
