# ROS Sothat — Phase 6.2A.2: Diamond Currency Ledger & Transaction Engine Report

**Date:** November 11, 2026  
**Status:** COMPLETED & VERIFIED  
**Test Suite Status:** 109 / 109 passing (100% success rate in 7.35s)  
**Governing Strategy:** Option A (Independent Private-Server Architecture; 100% Unmodified Original iOS Client IPA)

---

## 1. Executive Summary

Phase 6.2A.2 establishes the core economy foundation for the ROS Sothat independent private server backend. An append-only relational ledger model (`DiamondTransaction`) and an atomic transaction engine have been implemented. The ledger guarantees auditability, double-entry consistency, overdraft prevention, idempotency deduplication, and strict role-based access control (Admin only).

All 93 prior baseline tests remain 100% passing. 16 new automated tests in `tests/test_diamond_ledger.py` thoroughly validate atomic grants, atomic deductions, overdraft rejection, idempotency key replay and conflict detection, schema validation, role security, query pagination, and mathematical reconciliation between ledger records and character balances.

---

## 2. Strict Project Rules Adherence

| Rule | Status | Audit Verification |
| :--- | :---: | :--- |
| **Original IPA Untouched** | **PASS** | No client files, Mach-O binaries, or assets were touched or inspected during this phase. |
| **No Compatibility Claims** | **PASS** | Server APIs are developed and tested as an independent clean-room backend using synthetic test clients. |
| **No Production DB Modifications** | **PASS** | Tests run on isolated in-memory SQLite fixtures (`StaticPool`). No production migrations executed. |
| **Zero Plaintext Secrets** | **PASS** | Authorization relies on standard secure JWT bearer tokens; no secrets or tokens committed. |
| **Non-Destructive Schema** | **PASS** | Existing `Character` default diamond balance (100) and columns are completely preserved. |

---

## 3. Relational Ledger Architecture

### 3.1 Data Model: `DiamondTransaction`

The table `diamond_transactions` records every currency mutation as an immutable ledger entry.

| Column | Type | Constraints / Attributes | Description |
| :--- | :--- | :--- | :--- |
| `id` | `BigInteger / Integer` | Primary Key, Autoincrement, Index | Unique monotonic transaction identifier. |
| `character_gid` | `BigInteger / Integer` | Foreign Key (`characters.gid`), Indexed, Not Null | Target character receiving or spending diamonds. |
| `admin_account_id` | `Integer` | Foreign Key (`accounts.id`), Indexed, Not Null | Admin operator account responsible for the action. |
| `operation_type` | `String(16)` | `VARCHAR(16)`, Not Null | Mutation type: `'GRANT'` or `'DEDUCT'`. |
| `amount` | `BigInteger` | `> 0`, Not Null | Positive integer transaction magnitude. |
| `balance_before` | `BigInteger` | `>= 0`, Not Null | Snapshot of character diamonds prior to mutation. |
| `balance_after` | `BigInteger` | `>= 0`, Not Null | Snapshot of character diamonds immediately following mutation. |
| `idempotency_key` | `String(64)` | `UNIQUE`, Indexed, Not Null | Caller-supplied UUID or unique string to prevent replay/duplicate grants. |
| `reason` | `String(255)` | `VARCHAR(255)`, Not Null | Audit justification (e.g. event rewards, moderation adjustments). |
| `created_at` | `DateTime` | Indexed, Not Null, Default `utcnow` | Server-side UTC creation timestamp. |

### 3.2 Database-Level Defense-in-Depth Constraints

- `chk_diamond_tx_amount_positive`: `amount > 0`
- `chk_diamond_tx_balance_before_non_negative`: `balance_before >= 0`
- `chk_diamond_tx_balance_after_non_negative`: `balance_after >= 0`
- `chk_character_diamonds_non_negative`: `diamonds >= 0` on `characters` table

These check constraints ensure that neither application bugs nor direct database modifications can force a character or ledger entry into a negative diamond balance.

---

## 4. Endpoint Specifications & Authorization

All diamond endpoints are located under the API v1 admin route prefix (`/api/v1/admin/characters/{gid}/diamonds/...`) and protected by the `Depends(get_current_admin)` RBAC dependency.

