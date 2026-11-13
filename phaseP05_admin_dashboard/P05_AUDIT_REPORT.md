# ROS Sothat — Phase P05: Secure Admin Dashboard
## Stage A — Comprehensive Pre-Implementation Audit Report

**Date:** 2026-11-13  
**Auditor:** Antigravity / DeepMind AI Assistant  
**Status:** COMPLETE — STAGE A AUDIT ONLY (NO SYSTEM FILES MODIFIED)  
**Project Root:** `D:\ROS-Legacy-Analysis\`  
**Backend:** `D:\ROS-Legacy-Analysis\ros-private-server`  
**Frontend:** `D:\ROS-Legacy-Analysis\ros-website`  
**P05 Artifacts Directory:** `D:\ROS-Legacy-Analysis\phaseP05_admin_dashboard\`  

---

## 1. Executive Summary

Phase P05 authorizes the audit, design, implementation, and verification of a secure, responsive **Admin Dashboard** for the ROS Sothat private server platform.

As mandated by Stage A rules, this audit was conducted strictly in **READ-ONLY** mode prior to modifying any source code or database schemas. This report documents the exact architectural foundation, existing security enforcement, data flow models for economy and inventory, baseline test suites, identified gaps, and the detailed roadmap for subsequent stages (B through J).

### Layer 1 vs. Layer 2 Scope Distinction
* **Layer 1 (Target of P05):** Private server relational database, FastAPI administration API, atomic diamond transaction ledger, relational inventory ledger, administrative audit logs, and Vue 3 frontend admin portal.
* **Layer 2 (Out of Scope for P05):** Mercury UDP network protocol, BaseApp / CellApp game entity managers, and original game client property synchronization. P05 makes zero claims regarding native in-game client synchronization, preserving the untouched original game assets.

---

## 2. Baseline Integrity & Cryptographic Hash Verification

Before initiating any analysis, the read-only protected assets were verified against their known reference hashes:

| Protected Asset | Known Original SHA-256 | Current Computed SHA-256 | Verification Result |
|---|---|---|---|
| `D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa` | `D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55` | `D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55` | **MATCH (PERFECT)** |
| `D:\ROS-Legacy-Analysis\extracted\Payload\client.app\client` | `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6` | `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6` | **MATCH (PERFECT)** |

Zero bytes of the original game IPA or extracted binary were accessed or modified.

---

## 3. Existing Backend Architecture (Section A1)

### 3.1 Framework & Module Layout
The backend application is implemented using FastAPI and SQLAlchemy (asyncio) structured into modular domains:
* `app/main.py`: Entry point; binds CORS, lifespan hooks (background memory cleanup), error handling, and registers all sub-routers under `API_V1_PREFIX` (`/api/v1`).
* `app/account/`: Manages `accounts` and `email_otps` tables. Contains password hashing (PBKDF2-HMAC-SHA256), email OTP hashing (server-side HMAC-SHA256 with `OTP_SECRET_KEY`), token generation/verification (HMAC-SHA256 signed bearer tokens), and authentication dependencies.
* `app/player/`: Manages player characters (`characters` table), appearances JSON, game settings JSON, and statistics JSON.
* `app/economy/`: Manages character diamond currency and append-only ledger (`diamond_transactions` table).
* `app/inventory/`: Manages item catalog (`items` table), player inventory slots (`inventory_items` table), and inventory modification transactions (`inventory_transactions` table).
* `app/admin/`: Existing admin API endpoints (`app/admin/router.py`).
* `app/lobby/`, `app/room/`, `app/matchmaking/`: In-memory game coordination services.
* `app/cli/admin.py`: CLI bootstrap utility for administrative promotion.

### 3.2 Database Session & Transaction Management
* Configured in `app/database/session.py`.
* Production configuration defaults to `sqlite+aiosqlite:///./ros_private.db` with support for PostgreSQL (`postgresql+asyncpg`).
* Test suites execute against an isolated in-memory SQLite database (`sqlite+aiosqlite:///:memory:`).
* All transactions use `async with async_session_factory() as session` with explicit `session.commit()` and `session.rollback()`.

---

## 4. Existing Frontend Architecture (Section A2)

