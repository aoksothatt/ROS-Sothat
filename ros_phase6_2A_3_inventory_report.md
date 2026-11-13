# ROS Sothat — Phase 6.2A.3: Item Catalog & Player Inventory Management Report

**Date:** November 11, 2026  
**Status:** COMPLETED & VERIFIED  
**Test Suite Status:** 123 / 123 passing (100% success rate across all modules)  
**Governing Strategy:** Option A (Independent Private-Server Backend; 100% Unmodified Original iOS Client IPA)  

---

## 1. Executive Summary

Phase 6.2A.3 introduces a production-grade relational item catalog and player inventory management subsystem into the ROS Sothat independent private-server backend. The architecture moves beyond the initial prototype's hardcoded JSON cosmetic arrays to an append-only, relational structure with strict stack limits, database constraints, administrative controls, and an immutable audit transaction history.

All 115 prior baseline tests continue to pass with zero regressions. 8 new automated tests in [`tests/test_inventory.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/test_inventory.py) validate catalog lifecycle, admin RBAC protections, non-stackable uniqueness, stackable overflow prevention, partial and full item removals, whitespace trimming, idempotency replay/conflict detection, and multi-connection concurrency.

---

## 2. Existing Inventory Architecture Audit Findings

Prior to Phase 6.2A.3:
1. **Storage Mechanism:** Character cosmetic items were stored as unstructured integer arrays inside a single JSON column on the `characters` table:
   ```python
   # Character.appearances (Semi-structured JSON)
   {
       "equipped_clothing": [10001, 10002],
       "unlocked_items": [10001, 10002],
       "active_weapon_skin": 0
   }
   ```
2. **Catalog Metadata:** No item catalog model existed. Items had arbitrary integer IDs without names, descriptions, types, stackability flags, or asset identifiers.
3. **Data Preservation:** The existing `Character.appearances` JSON field and its endpoints (`PUT /api/v1/player/character/appearances`) have been **100% preserved** to maintain backward compatibility with synthetic test clients. The relational inventory system operates alongside `appearances` without data loss or column truncation.
4. **Services Interacting with Inventory:** Previously, only `PlayerService` read or wrote cosmetic items.

---

## 3. Relational Inventory Architecture & Database Models

Three relational models have been implemented in [`app/inventory/models.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/inventory/models.py):

```
 ┌───────────────────────────────────┐               ┌───────────────────────────────────┐
 │               Item                │               │             Character             │
 ├───────────────────────────────────┤               ├───────────────────────────────────┤
 │ id: int (PK)                      │               │ gid: int (PK)                     │
 │ item_code: varchar(64) (UNIQUE)   │               │ nickname: varchar(64)             │
 │ name: varchar(128)                │               │ diamonds: bigint                  │
 │ description: varchar(512)         │               │ ...                               │
 │ item_type: varchar(32)            │               └─────────────────┬─────────────────┘
 │ icon: varchar(255)                │                                 │
 │ stackable: bool                   │                                 │
 │ max_stack: int (CHECK >= 1)       │                                 │
 │ is_active: bool                   │                                 │
 └─────────────────┬─────────────────┘                                 │
                   │                                                   │
                   │ 1                                               1 │
                   │         ┌───────────────────────────────┐         │
                   └────────►│         InventoryItem         │◄────────┘
                             ├───────────────────────────────┤
                             │ id: bigint (PK)               │
                             │ character_gid: bigint (FK)    │
                             │ item_id: int (FK)             │
                             │ quantity: int (CHECK > 0)     │
                             │ UNIQUE (character_gid, item_id│
                             └───────────────────────────────┘
                                             ▲
                                             │ (Audited by)
                             ┌───────────────┴───────────────┐
                             │     InventoryTransaction      │
                             ├───────────────────────────────┤
                             │ id: bigint (PK)               │
                             │ character_gid: bigint (FK)    │
                             │ item_id: int (FK)             │
                             │ admin_account_id: int (FK)    │
                             │ operation_type: varchar(16)   │
                             │ quantity: int (CHECK > 0)     │
                             │ quantity_before: int (>= 0)   │
                             │ quantity_after: int (>= 0)    │
                             │ reason: varchar(255)          │
                             │ idempotency_key: varchar (UQ) │
                             └───────────────────────────────┘
```

### 3.1 Model 1: `Item` (Relational Catalog)
- **`id`**: Primary Key, autoincrement.
- **`item_code`**: Unique, uppercase alphanumeric + underscore identifier (e.g. `WEAP_M4A1_CYBER`, `CONS_MEDKIT_ADV`).
- **`name`**: Display name string.
- **`description`**: Descriptive text.
- **`item_type`**: Categorization tag (`WEAPON_SKIN`, `CLOTHING`, `CONSUMABLE`, `CRATE`, `CURRENCY`, `BADGE`).
- **`icon`**: Asset or UI placeholder path.
- **`stackable`**: Boolean determining whether items stack in a single slot.
- **`max_stack`**: Maximum allowable quantity per slot (enforced `max_stack >= 1` by check constraint). Non-stackable items enforce `max_stack = 1`.
- **`is_active`**: Soft-deletion/enablement toggle. Inactive items cannot be granted to players.