```
                              ┌─────────────────────────────────────────┐
                              │  Client Request (Admin Bearer Token)    │
                              └────────────────────┬────────────────────┘
                                                   │
                                      [RBAC Authorization Check]
                                 401 if unauth / 403 if player or banned
                                                   │
                                                   ▼
                                      [Idempotency Key Check]
                                                   │
                        ┌──────────────────────────┴──────────────────────────┐
                        │ Key Exists                                          │ Key New
                        ▼                                                     ▼
         ┌──────────────────────────────┐                      ┌──────────────────────────────┐
         │ Check parameter match:       │                      │ Fetch Character (Lock row)   │
         │ - Matching: Return 200 OK    │                      │ - Insufficient funds -> 400  │
         │ - Mismatch: Return 409 Conf. │                      │ - Calculate new balance      │
         └──────────────────────────────┘                      │ - Mutate character balance   │
                                                               │ - Insert DiamondTransaction  │
                                                               │ - Single Atomic Commit       │
                                                               └──────────────┬───────────────┘
                                                                              │
                                                                              ▼
                                                                       200 OK + Ledger Record
```

### 4.1 Endpoints Implemented

1. **`POST /api/v1/admin/characters/{gid}/diamonds/grant`**
   - **Request Body:**
     - `amount`: Positive integer (`1 <= amount <= 100,000,000`).
     - `idempotency_key`: Non-empty string (`1 <= len <= 64`).
     - `reason`: Audit reason string (`1 <= len <= 255`).
   - **Behavior:**
     - Checks idempotency table.
     - Adds `amount` to character diamonds.
     - Appends `GRANT` transaction row.
     - Commits atomically.
   - **Response:** HTTP 200 OK (`DiamondTransactionOut`).

2. **`POST /api/v1/admin/characters/{gid}/diamonds/deduct`**
   - **Request Body:**
     - `amount`: Positive integer (`1 <= amount <= 100,000,000`).
     - `idempotency_key`: Non-empty string (`1 <= len <= 64`).
     - `reason`: Audit reason string (`1 <= len <= 255`).
   - **Behavior:**
     - Checks idempotency table.
     - Verifies `character.diamonds >= amount`. If insufficient, raises HTTP 400 Bad Request with details.
     - Subtracts `amount` from character diamonds.
     - Appends `DEDUCT` transaction row.
     - Commits atomically.
   - **Response:** HTTP 200 OK (`DiamondTransactionOut`).

3. **`GET /api/v1/admin/characters/{gid}/diamonds/history`**
   - **Query Parameters:**
     - `limit`: Integer (`1 <= limit <= 100`, default 50).
     - `offset`: Integer (`>= 0`, default 0).
   - **Behavior:**
     - Verifies character exists (HTTP 404 if not found).
     - Returns current character diamond balance, total transaction count, and list of transactions ordered newest-first (`id DESC`).
   - **Response:** HTTP 200 OK (`DiamondHistoryResponse`).

---

## 5. Non-Destructive Migration Strategy

The migration script [`migrations/003_add_diamond_transactions.sql`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/migrations/003_add_diamond_transactions.sql) has been created.

- **SQLite & PostgreSQL DDL**:
  - `CREATE TABLE IF NOT EXISTS diamond_transactions (...)`
  - High-performance indexes on `character_gid`, `admin_account_id`, `idempotency_key`, and `created_at`.
  - Non-destructive: Existing `accounts` and `characters` tables are completely unaffected.
- **Rollback Instructions**: Documented in comments (`DROP TABLE IF EXISTS diamond_transactions;`).

---

## 6. Automated Verification & Test Results

The test suite was executed across all components using `pytest`:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server
configfile: pytest.ini
plugins: anyio-4.16.0, platformdirs-4.13.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 109 items

tests\test_account.py ....                                               [  3%]
tests\test_admin_bootstrap_cli.py ..........                             [ 12%]
tests\test_admin_rbac.py ...........                                     [ 22%]
tests\test_diamond_ledger.py ................                            [ 37%]
tests\test_discovery.py ..............                                   [ 50%]
tests\test_gateway_adapter.py .....                                      [ 55%]
tests\test_handshake.py ......                                           [ 60%]
tests\test_lobby.py ..                                                   [ 62%]
tests\test_matchmaking.py ..                                             [ 64%]
tests\test_mercury_protocol.py ................                          [ 78%]
tests\test_mercury_transport.py .......                                  [ 85%]
tests\test_player.py ...                                                 [ 88%]
tests\test_remediation.py ............                                   [ 99%]
tests\test_room.py .                                                     [100%]