### 4.1 Framework & Store Structure
* **Stack:** Vue 3, Vite, TypeScript, Pinia, Vue Router 4.
* **Router (`src/router/index.ts`):** Defines navigation routes with global navigation guard `beforeEach`:
  * Public routes: `/` (Home), `/login` (Login), `/register` (Register), `/404` (Not Found).
  * Protected routes: `/dashboard`, `/dashboard/profile`, `/dashboard/wallet`, `/dashboard/inventory`, `/dashboard/statistics`, `/dashboard/settings`.
* **State Management (`src/stores/auth.ts`):**
  * Manages `token` in `sessionStorage` (`ros_sothat_token`).
  * Manages `user: AccountProfile | null`.
  * Computes `isAuthenticated`, `isPlayer`, `isAdmin`.
  * Restores session via `initSession()` calling `GET /api/v1/account/me`.
* **API Service (`src/services/api.ts`):** Centralized HTTP client wrapping `fetch` with Bearer authorization headers and structured error propagation.

---

## 5. Current Authorization Architecture (Section A3)

### 5.1 Identity & Role Storage
* Administrators are identified strictly via the database column `accounts.role` (`VARCHAR(16)`), with valid values `'player'` and `'admin'`.
* Roles are **NEVER** trusted from client requests, request JSON payloads, or frontend state.

### 5.2 Token Verification & Lifecycle
* When a user logs in via email OTP or password, the server creates a two-segment token (`base64url(payload).base64url(HMAC_SHA256(secret, payload))`).
* The payload includes `sub` (account_id), `username`, `role`, and `exp` timestamp.
* On incoming requests, `get_current_account` in `app/account/service.py`:
  1. Validates the Bearer token signature using constant-time comparison (`hmac.compare_digest`).
  2. Verifies `time.time() <= payload["exp"]`.
  3. Queries the database for the active `Account` record by `sub` (account ID).
  4. Confirms `account.is_banned == False` (403 Forbidden if banned).
* `get_current_admin` depends on `get_current_account` and asserts `account.role == "admin"`. If `account.role != "admin"`, it immediately raises `HTTP 403 Forbidden`.

### 5.3 Authorization Enforcement Status Matrix

| Scenario | Handled By | Response Code & Detail |
|---|---|---|
| Unauthenticated request (no header) | `get_current_account` | `401 Unauthorized` ("Missing Bearer authentication token.") |
| Corrupted or invalid token signature | `get_current_account` | `401 Unauthorized` ("Invalid or expired token.") |
| Expired token | `get_current_account` | `401 Unauthorized` ("Invalid or expired token.") |
| Valid player token to admin endpoint | `get_current_admin` | `403 Forbidden` ("Admin privileges required.") |
| Banned account token | `get_current_account` | `403 Forbidden` ("Account is banned.") |
| Valid admin token to admin endpoint | `get_current_admin` | `200 OK` (Proceeds to controller) |

### 5.4 IDOR & Cross-Account Isolation
* In `app/player/router.py`, all player endpoints (`/player/character`, `/player/character/inventory`, `/player/character/diamonds/history`, `/player/character/settings`, `/player/character/appearances`) derive the account ID strictly from `current_account.id`.
* Players cannot query or modify another player's inventory, diamonds, or settings.

---

## 6. Diamond Data Integrity & Concurrency Model (Section A4)

### 6.1 Balance Storage & Database Constraints
* Diamonds are stored in `characters.diamonds` (`BigInteger`, default `100`).
* Table-level database constraint: `CheckConstraint("diamonds >= 0", name="chk_character_diamonds_non_negative")`. Negative balances are physically rejected by the database engine.

### 6.2 Ledger Implementation
* Every operation is recorded in `diamond_transactions`:
  * `id` (`BigInteger` PK)
  * `character_gid` (`BigInteger` FK to `characters.gid`)
  * `admin_account_id` (`Integer` FK to `accounts.id`)
  * `operation_type` (`VARCHAR(16)`: `'GRANT'` or `'DEDUCT'`)
  * `amount` (`BigInteger`, check constraint `amount > 0`)
  * `balance_before` (`BigInteger`, check constraint `balance_before >= 0`)
  * `balance_after` (`BigInteger`, check constraint `balance_after >= 0`)
  * `idempotency_key` (`VARCHAR(64)` UNIQUE, indexed)
  * `reason` (`VARCHAR(255)`)
  * `created_at` (`TIMESTAMP`)

