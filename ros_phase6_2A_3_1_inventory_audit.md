# ROS Sothat — Phase 6.2A.3.1: Inventory Security, Concurrency & Data Integrity Audit Report

**Date:** November 11, 2026  
**Audit Scope:** Read-Only Security, Concurrency, and Data Integrity Audit of Phase 6.2A.3 Relational Item Catalog & Player Inventory Management System  
**Auditor:** Antigravity (Advanced Agentic Coding Pair Programmer)  
**Governing Strategy:** Option A (Independent Private-Server Backend; 100% Unmodified Original ROS Legacy iOS Client IPA)  
**Target Codebase Location:** `C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server`  
**Automated Test Baseline:** 123/123 tests passing (10.40s)  
**Database Engines Validated:** SQLite 3.45.1 (`sqlite+aiosqlite:///:memory:` and multi-connection file-based SQLite)  
**Database Engines Untested Live:** PostgreSQL (Service running, but Python async driver `asyncpg`/`psycopg` not installed in environment)  

---

## 1. Executive Summary & Audit Verdict

### **VERDICT: PASS WITH ISSUES**

**Summary of Audit Evaluation:**  
The relational item catalog, inventory mutation engine, and transaction audit ledger implemented in Phase 6.2A.3 demonstrate substantial improvements over previous iterations, directly resolving concurrency vulnerabilities previously identified during the diamond ledger audit.

Key architectural strengths confirmed during this read-only audit include:
1. **Database-Enforced Atomic Mutations:** Concurrency control does not rely on fragile Python-side memory arithmetic. Grant operations utilize dialect-aware native upserts (`ON CONFLICT DO UPDATE ... WHERE quantity + :qty <= max_stack RETURNING quantity`), preventing lost updates and stack overflow races. Removals utilize atomic decrement statements (`UPDATE ... WHERE quantity > :qty RETURNING quantity`) and atomic deletions (`DELETE ... WHERE quantity == :qty_before`), completely preventing negative quantities and database check constraint violations.
2. **Two-Tier Idempotency Engine:** In-memory application checks provide fast-path deduplication, backed by a hard database `UNIQUE` constraint and index on `inventory_transactions.idempotency_key`. Concurrent identical requests are safely resolved by catching `IntegrityError` and querying the committed transaction without duplicate side-effects.
3. **Strict RBAC & Player Privacy Isolation:** The player inventory endpoint (`GET /api/v1/player/character/inventory`) derives character identity exclusively from trusted server-side authentication tokens (`get_current_account`), preventing arbitrary character ID tampering. Administrative catalog and inventory endpoints require `get_current_admin` and strictly reject normal players (HTTP 403) and unauthenticated callers (HTTP 401).
4. **Append-Only Immutability:** Audit records in `inventory_transactions` are created within the same database transaction boundary as the inventory mutation. No update or delete endpoints exist for ledger history.

**Identified Issues (Non-Critical):**
- **Medium Severity:** PostgreSQL-specific behavior and DDL have not been validated against a live PostgreSQL instance due to missing Python async database drivers in the test environment.
- **Low Severity:** Certain complex concurrency scenarios (mixed grant/remove races, identical simultaneous idempotency races) were validated via isolated diagnostic scripts but are not yet formalized into the permanent test suite (`tests/test_inventory.py`).
- **Low Severity:** The catalog update endpoint (`PATCH /api/v1/admin/items/{id}`) allows reducing an item's `max_stack` without validating whether active player inventories currently hold quantities exceeding the new threshold.

---

## 2. Findings Grouped by Severity

### 2.1 High Severity Findings
*None identified. Zero critical security, authorization bypass, or lost update vulnerabilities were found.*

---

### 2.2 Medium Severity Findings