============================= 109 passed in 7.35s =============================
```

### 6.1 Test Breakdown for `test_diamond_ledger.py` (16 Tests)

1. `test_admin_grant_diamonds_success`: Admin successfully grants diamonds, updating balance from 100 to 600 and writing ledger row.
2. `test_admin_deduct_diamonds_success`: Admin successfully deducts diamonds within available balance (100 to 55).
3. `test_deduct_exact_balance_to_zero`: Deducts exact current balance down to 0 diamonds cleanly.
4. `test_deduct_insufficient_balance_rejected`: Rejects overdraft deduction with HTTP 400; leaves balance untouched.
5. `test_idempotency_exact_replay`: Replays identical transaction payload; returns existing transaction without double-crediting.
6. `test_idempotency_conflict_on_mismatched_amount`: Detects idempotency key reuse with different amount; returns HTTP 409 Conflict.
7. `test_idempotency_conflict_on_mismatched_operation_type`: Detects idempotency key reuse with different operation (`GRANT` vs `DEDUCT`); returns HTTP 409 Conflict.
8. `test_idempotency_conflict_on_different_character`: Detects idempotency key reuse across different characters; returns HTTP 409 Conflict.
9. `test_amount_validation_rules`: Rejects non-positive (0), negative (-50), excessive (> 100M), or empty idempotency keys with HTTP 422.
10. `test_character_not_found_handling`: Validates HTTP 404 for non-existent character GID on grant, deduct, and history.
11. `test_rbac_authorization_enforced`: Validates HTTP 401 for unauthenticated calls and HTTP 403 for ordinary player tokens.
12. `test_banned_admin_rejected`: Validates HTTP 403 when a banned admin attempts any economy action.
13. `test_diamond_history_ordering_and_pagination`: Validates newest-first sorting and limit/offset pagination on transaction history.
14. `test_ledger_sum_matches_character_balance`: Validates that mathematical sum of all ledger operations matches the character's exact database balance.
15. `test_database_check_constraint_rejects_negative_character_diamonds`: Validates database-level check constraint rejecting negative balances.
16. `test_database_check_constraint_rejects_non_positive_transaction_amount`: Validates database-level check constraint rejecting non-positive transaction amounts.

---

## 7. Modified and Created Files

- `app/economy/__init__.py` *(Created)*
- `app/economy/models.py` *(Created)*: `DiamondTransaction` ORM model with check constraints.
- `app/economy/schemas.py` *(Created)*: Pydantic v2 schemas and validation bounds.
- `app/economy/repository.py` *(Created)*: Database repository with character locking support and query pagination.
- `app/economy/service.py` *(Created)*: Economy transaction service with idempotency conflict checks and atomic commits.
- `app/player/models.py` *(Modified)*: Added `chk_character_diamonds_non_negative` check constraint and `diamond_transactions` relationship.
- `app/database/session.py` *(Modified)*: Registered `app.economy.models` in `init_db()`.
- `tests/conftest.py` *(Modified)*: Registered `app.economy.models` in test fixtures.
- `app/admin/router.py` *(Modified)*: Added `/characters/{gid}/diamonds/grant`, `/characters/{gid}/diamonds/deduct`, and `/characters/{gid}/diamonds/history` routes.
- `migrations/003_add_diamond_transactions.sql` *(Created)*: Non-destructive migration script for SQLite and PostgreSQL.
- `tests/test_diamond_ledger.py` *(Created)*: 16 test cases covering all requirements.

---

## 8. Next Steps & Approval Gate

Phase 6.2A.2 is complete and verified.

The next milestone on the Phase 6.2A roadmap is:
- **Phase 6.2A.3: Item Catalog and Player Inventory Management**
  - Item catalog repository (weapons, clothing, consumables).
  - Player inventory model and purchase/unlock transactions linked to character diamond balances.
  - Verification with automated synthetic client tests.

Awaiting user approval before proceeding to Phase 6.2A.3.
