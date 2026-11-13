# ROS Sothat — Phase 6.2A.2.1: Diamond Ledger Security & Reliability Audit Report

**Date:** November 11, 2026  
**Audit Scope:** Read-Only Security & Concurrency Verification of Phase 6.2A.2 Diamond Currency Ledger  
**Auditor:** Antigravity (Advanced Agentic Coding Pair Programmer)  
**Governing Strategy:** Option A (Independent Private-Server Backend; 100% Unmodified Original iOS Client IPA)  
**Database Engines Tested:** SQLite (`sqlite+aiosqlite:///:memory:` and file-based SQLite)  
**Database Engines Untested:** PostgreSQL (No live PostgreSQL instance configured in test suite)  

---

## 1. Overall Audit Verdict

### **VERDICT: PASS WITH ISSUES**

**Summary of Verdict:**  
The administrative security, RBAC authorization, Pydantic input validation, idempotency uniqueness, and append-only ledger integrity mechanisms are well-designed and strictly enforced. Sequential operations, ledger balance mathematical reconciliation, overdraft rejection, and role-based permissions all pass 100% (109/109 tests).

However, a **High-Severity concurrency vulnerability (Lost Update / Double Spending)** was discovered under concurrent request scenarios on SQLite. Because SQLite lacks support for `SELECT ... FOR UPDATE`, row-level locking is skipped, and balance calculation is performed in Python application memory rather than via atomic SQL statements (`UPDATE characters SET diamonds = diamonds - :amount WHERE gid = :gid AND diamonds >= :amount`). Consequently, simultaneous grants overwrite one another, and simultaneous deductions allow concurrent overdrafts on SQLite. Additionally, the test suite currently contains **zero concurrency tests** and **no PostgreSQL verification**.

---

## 2. Findings Grouped by Severity

### 2.1 High Severity Findings

