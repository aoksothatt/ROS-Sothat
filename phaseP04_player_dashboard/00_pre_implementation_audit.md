# Phase P04 — Pre-Implementation Audit & System Analysis

**Document:** `00_pre_implementation_audit.md`  
**Phase:** P04 (Player Dashboard Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Author:** Antigravity Engineering Agent  
**Date:** November 13, 2026  
**Security Level:** Read-Only Analysis & Isolated Development Preparation  

---

## 1. Executive Summary

This pre-implementation audit examines the existing web frontend (`ros-website`) and backend platform (`ros-private-server`) to establish the architectural foundation for **Phase P04: Player Dashboard**. 

Every data entity, database relationship, repository query, and API endpoint was traced directly from source code and schema definitions. No assumptions were made based on prior documentation or speculative feature lists.

### Baseline Asset Hash Verification
Prior to audit or implementation activities, the original protected binaries were verified:
- **`RoS-Legacy-iOS.ipa` SHA-256:**  
  `D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55` (**MATCH**)
- **`Payload\client.app\client` SHA-256:**  
  `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6` (**MATCH**)

---

## 2. Answers to Mandatory Audit Questions

### 1. How is a player account linked to a game character?
- An account is stored in the `accounts` table (`id` primary key).
- A character is stored in the `characters` table with `account_id: Integer` defined as a foreign key (`ForeignKey("accounts.id")`) with a strict `unique=True` constraint.
- In SQLAlchemy ORM:
  - `Account.character`: `relationship("Character", back_populates="account", uselist=False, cascade="all, delete-orphan")`
  - `Character.account`: `relationship("Account", back_populates="character")`

### 2. Can one account have multiple characters?
- **No.** The unique constraint on `characters.account_id` and `uselist=False` in the ORM strictly limits each player account to a single character profile.

### 3. What is the authoritative diamond balance?
- The authoritative balance is stored in the database column `characters.diamonds` (BigInteger, default 100).
- It is enforced at the database level by a check constraint: `CheckConstraint("diamonds >= 0", name="chk_character_diamonds_non_negative")`.

### 4. Is the balance calculated from a ledger or stored directly?
- **Hybrid Source of Truth:** The balance is stored directly in `characters.diamonds` for low-latency atomic queries and updates, but every modification is atomically paired with an immutable entry in the `diamond_transactions` table.
- Each `DiamondTransaction` records `operation_type` (`GRANT` or `DEDUCT`), `amount`, `balance_before`, `balance_after`, `idempotency_key`, and `reason`.
- Backend tests (`test_ledger_sum_matches_character_balance`) verify that the net sum of transactions matches `characters.diamonds` identically.

### 5. Are inventory items linked to accounts or characters?
- Inventory items are linked to **characters**, not accounts.
- Specifically, `inventory_items.character_gid` references `characters.gid`.

### 6. What fields describe an inventory item?
- An `InventoryItem` record has:
  - `id`: BigInteger primary key
  - `character_gid`: BigInteger foreign key to `characters.gid`
  - `item_id`: Integer foreign key to `items.id`
  - `quantity`: Integer (positive)
  - `created_at`: DateTime
  - `updated_at`: DateTime
  - `item`: joined catalog `Item` object with:
    - `item_code`: programmatic identifier (e.g. `M4A1_DRAGON`)
    - `name`: display title
    - `description`: item text
    - `item_type`: category (`WEAPON_SKIN`, `CLOTHING`, `CONSUMABLE`)
    - `icon`: asset icon path
    - `stackable`: boolean
    - `max_stack`: integer limit
    - `is_active`: catalog status boolean

### 7. Is there an item catalog?
- **Yes.** The relational `items` table serves as the authoritative catalog of all valid items in the private server ecosystem.

### 8. Are item quantities supported?
- **Yes.** `inventory_items.quantity` is an integer constrained by `CheckConstraint("quantity > 0")`. For stackable items, quantities can stack up to `item.max_stack`.

### 9. Are equipped items supported?
- **Yes.** Equipped cosmetic items and skins are tracked in `characters.appearances` (JSON), specifically `equipped_clothing: List[int]` and `active_weapon_skin: int`. Players can equip clothing via `PUT /api/v1/player/character/appearances`.

### 10. What player statistics currently exist?
- The `characters.stats` (JSON) field exists and initializes to:
  ```json
  {
    "total_matches": 0,
    "total_wins": 0,
    "total_kills": 0,
    "damage_dealt": 0.0
  }
  ```

### 11. Are statistics real or placeholders?
- The data fields are real database attributes, but because multiplayer matches on the dedicated game server have not yet begun, all accounts currently hold initial 0 values. Match telemetry is not fabricated.

### 12. Which endpoints are available?
- **Account Router (`/api/v1/account`):**
  - `POST /register`, `POST /login`, `POST /guest`, `POST /otp/request`, `POST /otp/verify`, `GET /me`
- **Player Router (`/api/v1/player`):**
  - `POST /character`: Create character
  - `GET /character`: Retrieve authenticated user's character profile (`CharacterOut`)
  - `GET /{gid}`: Public character profile
  - `PUT /character/settings`: Update game settings
  - `PUT /character/appearances`: Update equipped loadout
  - `GET /character/inventory`: Retrieve authenticated player's inventory items

### 13. Which endpoints require player authentication?
- `GET /api/v1/account/me`
- `POST /api/v1/player/character`
- `GET /api/v1/player/character`
- `PUT /api/v1/player/character/settings`
- `PUT /api/v1/player/character/appearances`
- `GET /api/v1/player/character/inventory`

### 14. Can players access only their own records?
- **Yes.** All authenticated endpoints derive the operator identity from the decoded JWT token (`current_account.id`). No caller-supplied `account_id` or `character_gid` is accepted on private endpoints.

### 15. Are any existing APIs unsafe for player-facing use?
- **Yes:** Endpoints under `/api/v1/admin/*` (`grant_diamonds`, `deduct_diamonds`, `grant_item`, `remove_item`, `role_updates`) require `get_current_admin` privileges. Calling these from player pages returns 403 Forbidden.
- **Missing Read-Only Endpoint:** While `GET /api/v1/player/character` returns `diamonds: int`, there is currently no player-safe endpoint to view personal `diamond_transactions` ledger history (`GET /api/v1/player/character/diamonds/history`).

---

## 3. Existing Architecture Review

### 3.1 Frontend (`ros-website`)
- **Technology Stack:** Vue 3.5, TypeScript 5.6, Vite 5.4, Pinia 2.2, Vue Router 4.4.
- **Current State:**
  - `src/stores/auth.ts`: In-memory token management with `sessionStorage` mirroring.
  - `src/router/index.ts`: Route protection via `beforeEach` navigation guards.
  - `src/pages/DashboardPage.vue`: Single landing page with basic profile details and static placeholder cards.
- **Target Evolution:** Refactor the dashboard into a modular layout with sub-routes:
  - `/dashboard` (Overview)
  - `/dashboard/profile` (Player Identity & Character Details)
  - `/dashboard/wallet` (Diamond Balance & Transaction Ledger)
  - `/dashboard/inventory` (Inventory Grid & Item Details)
  - `/dashboard/statistics` (Combat & Match Record Status)
  - `/dashboard/settings` (Account & Session Security)

### 3.2 Backend (`ros-private-server`)
- **Technology Stack:** FastAPI, SQLAlchemy 2.0 (asyncio), Pydantic v2, aiosqlite / asyncpg.
- **State & Services:**
  - `PlayerService`: Handles character lookup, creation, settings, and appearances.
  - `EconomyService`: Handles atomic diamond grants, deductions, and transaction history.
  - `InventoryService`: Handles catalog queries, stack management, and inventory listing.
- **Gap Identified:**
  - Need a safe, read-only endpoint in `app/player/router.py`:
    `GET /api/v1/player/character/diamonds/history`
    to expose `EconomyService.get_character_history(char.gid)` to the authenticated player without granting administrative privileges.

---

## 4. Planned Changes & Risk Mitigation

| Component | Target File | Nature of Change | Risk & Mitigation |
| :--- | :--- | :--- | :--- |
| **Backend API** | `app/player/router.py` | Add `GET /character/diamonds/history` read-only endpoint | **Zero regression risk:** Reuses existing `EconomyService.get_character_history`, strictly scoped to `current_account.id`. |
| **Backend Tests**| `tests/test_player_dashboard_api.py` | Add authorization and isolation tests for dashboard endpoints | Verifies that unauthenticated or cross-account access is rejected. |
| **Frontend Types**| `src/types/dashboard.ts` | Define TypeScript interfaces for Character, Inventory, Wallet, and Ledger | Type safety prevents malformed property access. |
| **Frontend Services**| `src/services/player.ts` | Type-safe fetch methods for character, wallet, inventory, and stats | Centralizes error handling and token injection. |
| **Frontend Views**| `src/pages/dashboard/*` | 6 dedicated sub-pages in tactical dark theme | Replaces placeholders with real backend telemetry. |
| **Frontend Components**| `src/components/dashboard/*`| Sidebar, Navbar, Item Cards, Wallet Ledger Table, Empty States | Responsive flex/grid layouts supporting 375px to 1920px viewports. |
| **Frontend Router**| `src/router/index.ts` | Register nested dashboard routes under `/dashboard` | Preserves existing auth guard protection. |

---

## 5. Audit Conclusion

The backend architecture possesses robust, production-grade economy, character, and inventory tables. Adding a single read-only diamond history endpoint completes the required API surface.

Phase P04 implementation may proceed immediately.