### 6.3 Atomicity & Concurrency Safety
* `EconomyRepository.atomic_grant` executes:
  ```sql
  UPDATE characters 
  SET diamonds = diamonds + :amount, updated_at = :now 
  WHERE gid = :character_gid 
  RETURNING diamonds;
  ```
* `EconomyRepository.atomic_deduct` executes:
  ```sql
  UPDATE characters 
  SET diamonds = diamonds - :amount, updated_at = :now 
  WHERE gid = :character_gid AND diamonds >= :amount 
  RETURNING diamonds;
  ```
* Both balance modification and transaction insertion take place within a single database transaction. If ledger creation fails, the transaction is rolled back completely.
* Replays with identical idempotency keys return the existing record idempotently. Replays with conflicting parameters return `409 Conflict`.

---

## 7. Inventory Ownership & Data Model (Section A5)

### 7.1 Relational Schema
* Catalog items: `items` table (`id`, `item_code` UNIQUE, `name`, `description`, `item_type`, `icon`, `stackable`, `max_stack`, `is_active`).
* Player inventory: `inventory_items` table:
  * `character_gid` (`BigInteger` FK)
  * `item_id` (`Integer` FK)
  * `quantity` (`Integer`, check constraint `quantity > 0`)
  * Unique constraint: `UniqueConstraint("character_gid", "item_id", name="uq_character_inventory_item")`
* Transactions: `inventory_transactions` table (tracks `character_gid`, `item_id`, `admin_account_id`, `operation_type`, `quantity`, `quantity_before`, `quantity_after`, `reason`, `idempotency_key`, `created_at`).

### 7.2 Critical Audit Finding: Equipped Items During Removal
* In `Character.appearances`, clothing IDs are stored in JSON:
  ```json
  {
    "equipped_clothing": [10001, 10002],
    "unlocked_items": [10001, 10002],
    "active_weapon_skin": 0
  }
  ```
* **Vulnerability Identified:** The existing `InventoryService.remove_inventory` verifies quantity in `inventory_items`, but does NOT cross-reference `Character.appearances["equipped_clothing"]`. If an admin deletes or removes an item that is currently equipped down to zero, the character profile retains dangling item IDs in `equipped_clothing`.
* **Remediation Required:** In Stage D, ensure that when an item quantity drops to 0, either:
  1. The item is automatically removed from `character.appearances["equipped_clothing"]` in the same transaction, or
  2. Removal of currently equipped gear requires explicit unequipping or rejection.

---

## 8. Existing Database Schemas & Migrations (Section A6)

Existing migrations in `ros-private-server/migrations/`:
* `001_add_device_id.sql`
* `002_add_account_role.sql`
* `003_add_diamond_transactions.sql`
* `004_add_inventory_system.sql`
* `005_add_email_and_otp_tables.sql`

All existing migrations provide dual-syntax DDL for SQLite and PostgreSQL.

---

## 9. Baseline Test Suite Verification

Both test suites were executed in isolated test environments:

### 9.1 Backend Test Results (`ros-private-server`)
* **Execution:** `python -m pytest -v`
* **Result:** **162 passed, 1 skipped** (live PostgreSQL connection skipped as expected in local test mode) in 24.49s.
* **Coverage:** Account authentication, OTP, rate limiting, RBAC, diamond ledger atomicity, diamond concurrency, inventory CRUD, inventory concurrency, player dashboard API, discovery parsing, and Mercury UDP protocol framing.

### 9.2 Frontend Test Results (`ros-website`)
* **Execution:** `npm.cmd test` (Vitest v2.1.9)
* **Result:** **53 passed** across 6 test suites (auth service, auth store, otp input, router guards, player dashboard, browser viewports) in 4.35s.
* **Production Build (`npm.cmd run build`):** TypeScript compilation (`vue-tsc`) and Vite asset bundling completed successfully with **0 errors** in 1.40s.

---

## 10. Identified Weaknesses, Missing Features & Roadmap