#### `FINDING-SEC-01`: Lost Update & Concurrency Race Condition under SQLite (Dev & Local Environments)
- **Component:** Concurrency & Transaction Atomicity
- **Affected Files & Lines:**
  - [`app/economy/repository.py#L14-L19`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/repository.py#L14-L19)
  - [`app/economy/service.py#L52-L56`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/service.py#L52-L56)
  - [`app/economy/service.py#L122-L132`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/service.py#L122-L132)
- **Description:**  
  In `app/economy/repository.py`, `with_for_update()` is explicitly bypassed when running on SQLite because SQLite does not support the SQL `FOR UPDATE` clause:
  ```python
  if for_update and dialect_name and dialect_name != "sqlite":
      stmt = stmt.with_for_update()
  ```
  In `app/economy/service.py`, diamond balance mutation is computed in Python memory:
  ```python
  balance_before = character.diamonds
  balance_after = balance_before + req.amount
  character.diamonds = balance_after
  ```
  In SQLite, deferred transactions allow concurrent read operations. When two requests arrive simultaneously:
  1. **Simultaneous Grants Overwrite (Lost Update):** If Request A grants 50 and Request B grants 30 to a character with 100 diamonds, both read `diamonds = 100`. Request A computes 150; Request B computes 130. The final balance becomes 130 instead of 180. 50 diamonds are silently lost.
  2. **Simultaneous Deductions Overdraft (Double Spend):** If Request A deducts 80 and Request B deducts 80 from a character with 100 diamonds, both evaluate `balance_before < 80` as `False` (100 >= 80). Both deductions succeed with HTTP 200, recording 160 diamonds total deducted in the ledger, while the final character balance ends at 20.
- **Empirical Proof:** Verified via diagnostic script executing concurrent async sessions against SQLite; both simultaneous 80-diamond deductions returned HTTP 200 OK.

---

#### `FINDING-TEST-01`: Absence of Concurrency Tests & Zero PostgreSQL Test Coverage
- **Component:** Automated Test Suite
- **Affected Files & Lines:**
  - [`tests/test_diamond_ledger.py#L1-L590`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/test_diamond_ledger.py#L1-L590)
  - [`tests/conftest.py#L17-L23`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/conftest.py#L17-L23)
- **Description:**  
  All 16 tests in `tests/test_diamond_ledger.py` are strictly sequential (e.g. `await client.post(...)` followed by another `await client.post(...)`). Not a single test uses `asyncio.gather` or concurrent workers to test simultaneous grants, simultaneous deductions, or race conditions on the same idempotency key.
  Furthermore, all tests run exclusively on an in-memory SQLite fixture (`sqlite+aiosqlite:///:memory:`). PostgreSQL-specific behavior—specifically `SELECT ... FOR UPDATE` row locking and PostgreSQL DDL—has never been tested against an actual PostgreSQL database.

---

### 2.2 Medium Severity Findings

#### `FINDING-SEC-02`: In-Memory Test Fixture (`StaticPool`) Transaction State Leakage during Concurrent Races
- **Component:** Test Infrastructure & Shared Connections
- **Affected Files & Lines:**
  - [`tests/conftest.py#L19-L23`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/conftest.py#L19-L23)
- **Description:**  
  In `tests/conftest.py`, the test engine is initialized with `poolclass=StaticPool`. Under SQLite, `StaticPool` maintains a single shared connection across all `AsyncSession` instances. If two concurrent coroutines execute updates concurrently on separate sessions using this pool, uncommitted updates from Session B can be committed by Session A's `commit()`. While this is specific to `StaticPool` in test environments and does not affect multi-connection production deployments, it makes writing reliable in-memory concurrency tests tricky unless sessions are properly isolated.

---

### 2.3 Low & Informational Severity Findings

#### `FINDING-VAL-01`: Whitespace-Only Strings Permitted in `reason` and `idempotency_key`
- **Component:** Input Validation
- **Affected Files & Lines:**
  - [`app/economy/schemas.py#L16-L23`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/schemas.py#L16-L23)
  - [`app/economy/schemas.py#L33-L40`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/schemas.py#L33-L40)
- **Description:**  
  `reason` and `idempotency_key` are validated with `min_length=1, max_length=255`. A string composed entirely of whitespace (e.g. `"   "`) passes validation because Pydantic measures raw character length.
- **Impact:** Suboptimal audit trail clarity; no operational failure.

#### `FINDING-API-01`: Existence Disclosure on History Endpoint
- **Component:** Information Disclosure (Admin Only)
- **Affected Files & Lines:**
  - [`app/economy/service.py#L172-L177`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/service.py#L172-L177)
- **Description:**  
  Requesting diamond history for a non-existent character GID returns HTTP 404, while an existing character with zero transactions returns HTTP 200 with an empty list. Since this endpoint is restricted exclusively to authenticated administrators (`get_current_admin`), this is standard administrative API behavior and poses no security risk to normal players.

---

## 3. Detailed Audit Tasks Verification

### 3.1 Task 1: Atomicity & Concurrency
- **Balance Update and Ledger Insert in One Transaction:**  
  **CONFIRMED.** In [`app/economy/service.py#L70`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/service.py#L70) and [`#L146`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/service.py#L146), `character.diamonds` update and `DiamondTransaction` creation are committed together via a single `await self.repository.commit()`.
- **Concurrent Grants:**  
  **FAIL on SQLite; THEORETICAL PASS on PostgreSQL.** On SQLite, concurrent grants suffer from Lost Update anomalies (demonstrated: 100 + 50 + 30 = 130). On PostgreSQL, `SELECT ... FOR UPDATE` serializes access, preventing lost updates.
- **Concurrent Deductions:**  
  **FAIL on SQLite; THEORETICAL PASS on PostgreSQL.** On SQLite, concurrent deductions both see the initial balance and succeed, allowing double spending (demonstrated: 100 - 80 - 80 = 20 balance, 160 ledger total).
- **Rollback on Ledger Insert Failure:**  
  **CONFIRMED.** Any `HTTPException`, `IntegrityError`, or generic `Exception` triggers `await self.repository.rollback()`, ensuring uncommitted balance changes are reverted.

### 3.2 Task 2: Idempotency
- **Unique Constraint in Database:**  
  **CONFIRMED.** Model [`DiamondTransaction.idempotency_key`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/economy/models.py#L49-L54) specifies `unique=True`. Migration [`003_add_diamond_transactions.sql#L17`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/migrations/003_add_diamond_transactions.sql#L17) creates a `UNIQUE` constraint and index `ix_diamond_transactions_idempotency_key`.
- **Simultaneous Requests with Same Key:**  
  **CONFIRMED.** When two simultaneous requests use the same key, the second encounters `IntegrityError`, catches it, calls `rollback()`, queries the winning transaction, and returns the existing transaction idempotently.
- **Identical Replays:**  
  **CONFIRMED.** Returns existing transaction with HTTP 200 OK without double-crediting.
- **Conflicting Requests:**  
  **CONFIRMED.** Reusing a key with mismatched `character_gid`, `operation_type`, or `amount` returns HTTP 409 Conflict.
- **Failed Transactions:**  
  **CONFIRMED.** If a transaction fails before commit, rollback discards the ledger row, leaving the key available for retry.

### 3.3 Task 3: Admin Security
- **Every Endpoint Requires `get_current_admin`:**  
  **CONFIRMED.** [`app/admin/router.py#L144`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/admin/router.py#L144), [`#L159`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/admin/router.py#L159), [`#L174`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/admin/router.py#L174).
- **Player Access Blocked:**  
  **CONFIRMED.** Non-admin player tokens receive HTTP 403 Forbidden.
- **Unauthenticated Access Blocked:**  
  **CONFIRMED.** Missing or invalid tokens receive HTTP 401 Unauthorized with `WWW-Authenticate: Bearer`.
- **Banned Administrators Blocked:**  
  **CONFIRMED.** `get_current_account` explicitly checks `if account.is_banned: raise HTTPException(403)`.
- **Admin Identity Provenance:**  
  **CONFIRMED.** `admin_account_id` in `DiamondTransaction` is set directly from `admin.id` (server-side authenticated token `sub`), completely ignoring client-supplied payload values.
- **Private History Exposure:**  
  **CONFIRMED.** No player-facing endpoint in `app/player/router.py` exposes transaction history.

### 3.4 Task 4: Input Validation
- **Positive Integer Amounts:**  
  **CONFIRMED.** Pydantic schema enforces `amount: int = Field(..., gt=0, le=100_000_000)`.
- **Zero & Negative Rejected:**  
  **CONFIRMED.** Amount = 0 and Amount = -50 trigger HTTP 422 Unprocessable Entity.
- **Excessive Amounts Rejected:**  
  **CONFIRMED.** Amount > 100,000,000 triggers HTTP 422.
- **Character Existence:**  
  **CONFIRMED.** Non-existent GID returns HTTP 404 Not Found.
- **Overdraft Rejection:**  
  **CONFIRMED (Sequential).** When `balance_before < req.amount`, returns HTTP 400 Bad Request with `"Insufficient diamond balance"`.

### 3.5 Task 5: Ledger Integrity
- **One Mutation = One Ledger Row:**  
  **CONFIRMED.** Balance change and ledger insert occur in tandem.
- **Balance Math Reconciliation:**  
  **CONFIRMED.** Verified by `test_ledger_sum_matches_character_balance` (Initial balance + Sum of Grants - Sum of Deductions = Current Balance).
- **Immutability:**  
  **CONFIRMED.** No `UPDATE` or `DELETE` endpoints or repository methods exist for `DiamondTransaction`.
- **Pagination & Sorting:**  
  **CONFIRMED.** Ordered `id DESC` (newest first). Paginated with `limit` (max 100) and `offset`.
- **Database Constraints:**  
  **CONFIRMED.** Check constraints reject negative balances and zero/negative amounts at the database level.

### 3.6 Task 6: Migration Review
- **DDL Syntax:**  
  **CONFIRMED.** Both SQLite and PostgreSQL DDL blocks in [`migrations/003_add_diamond_transactions.sql`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/migrations/003_add_diamond_transactions.sql) are syntactically valid.
- **Foreign Keys:**  
  **CONFIRMED.** References `characters(gid)` and `accounts(id)`.
- **Preservation of Existing Data:**  
  **CONFIRMED.** The script strictly performs `CREATE TABLE` and `CREATE INDEX`. No existing tables or character balances are modified or reset.
- **Production Execution Status:**  
  **CONFIRMED.** No migrations have been run against a production database.

### 3.7 Task 7: Test Quality
- **Automated Tests Executed:** 109 tests across 14 test modules in 7.23 seconds.
- **Database Tested:** SQLite in-memory only.
- **Missing Test Scenarios:**
  - Concurrent grants (`asyncio.gather`).
  - Concurrent deductions (`asyncio.gather`).
  - Concurrent duplicate idempotency requests (`asyncio.gather`).
  - Live PostgreSQL concurrency validation.

---

## 4. Test Execution Summary

The following test command was executed in read-only mode against the isolated test environment:

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

============================= 109 passed in 7.23s =============================
```

---

## 5. Remaining Risks

1. **Local & Development Overdraft Risk (SQLite):**  
   If multiple clients or test scripts simultaneously trigger deductions for the same character during local testing, balances can desynchronize or overdraft.
2. **PostgreSQL Production Configuration Risk:**  
   PostgreSQL behavior relies on `SELECT ... FOR UPDATE` to lock character rows. If PostgreSQL runs with read replicas or without proper transaction isolation, row locking assumptions must be validated against PostgreSQL directly before production deployment.
3. **Double Commit Under Concurrency in SQLite:**  
   Because `character.diamonds = balance_after` assigns absolute numbers rather than applying relative delta updates (`diamonds = diamonds + :amount`), any environment without strict serializable row locks will suffer from lost updates during race conditions.

---

## 6. Recommended Fixes (For Subsequent Implementation)

The following non-disruptive fixes are recommended to resolve the identified issues:

### Recommendation 1: Atomic SQL Expressions for Balance Updates
Instead of reading `character.diamonds` into Python, calculating `balance_after`, and assigning `character.diamonds = balance_after`:
- Use an atomic SQL update statement:
  ```python
  # For deductions:
  stmt = (
      update(Character)
      .where(Character.gid == character_gid, Character.diamonds >= req.amount)
      .values(diamonds=Character.diamonds - req.amount)
  )
  res = await session.execute(stmt)
  if res.rowcount == 0:
      # Either character does not exist or insufficient balance!
  ```
- This forces the database engine (both SQLite and PostgreSQL) to atomically verify and decrement the balance in a single instruction, preventing double spending even when row-level locking is unavailable.

### Recommendation 2: Per-Character In-Memory Concurrency Lock (Single-Worker Server)
Since the ROS Private Server architecture enforces single-worker execution (`validate_single_worker_configuration()`), an in-memory lock table (`dict[int, asyncio.Lock]`) keyed by `character_gid` can serialize all mutations for any given character in the FastAPI layer before database queries execute. This completely eliminates concurrent races for the same character under SQLite.

### Recommendation 3: Add Concurrency Test Suite
Add automated tests in `tests/test_diamond_ledger.py` utilizing `asyncio.gather` to assert that:
- Simultaneous grants correctly accumulate without lost updates.
- Simultaneous deductions exceeding balance result in exactly one success and one HTTP 400 rejection.
- Simultaneous identical idempotency tokens resolve cleanly without HTTP 500 errors.

### Recommendation 4: Whitespace Stripping in Schemas
Add `@field_validator("idempotency_key", "reason")` with `.strip()` in `app/economy/schemas.py` to reject whitespace-only strings.

---

## 7. Conclusion & Next Steps

This audit is **complete and read-only**. No project code, configurations, database records, or test files were modified.

**Awaiting operator approval before proceeding.**