### 3.2 Model 2: `InventoryItem` (Player Inventory Slots)
- **`id`**: Primary Key.
- **`character_gid`**: Foreign Key to `characters.gid`.
- **`item_id`**: Foreign Key to `items.id`.
- **`quantity`**: Slot count. Enforced `quantity > 0` by check constraint `chk_inventory_item_quantity_positive`.
- **Unique Constraint:** `(character_gid, item_id)` guarantees exactly one inventory slot per character per item.

### 3.3 Model 3: `InventoryTransaction` (Append-Only Audit Ledger)
- **`id`**: Primary Key.
- **`character_gid`**: Recipient/donor character.
- **`item_id`**: Catalog item modified.
- **`admin_account_id`**: Admin account executing the mutation (derived server-side from JWT token `sub`).
- **`operation_type`**: `'GRANT'` or `'REMOVE'`.
- **`quantity`**: Quantity magnitude (> 0).
- **`quantity_before`**: Previous slot quantity ($\ge 0$).
- **`quantity_after`**: Resulting slot quantity ($\ge 0$).
- **`reason`**: Mandatory administrative justification string.
- **`idempotency_key`**: Unique client-supplied token preventing duplicate operations.

---

## 4. API Endpoints

### 4.1 Admin Endpoints ([`app/admin/router.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/admin/router.py#L188-L288))
*All endpoints require `Depends(get_current_admin)`.*

| Method | Path | Request Body | Description |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/v1/admin/items` | None (Query: `item_type`, `is_active`, `limit`, `offset`) | Paginated listing of catalog items. |
| **POST** | `/api/v1/admin/items` | `ItemCreate` | Registers a new item. Rejects duplicate `item_code` with 409. |
| **PATCH** | `/api/v1/admin/items/{item_id}` | `ItemUpdate` | Updates item display name, description, icon, max stack, or active state. |
| **GET** | `/api/v1/admin/characters/{gid}/inventory` | None (Query: `limit`, `offset`) | Lists all inventory items held by target character. |
| **POST** | `/api/v1/admin/characters/{gid}/inventory/grant` | `InventoryGrantRequest` | Atomically grants stackable or non-stackable items to character. |
| **POST** | `/api/v1/admin/characters/{gid}/inventory/remove` | `InventoryRemoveRequest` | Atomically removes items from inventory; deletes slot if quantity reaches 0. |
| **GET** | `/api/v1/admin/characters/{gid}/inventory/history` | None (Query: `limit`, `offset`) | Paginated audit trail of inventory grants and removals ordered newest-first. |

### 4.2 Player Endpoints ([`app/player/router.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/player/router.py#L52-L73))
*Requires authenticated player session (`Depends(get_current_account)`).*

| Method | Path | Description |
| :--- | :--- | :--- |
| **GET** | `/api/v1/player/character/inventory` | Retrieves the authenticated player's own inventory items with full item catalog metadata. |

---

## 5. Security & Reliability Controls

1. **Role-Based Access Control:**  
   Unauthenticated calls receive `HTTP 401 Unauthorized`. Non-admin players receive `HTTP 403 Forbidden` on all administrative catalog and inventory endpoints.
2. **Server-Side Identity:**  
   The `admin_account_id` recorded in `InventoryTransaction` is derived exclusively from the authenticated session (`admin.id`), ignoring client-supplied payloads.
3. **Overdraft & Negative Balance Prevention:**  
   Attempting to remove more items than a character owns returns `HTTP 400 Bad Request` (`"Insufficient item quantity"`). Check constraints reject negative quantities at the database level.
4. **Stack Overflow Prevention:**  
   Attempting to grant items beyond an item's `max_stack` limit returns `HTTP 400 Bad Request` (`"Cannot grant X items: would exceed max stack limit"`).
5. **Non-Stackable Duplicate Guard:**  
   Attempting to grant a duplicate non-stackable item returns `HTTP 400 Bad Request` (`"Item is non-stackable and character already owns it"`).
6. **Input Validation & Trimming:**  
   Empty or whitespace-only strings for `reason` or `idempotency_key` are rejected with `HTTP 422 Unprocessable Entity`. Input text fields are automatically trimmed.
7. **Idempotency Deduplication:**  
   Exact replays return the original transaction with `HTTP 200 OK` without double-crediting. Conflicting replays using the same key return `HTTP 409 Conflict`.
