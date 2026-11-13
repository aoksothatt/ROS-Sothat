# ROS Sothat — Rollback & Disaster Recovery Procedures
**Document ID:** `09_rollback_instructions.md`  
**System:** ROS Sothat Private Server Platform  
**Phase:** P02 (Backend Foundation & Email OTP Integration)  
**Date:** November 2026  
**Status:** VALIDATED  

---

## 1. Overview & Rollback Principles

Phase P02 was intentionally architected to be completely non-destructive and backward-compatible. Rolling back Phase P02 changes can be executed cleanly at either the database layer, the code layer, or both, without risking data corruption for pre-existing accounts, characters, diamond balances, or inventory items.

---

## 2. Database Rollback Procedures

If a database rollback is required on an existing database instance:

### 2.1 SQLite Rollback
SQLite does not natively support `DROP COLUMN` in older versions without table recreation. However, because `email` is nullable and defaults to `NULL`, leaving the column unused has zero adverse side effects. 

To completely purge Phase P02 tables and indexes in SQLite:
```sql
-- 1. Drop the OTP tracking table
DROP TABLE IF EXISTS email_otps;

-- 2. Drop the email index
DROP INDEX IF EXISTS ix_accounts_email;

-- 3. (Optional) Purge OTP-created player accounts
DELETE FROM accounts WHERE password_hash LIKE '*OTP_ONLY_%';
```

### 2.2 PostgreSQL Rollback
PostgreSQL supports transactional DDL and direct column dropping:
```sql
BEGIN;

-- 1. Drop the OTP tracking table
DROP TABLE IF EXISTS email_otps CASCADE;

-- 2. Drop the email index
DROP INDEX IF EXISTS ix_accounts_email;

-- 3. Remove the email column from accounts
ALTER TABLE accounts DROP COLUMN IF EXISTS email;

-- 4. Purge OTP-created accounts if desired
DELETE FROM accounts WHERE password_hash LIKE '*OTP_ONLY_%';

COMMIT;
```

---

## 3. Codebase Rollback Checklist

To revert the source code to the pre-P02 baseline:

1. **Delete Newly Added Phase P02 Files:**
   - Remove directory: `app/email/` (`provider.py`, `__init__.py`)
   - Remove test file: `tests/test_email_otp.py`
   - Remove migration: `migrations/005_add_email_and_otp_tables.sql`
   - Remove deliverables: `phaseP02_deliverables/`

2. **Revert Modified Files in `app/`:**
   - `app/config.py`: Remove lines under `# Email & OTP Configuration (Phase P02)`
   - `app/account/models.py`: Remove `EmailOTP` class and `email` column from `Account`
   - `app/account/repository.py`: Revert to pre-P02 baseline (remove OTP repository methods)
   - `app/account/service.py`: Remove `request_otp`, `verify_otp`, and OTP cryptographic helpers
   - `app/account/router.py`: Remove `/otp/request` and `/otp/verify` endpoints
   - `app/account/schemas.py`: Remove `OTPRequest`, `OTPResponse`, and `OTPVerifyRequest`
   - `app/account/rate_limiter.py`: Remove `rate_limit_otp_request` and `rate_limit_otp_verify`

3. **Post-Rollback Verification:**
   Execute pytest to ensure the 134 baseline tests pass cleanly:
   ```bash
   cd D:\ROS-Legacy-Analysis\ros-private-server
   pytest -v
   ```
   Confirm result: `133 passed, 1 skipped in ~100s`.