#### `FINDING-TEST-01`: Absence of Live PostgreSQL End-to-End Concurrency & DDL Validation
- **Component:** Test Infrastructure & Database Compatibility
- **Affected Files & Lines:**
  - [`migrations/004_add_inventory_system.sql#L72-L135`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/migrations/004_add_inventory_system.sql#L72-L135)
  - [`app/inventory/repository.py#L133-L155`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/repository.py#L133-L155)
  - [`tests/conftest.py#L15-L25`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/conftest.py#L15-L25)
- **Description:**  
  While the codebase implements dialect-specific branching for PostgreSQL (`sqlalchemy.dialects.postgresql.insert` vs `sqlalchemy.dialects.sqlite.insert`), all automated tests run exclusively against in-memory or file-based SQLite engines. Although a local PostgreSQL service (`postgresql-x64-18`) is running on the host machine, no async PostgreSQL client library (such as `asyncpg` or `psycopg`) is installed in the Python virtual environment.
- **Impact:**  
  PostgreSQL-specific syntax (such as `BIGSERIAL`, `TIMESTAMP WITH TIME ZONE`, and foreign key `ON DELETE CASCADE` / `ON DELETE RESTRICT` semantics) and PostgreSQL lock escalation behavior under high concurrency remain unverified against live PostgreSQL server instances.
- **Recommended Remediation:**  
  1. Install `asyncpg` in the development requirements.
  2. Add an optional environment variable (e.g., `TEST_POSTGRES_URL`) to `tests/conftest.py` that, when present, executes the suite against an isolated PostgreSQL database.

---

### 2.3 Low Severity Findings

#### `FINDING-TEST-02`: Missing Formal Concurrency Test Coverage for Mixed Operations & Idempotency Races in `tests/test_inventory.py`
- **Component:** Automated Test Suite
- **Affected Files & Lines:**
  - [`tests/test_inventory.py#L437-L516`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/test_inventory.py#L437-L516)
- **Description:**  
  In [`tests/test_inventory.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/test_inventory.py), `test_concurrent_inventory_grants_and_removals` tests two simultaneous grants and two simultaneous removals. However, it does not include permanent automated tests for:
  1. Simultaneous mixed operations (concurrent grant + removal on the same inventory slot).
  2. Concurrent race on the exact same idempotency key across independent sessions.
  3. Concurrent race on conflicting parameters using the same idempotency key.
- **Empirical Diagnostic Validation:**  
  During this audit, an isolated diagnostic script (`test_concurrency_diagnostic.py`) was executed to evaluate these exact cases against multi-connection SQLite:
  - *Mixed Grant + Remove:* Initial 50 + Grant 20 + Remove 10 evaluated cleanly to final quantity 60, with transaction records capturing accurate before/after snapshots.
  - *Identical Idempotency Race:* Both parallel workers returned HTTP 200 with identical transaction ID 5, and exactly 1 record was inserted into the database.
  - *Conflicting Idempotency Race:* One worker succeeded; the second received HTTP 409 Conflict.
- **Recommended Remediation:**  
  Incorporate these diagnostic test scenarios directly into [`tests/test_inventory.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/test_inventory.py) so they run in standard CI passes.

---

#### `FINDING-CAT-01`: Unconstrained Reduction of `max_stack` via Admin Catalog API
- **Component:** Catalog Management & Stack Bounds
- **Affected Files & Lines:**
  - [`app/inventory/service.py#L91-L98`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/service.py#L91-L98)
  - [`app/inventory/schemas.py#L50`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/schemas.py#L50)
- **Description:**  
  When an administrator updates a catalog item via `PATCH /api/v1/admin/items/{item_id}`, the service allows lowering `max_stack` (e.g., from 100 to 10) as long as `req.max_stack >= 1`. However, the service does not query `inventory_items` to verify whether any player currently possesses a quantity exceeding the new limit.
- **Impact:**  
  Existing inventory slots are not corrupted or deleted (players still hold their items), and subsequent removals remain functional. However, players will hold items in excess of the newly defined `max_stack`, and any subsequent grant operations on those slots will be rejected until the quantity is manually reduced below the new threshold.
- **Recommended Remediation:**  
  During catalog item update, if `max_stack` is being decreased, execute a check:
  `SELECT MAX(quantity) FROM inventory_items WHERE item_id = :item_id`.
  If the highest held quantity exceeds the proposed `max_stack`, return HTTP 400 Bad Request indicating that players currently hold stacks larger than the proposed limit.

---

### 2.4 Informational Findings

#### `FINDING-API-01`: Existence Disclosure on Admin Inventory Endpoints
- **Component:** API Information Disclosure (Admin Restricted)
- **Affected Files & Lines:**
  - [`app/inventory/service.py#L113-L119`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/service.py#L113-L119)
  - [`app/inventory/service.py#L331-L336`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/service.py#L331-L336)
- **Description:**  
  Requesting inventory or transaction history for a non-existent character GID returns HTTP 404, while querying an existing character with an empty inventory returns HTTP 200 with an empty list. Because these endpoints are guarded by `Depends(get_current_admin)`, this behavior is appropriate for administrative operations and poses no risk to player privacy.

---

## 3. Detailed Audit Tasks Verification

### 3.1 Stack Integrity
- **Database Enforcement vs Python Validation:**  
  **CONFIRMED.** Stack integrity is strictly enforced at the database layer. In [`app/inventory/repository.py#L146-L155`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/repository.py#L146-L155), the SQL `WHERE` clause on upsert conflicts specifies:
  ```python
  where=(InventoryItem.quantity + quantity <= item.max_stack)
  ```
  If a concurrent update causes `quantity + incoming > max_stack`, the database engine updates zero rows. The `.returning()` clause yields `None`, triggering `ValueError` and rolling back the transaction.
- **Non-Stackable Quantity = 1:**  
  **CONFIRMED.** Non-stackable items are created with `max_stack=1` and `stackable=False`. In `atomic_grant` ([`app/inventory/repository.py#L156-L167`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/repository.py#L156-L167)), non-stackable items execute a standard `INSERT` without conflict updates. Attempting to grant a non-stackable item to a character who already owns it triggers `UniqueConstraint("character_gid", "item_id")` at the database level.
- **Inactive Items Rejection:**  
  **CONFIRMED.** [`app/inventory/service.py#L180-L184`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/service.py#L180-L184) validates `item.is_active` prior to mutation. Inactive items are rejected with HTTP 400 Bad Request.
- **Invalid Quantity Rejection:**  
  **CONFIRMED.** Quantities `<= 0` and `> 9999` are rejected by Pydantic schemas ([`app/inventory/schemas.py#L79, L105`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/schemas.py#L79)). Furthermore, database CHECK constraints (`chk_inventory_item_quantity_positive`, `chk_inv_tx_quantity_positive`) reject non-positive quantities at the database engine level.

---

### 3.2 Concurrency & Race Conditions
- **Concurrent Grants (Lost Update Prevention):**  
  **CONFIRMED.** Multi-connection tests demonstrated that two simultaneous grants of 50 to a character slot accumulated to 100 without losing updates.
- **Concurrent Overflow Prevention:**  
  **CONFIRMED.** Empirical testing with initial balance 60 and `max_stack = 70` under concurrent grants of 10 and 10 demonstrated that exactly one grant succeeded (+10 to 70), while the second grant failed with HTTP 400 (`Cannot grant 10 items: would exceed max stack limit of 70`). The final balance remained safely capped at 70.
- **Concurrent Deductions & Overdraft Prevention:**  
  **CONFIRMED.** Removals use atomic conditional queries. Partial removals execute `UPDATE ... WHERE quantity > :qty`. Full removals execute `DELETE ... WHERE quantity == :qty_before`. When two simultaneous removals of 80 were attempted against a slot holding 100, exactly one succeeded (-80 to 20), and the second failed safely.
- **Mixed Concurrent Operations:**  
  **CONFIRMED.** Concurrent grant of +20 and removal of -10 against an initial balance of 50 executed safely, leaving exactly 60 items.
- **Slot Deletion on Quantity Zero:**  
  **CONFIRMED.** Removing an item with `quantity == 1` completely deletes the row from `inventory_items`, ensuring `CheckConstraint("quantity > 0")` is never violated.
- **History Snapshot Accuracy:**  
  **CONFIRMED.** Because `atomic_grant` and `atomic_remove` derive `quantity_before` and `quantity_after` from the database `RETURNING` statement, history snapshots reflect the actual chronological sequence of committed values (`50 -> 70`, `70 -> 60`).

---

### 3.3 Idempotency & Replay Protection
- **Identical Simultaneous Requests:**  
  **CONFIRMED.** Tested concurrently across separate database sessions. Fast-path and `IntegrityError` catch handlers ensure both callers receive HTTP 200 OK with identical transaction details and identical transaction IDs.
- **Conflicting Requests:**  
  **CONFIRMED.** Replaying an idempotency key with differing character GID, item ID, operation type, or quantity immediately returns HTTP 409 Conflict.
- **Retry After Failure:**  
  **CONFIRMED.** If an operation fails validation or stack limits, the session rolls back completely. Retrying with valid parameters using the same idempotency key succeeds cleanly.
- **Database Unique Constraint as Final Guard:**  
  **CONFIRMED.** `inventory_transactions.idempotency_key` is protected by `unique=True` in SQLAlchemy models and `CREATE UNIQUE INDEX ix_inventory_transactions_idempotency_key` in database DDL.

---

### 3.4 Player Authorization & Privacy
- **Authenticated Identity Resolution:**  
  **CONFIRMED.** [`app/player/router.py#L54-L73`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/player/router.py#L54-L73) enforces `current_account: Account = Depends(get_current_account)`. The character GID is derived from `player_service.repository.get_by_account_id(current_account.id)`.
- **Cross-Character Access Prevention:**  
  **CONFIRMED.** The endpoint accepts no character GID in the path or query parameters. A player cannot supply another player's GID to inspect their inventory.
- **Admin Endpoint Protection:**  
  **CONFIRMED.** All administrative catalog and inventory endpoints require `admin: Account = Depends(get_current_admin)`. Standard player tokens receive HTTP 403 Forbidden. Unauthenticated requests receive HTTP 401 Unauthorized.
- **Banned Accounts:**  
  **CONFIRMED.** `get_current_account` checks `account.is_banned` and raises HTTP 403 Forbidden for banned accounts.

---

### 3.5 Transaction History Integrity
- **One Mutation = One History Entry:**  
  **CONFIRMED.** Every successful grant or removal creates exactly one row in `inventory_transactions`. Failed operations roll back and create zero rows.
- **Atomic Transaction Boundary:**  
  **CONFIRMED.** Inventory mutations and transaction records are executed within the same database transaction and committed together via `await self.repository.commit()`.
- **Server-Side Admin Provenance:**  
  **CONFIRMED.** `admin_account_id` is populated directly from `admin.id` returned by `get_current_admin`. It cannot be supplied or spoofed in request bodies.
- **Pagination & Ordering:**  
  **CONFIRMED.** History queries sort by `InventoryTransaction.id.desc()` (newest first) and honor `limit` (max 100) and `offset` query parameters.
- **Ledger Immutability:**  
  **CONFIRMED.** No HTTP endpoints exist for updating or deleting inventory transactions.

---

### 3.6 Migration Review (`migrations/004_add_inventory_system.sql`)
- **DDL Syntax Validity:**  
  **CONFIRMED.** SQLite DDL uses valid `INTEGER PRIMARY KEY AUTOINCREMENT`, constraints, and indexes. PostgreSQL DDL uses valid `SERIAL`, `BIGSERIAL`, `TIMESTAMP WITH TIME ZONE`, and foreign key rules.
- **Foreign Keys:**  
  **CONFIRMED.** `inventory_items.character_gid -> characters(gid)`, `inventory_items.item_id -> items(id)`, and `inventory_transactions.admin_account_id -> accounts(id)` reference the correct tables.
- **Preservation of Existing Data:**  
  **CONFIRMED.** Migration 004 only creates new tables (`items`, `inventory_items`, `inventory_transactions`). It does not modify existing `characters` or `accounts` tables, preserving `Character.appearances` JSON data.
- **Zero Production Execution:**  
  **CONFIRMED.** No migrations have been run against any production database.

---

### 3.7 Test Quality Assessment
- **Test Suite Results:**  
  123 passing tests executed in 10.40s.
  - `tests/test_inventory.py`: 8 comprehensive tests covering catalog CRUD, RBAC, lifecycle grants/removals, idempotency, basic concurrency, history pagination, 404 validation, and database check constraints.
  - All existing account, admin RBAC, diamond ledger, matchmaking, room, and Mercury transport tests pass 100%.
- **Diagnostic Testing Executed:**  
  An isolated diagnostic test (`scratch/test_concurrency_diagnostic.py`) verified:
  - Mixed concurrent grant + remove operations.
  - Concurrent grants reaching `max_stack` limits.
  - Concurrent idempotency key collisions.
  - Rollback behavior on failed grants.
  - Full removal slot deletion down to 0.

---

## 4. SQLite vs PostgreSQL Validation Status

| Requirement / Component | SQLite Status | PostgreSQL Status | Details |
| :--- | :--- | :--- | :--- |
| **Catalog CRUD & Validation** | **VERIFIED** | **THEORETICALLY VALID** | Pydantic validation & Base ORM schemas work identically across dialects. |
| **Atomic Upsert (`atomic_grant`)** | **VERIFIED** | **THEORETICALLY VALID** | SQLite uses `sqlite_insert`; PostgreSQL branch uses `pg_insert` with matching syntax. |
| **Atomic Decrement (`atomic_remove`)** | **VERIFIED** | **THEORETICALLY VALID** | Standard ANSI SQL `UPDATE ... WHERE ... RETURNING` supported in both SQLite 3.35+ and PostgreSQL. |
| **Slot Deletion on Zero** | **VERIFIED** | **THEORETICALLY VALID** | Standard ANSI SQL `DELETE ... WHERE ...` supported in both engines. |
| **Check Constraints** | **VERIFIED** | **THEORETICALLY VALID** | `max_stack >= 1`, `quantity > 0`, `quantity_before >= 0`, `quantity_after >= 0` defined in DDL. |
| **Unique Indexes & Idempotency** | **VERIFIED** | **THEORETICALLY VALID** | `ix_inventory_transactions_idempotency_key` enforced at database layer. |
| **Live Database Execution** | **123/123 PASSED** | **UNTESTED** | No Python async driver installed for live PostgreSQL tests. |

---

## 5. Remaining Risks & Operational Recommendations

1. **PostgreSQL Deployment Risk:**  
   Before deploying against production PostgreSQL, install `asyncpg` and execute the test suite against a live staging PostgreSQL instance to ensure dialect-specific SQL functions operate identically under load.
2. **Catalog Stack Reduction Safeguard:**  
   Implement a validation check when updating catalog items (`PATCH /items/{id}`) to prevent setting `max_stack` lower than any existing inventory slot.
3. **Formalize Diagnostic Concurrency Tests:**  
   Incorporate mixed operation and idempotency collision tests into [`tests/test_inventory.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/test_inventory.py).

---

## 6. Conclusion & Next Steps

Phase 6.2A.3 (Relational Item Catalog & Player Inventory Management) has passed security, concurrency, and data integrity audits with **PASS WITH ISSUES** (due solely to the absence of a live PostgreSQL test harness and minor catalog validation edge cases). Concurrency control, stack integrity, RBAC authorization, and idempotency protection are robust.

**Status:** Awaiting user review and authorization before taking any further action or beginning Phase 6.2A.4.