| Area | Current State | Missing in P05 / Required Enhancement |
|---|---|---|
| **Admin Summary API** | Only `GET /admin/stats` returning in-memory lobby counts. | Missing `GET /api/v1/admin/dashboard/summary` aggregating real DB accounts, characters, total diamonds, inventory items, and recent administrative actions. |
| **Player Search & Detail API** | `GET /admin/accounts` returns basic account list without character details, search query `q`, or pagination total. | Need `GET /api/v1/admin/players` with search query, character nicknames, diamond balances, and `GET /api/v1/admin/players/{player_id}` for comprehensive player inspection. |
| **Account Suspension** | `POST /admin/accounts/{id}/ban` exists with self-ban guard. | Need clear suspend/reactivate API semantics (`POST /api/v1/admin/players/{player_id}/suspend` and `/reactivate`) recording admin audit entries. |
| **Equipped Item Safety** | `InventoryRepository.atomic_remove` does not check `appearances["equipped_clothing"]`. | Add automatic unequip or equipped-item safety check during inventory removal. |
| **Unified Audit Logging** | `diamond_transactions` and `inventory_transactions` exist, but no unified table logs account bans, role changes, and system events. | Add `audit_logs` table / model (`migrations/006_add_admin_audit_logs.sql`) and `GET /api/v1/admin/audit-logs` endpoint. |
| **Admin Frontend Portal** | Frontend currently only has player dashboard (`/dashboard/*`). | Create admin layout (`AdminLayout.vue`, `AdminSidebar.vue`, `AdminHeader.vue`), admin pages (`/admin`, `/admin/players`, `/admin/players/:id`, `/admin/transactions`, `/admin/inventory`, `/admin/audit-logs`), and `requiresAdmin` route guards. |

---

## 11. Proposed Architecture & Implementation Plan

### 11.1 Backend Implementation (Stages B, C, D, E, G)
1. **Migration 006 (`migrations/006_add_admin_audit_logs.sql`):** Add `audit_logs` table with indexes on `admin_account_id`, `action_type`, `created_at`.
2. **Audit Model & Service:** Create `app/admin/models.py` (`AdminAuditLog`), repository, and audit recording helper.
3. **Admin Router Extensions:**
   - `GET /api/v1/admin/dashboard/summary`
   - `GET /api/v1/admin/players` (with search and pagination)
   - `GET /api/v1/admin/players/{player_id}` (detailed inspection)
   - `POST /api/v1/admin/players/{player_id}/suspend`
   - `POST /api/v1/admin/players/{player_id}/reactivate`
   - `POST /api/v1/admin/players/{player_id}/diamonds/grant` (and deduct/history)
   - `GET /api/v1/admin/audit-logs` (filterable, paginated)
4. **Equipped Item Safeguard:** Ensure `InventoryService.remove_inventory` cleanses `Character.appearances["equipped_clothing"]` atomically when an item is fully removed.

### 11.2 Frontend Implementation (Stage F)
1. **Types (`src/types/admin.ts`):** Dashboard summary, player admin summaries, player detail, diamond mutation payloads, inventory grant/remove payloads, audit log entries.
2. **Admin API Service (`src/services/admin.ts`):** Admin HTTP requests using authenticated Bearer token.
3. **Route Guards (`src/router/index.ts`):** Add `meta: { requiresAuth: true, requiresAdmin: true }` redirecting unauthorized players to `/dashboard` or `/404`.
4. **Admin UI Components (`src/components/admin/`):**
   - `AdminLayout.vue`
   - `AdminSidebar.vue`
   - `AdminHeader.vue`
5. **Admin Pages (`src/pages/admin/`):**
   - `AdminOverviewPage.vue` (`/admin`)
   - `AdminPlayersPage.vue` (`/admin/players`)
   - `AdminPlayerDetailPage.vue` (`/admin/players/:id`)
   - `AdminDiamondsPage.vue` (`/admin/transactions`)
   - `AdminInventoryPage.vue` (`/admin/inventory`)
   - `AdminAuditLogsPage.vue` (`/admin/audit-logs`)

---

## 12. Risk Assessment & Decision Matrix

1. **Production Database Risk:** None. All development and testing run against isolated local/in-memory databases. Production database connection is forbidden.
2. **Original Game Binary Risk:** None. Read-only SHA-256 hashes verified before and after. Zero modifications to IPA or extracted Mach-O.
3. **Self-Lockout Risk:** Enforced by strict backend guards preventing administrators from banning or demoting their own account.
4. **Concurrency & Double Spending Risk:** Prevented by SQL-level atomic `UPDATE ... RETURNING` and database uniqueness constraints on idempotency keys.
5. **Decisions Requiring User Clarification:** None. All requirements fit cleanly within the approved P05 scope.

Stage A Audit is complete and verified. Proceeding to Stage B through J.