8. **Atomic Concurrency via Native Upsert & Atomic Expressions:**  
   - Grants utilize database-level `INSERT ... ON CONFLICT (character_gid, item_id) DO UPDATE SET quantity = quantity + :amount RETURNING quantity`.
   - Removals utilize atomic `DELETE` (when quantity reaches zero) or `UPDATE ... WHERE quantity > :amount RETURNING quantity`.

---

## 6. Migration Safety & Strategy

The migration script [`migrations/004_add_inventory_system.sql`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/migrations/004_add_inventory_system.sql) has been created.

- **Non-Destructive DDL:**  
  Creates `items`, `inventory_items`, and `inventory_transactions` tables with indexes and constraints.
- **Zero Production Execution:**  
  In compliance with project safety rules, this migration was **not executed against any real or production database**. It executes only against ephemeral in-memory test databases.
- **Preservation of Existing JSON:**  
  Existing `Character.appearances` columns and records are completely preserved. If future migration from legacy JSON to relational inventory is required, a reversible ETL migration script can be run without service downtime.

---

## 7. Automated Test Suite Results

The full test suite was executed across all 15 test modules:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server
configfile: pytest.ini
plugins: anyio-4.16.0, platformdirs-4.13.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collected 123 items

tests\test_account.py ....                                               [  3%]
tests\test_admin_bootstrap_cli.py ..........                             [ 11%]
tests\test_admin_rbac.py ...........                                     [ 20%]
tests\test_diamond_concurrency.py ......                                 [ 25%]
tests\test_diamond_ledger.py ................                            [ 38%]
tests\test_discovery.py ..............                                   [ 49%]
tests\test_gateway_adapter.py .....                                      [ 53%]
tests\test_handshake.py ......                                           [ 58%]
tests\test_inventory.py ........                                         [ 65%]
tests\test_lobby.py ..                                                   [ 66%]
tests\test_matchmaking.py ..                                             [ 68%]
tests\test_mercury_protocol.py ................                          [ 81%]
tests\test_mercury_transport.py .......                                  [ 86%]
tests\test_player.py ...                                                 [ 89%]
tests\test_remediation.py ............                                   [ 99%]
tests\test_room.py .                                                     [100%]

============================ 123 passed in 24.25s =============================
```

### Breakdown of New Inventory Tests ([`tests/test_inventory.py`](file:///C:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/test_inventory.py))
1. `test_admin_create_and_manage_catalog_items`: Tests catalog creation, code uniqueness (409), attribute patch updates, and catalog filtering.
2. `test_inventory_rbac_protection`: Tests that 401/403 protections block unauthorized catalog and inventory access while allowing player self-view.
3. `test_inventory_grant_and_remove_flow`: Full lifecycle test verifying non-stackable grant, duplicate non-stackable rejection, stackable accumulation, max stack overflow rejection, partial removal, overdraft rejection, and removal to zero with slot deletion.
4. `test_inventory_idempotency_and_validation`: Tests exact idempotency replays (200), parameter conflict replays (409), and whitespace-only rejection (422).
5. `test_concurrent_inventory_grants_and_removals`: Multi-connection concurrency test on isolated file database using `asyncio.gather` asserting safe parallel grant accumulation and overdraft rejection under contention.
6. `test_inventory_history_ordering_and_pagination`: Validates newest-first sorting and limit/offset pagination on inventory history.
7. `test_invalid_item_or_character_ids_rejected`: Validates HTTP 404 for operations referencing non-existent characters or items.
8. `test_database_check_constraints_prevent_invalid_inventory_records`: Validates that database-level check constraints reject invalid stack limits and negative quantities.

---

## 8. Database Engine Status

- **SQLite:** **100% VERIFIED** via `aiosqlite` and SQLite 3.45.1. Both single-connection in-memory tests and multi-connection concurrency tests pass.
- **PostgreSQL:** **CODE-REVIEWED & DOCUMENTED (Live Driver Unavailable)**. Native PostgreSQL dialect compilation for `INSERT ... ON CONFLICT DO UPDATE RETURNING` and `UPDATE ... RETURNING` was verified. Live execution requires installing `asyncpg` or `psycopg` in the Python environment.

---

## 9. Remaining Limitations & Next Steps

1. **Player Item Consumption / Purchase Flow:**  
   Players currently cannot spend diamonds to purchase items directly from the catalog. This flow will be implemented in Phase 6.2A.4 (Player Store & Item Purchase Engine).
2. **Cosmetic Equipping Integration:**  
   Equipping a clothing item or weapon skin currently updates the JSON `Character.appearances` field. Tying equipped status to relational inventory item ownership will be finalized during the character loadout phase.

---

## 10. Conclusion & Approval Gate

Phase 6.2A.3 is **fully implemented and verified**. All 123 tests pass.

Awaiting operator review and approval before proceeding to:
- **Phase 6.2A.4: Private-Room Lifecycle and Matchmaking Improvements** (or Player Store & Item Purchase Engine).
