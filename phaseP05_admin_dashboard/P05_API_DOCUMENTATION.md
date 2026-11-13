# ROS Sothat — Phase P05: Secure Admin Dashboard
## REST API Specification & Reference Manual

**Base URL:** `http://127.0.0.1:8000/api/v1`  
**Authentication Scheme:** HTTP Bearer JWT  
**Role Requirement:** `admin` (enforced via database `accounts.role == "admin"`)  
**Security Headers:** `Authorization: Bearer <token>`  

---

## 1. Overview & Response Codes

All administrative endpoints require a valid administrative Bearer token. Requests from unauthenticated clients return `401 Unauthorized`. Requests from authenticated players return `403 Forbidden`.

| HTTP Status | Meaning | Scenario |
|---|---|---|
| `200 OK` | Success | Query, inspection, or mutation succeeded. |
| `201 Created` | Created | New item or resource successfully created. |
| `400 Bad Request` | Validation Error | Negative/zero amount, missing reason, or invalid status transition. |
| `401 Unauthorized` | Auth Failure | Missing, expired, or invalid Bearer token. |
| `403 Forbidden` | Access Denied | Requester is a regular player or account is banned. |
| `404 Not Found` | Resource Missing | Account or Character ID does not exist. |
| `409 Conflict` | Idempotency / State | Idempotency key reused with mismatched parameters or duplicate resource. |

---

## 2. Administrative Endpoints Reference

### 2.1 Admin Session & Profile
```http
GET /api/v1/admin/me
```
* **Description:** Verifies caller admin authorization and returns current administrator details.
* **Response (200 OK):**
```json
{
  "id": 1,
  "username": "admin_root",
  "email": "admin@rossothat.local",
  "role": "admin",
  "is_banned": false,
  "created_at": "2026-11-13T10:00:00Z",
  "last_login": "2026-11-13T22:30:00Z",
  "has_character": true
}
```

---

### 2.2 Dashboard Overview Summary
```http
GET /api/v1/admin/dashboard/summary
```
* **Description:** Retrieves real-time aggregate server counts, active operational metrics, and the latest 8 administrative audit logs.
* **Response (200 OK):**
```json
{
  "total_accounts": 15,
  "active_accounts": 14,
  "suspended_accounts": 1,
  "total_characters": 12,
  "total_diamonds": 18500,
  "total_inventory_items": 84,
  "active_lobby_presences": 0,
  "active_rooms": 0,
  "queued_matchmaking_tickets": 0,
  "recent_activity": [
    {
      "id": 105,
      "admin_account_id": 1,
      "admin_username": "admin_root",
      "action_type": "DIAMOND_GRANT",
      "target_type": "character",
      "target_id": 2,
      "reason": "Bug bounty compensation",
      "details": {
        "amount": 500,
        "balance_before": 100,
        "balance_after": 600,
        "idempotency_key": "grant-20261113-001"
      },
      "created_at": "2026-11-13T22:45:10Z"
    }
  ]
}
```

---

### 2.3 Player Directory Search & Pagination
```http
GET /api/v1/admin/players?q={term}&is_banned={bool}&limit={n}&offset={m}
```
* **Parameters:**
  * `q` (Optional, string): Substring match on username, email, or character nickname; exact match on numeric Account ID.
  * `is_banned` (Optional, boolean): Filter by suspension status (`true` or `false`).
  * `limit` (Optional, int, default 50, max 100): Page limit.
  * `offset` (Optional, int, default 0): Record offset.
* **Response (200 OK):**
```json
{
  "total": 1,
  "limit": 50,
  "offset": 0,
  "players": [
    {
      "account_id": 2,
      "username": "alpha_warrior",
      "email": "warrior@rossothat.local",
      "role": "player",
      "is_banned": false,
      "ban_reason": null,
      "created_at": "2026-11-13T12:00:00Z",
      "last_login": "2026-11-13T20:15:00Z",
      "character_gid": 1,
      "character_nickname": "AlphaGhost",
      "character_level": 5,
      "diamonds": 600
    }
  ]
}
```

---

### 2.4 Player Detailed Inspection
```http
GET /api/v1/admin/players/{player_id}?lookup={account|gid}
```
* **Parameters:**
  * `player_id` (Path, int): Account ID or Character GID.
  * `lookup` (Optional, string): Mode (`account` or `gid`). Defaults to account with GID fallback.
* **Response (200 OK):**
```json
{
  "account_id": 2,
  "username": "alpha_warrior",
  "email": "warrior@rossothat.local",
  "role": "player",
  "is_banned": false,
  "ban_reason": null,
  "created_at": "2026-11-13T12:00:00Z",
  "last_login": "2026-11-13T20:15:00Z",
  "character": {
    "gid": 1,
    "nickname": "AlphaGhost",
    "char_type": 0,
    "level": 5,
    "exp": 1250,
    "gold": 25000,
    "diamonds": 600,
    "appearances": {
      "equipped_clothing": [10001],
      "unlocked_items": [10001],
      "active_weapon_skin": 0
    },
    "settings": {
      "fov": 75,
      "control_mode": 1
    },
    "stats": {
      "total_matches": 12,
      "total_wins": 3,
      "total_kills": 24
    }
  },
  "inventory_items": [
    {
      "id": 14,
      "item_id": 10001,
      "quantity": 1,
      "item_name": "Tactical Camo Jacket",
      "item_type": "clothing",
      "stackable": false,
      "max_stack": 1,
      "is_active": true
    }
  ],
  "recent_diamond_transactions": [
    {
      "id": 44,
      "operation_type": "GRANT",
      "amount": 500,
      "balance_before": 100,
      "balance_after": 600,
      "reason": "Bug bounty reward",
      "created_at": "2026-11-13T22:45:10Z"
    }
  ],
  "recent_audit_logs": []
}
```

---

### 2.5 Account Suspension
```http
POST /api/v1/admin/players/{player_id}/suspend
```
* **Request Body:**
```json
{
  "reason": "Exploiting map boundaries during match"
}
```
* **Response (200 OK):** Returns updated `AdminPlayerSummary` with `is_banned: true`.
* **Guards:** Prevents self-suspension (`400 Bad Request`). Prevents redundant suspension (`400 Bad Request`).

---

### 2.6 Account Reactivation
```http
POST /api/v1/admin/players/{player_id}/reactivate
```
* **Request Body:**
```json
{
  "reason": "Appeal accepted following verification"
}
```
* **Response (200 OK):** Returns updated `AdminPlayerSummary` with `is_banned: false`.

---

### 2.7 Atomic Diamond Grant
```http
POST /api/v1/admin/players/{player_id}/diamonds/grant
```
* **Request Body:**
```json
{
  "amount": 250,
  "reason": "Community tournament participation reward",
  "idempotency_key": "grant-tx-1002"
}
```
* **Response (200 OK):**
```json
{
  "id": 45,
  "character_gid": 1,
  "admin_account_id": 1,
  "operation_type": "GRANT",
  "amount": 250,
  "balance_before": 600,
  "balance_after": 850,
  "idempotency_key": "grant-tx-1002",
  "reason": "Community tournament participation reward",
  "created_at": "2026-11-13T22:50:00Z"
}
```

---

### 2.8 Atomic Diamond Deduction
```http
POST /api/v1/admin/players/{player_id}/diamonds/deduct
```
* **Request Body:**
```json
{
  "amount": 100,
  "reason": "Tournament penalty",
  "idempotency_key": "deduct-tx-1002"
}
```
* **Response (200 OK):** Returns transaction record with `balance_after: 750`.
* **Guard:** Rejects with `400 Bad Request` if `balance < amount` (insufficient funds / overdraft protection).

---

### 2.9 Inventory Item Grant
```http
POST /api/v1/admin/players/{player_id}/inventory/grant
```
* **Request Body:**
```json
{
  "item_id": 10001,
  "quantity": 1,
  "reason": "Reward distribution",
  "idempotency_key": "inv-grant-202"
}
```
* **Response (200 OK):**
```json
{
  "id": 18,
  "character_gid": 1,
  "item_id": 10001,
  "admin_account_id": 1,
  "operation_type": "GRANT",
  "quantity": 1,
  "quantity_before": 0,
  "quantity_after": 1,
  "reason": "Reward distribution",
  "idempotency_key": "inv-grant-202",
  "created_at": "2026-11-13T22:52:00Z"
}
```

---

### 2.10 Inventory Item Removal
```http
POST /api/v1/admin/players/{player_id}/inventory/remove
```
* **Request Body:**
```json
{
  "item_id": 10001,
  "quantity": 1,
  "reason": "Item revocation",
  "idempotency_key": "inv-rem-202"
}
```
* **Equipped Item Safeguard:** If quantity drops to 0, `InventoryService` automatically un-equips the item from `appearances["equipped_clothing"]` in the same transaction.

---

### 2.11 Persistent Administrative Audit Logs
```http
GET /api/v1/admin/audit-logs?admin_id={id}&target_id={id}&action_type={type}&limit={n}&offset={m}
```
* **Filters:**
  * `admin_id` (Optional, int): Filter by administrator ID.
  * `target_id` (Optional, int): Filter by target Account ID or Character GID.
  * `action_type` (Optional, string): Filter by action (`DIAMOND_GRANT`, `DIAMOND_DEDUCT`, `INVENTORY_GRANT`, `INVENTORY_REMOVE`, `ACCOUNT_SUSPEND`, `ACCOUNT_REACTIVATE`, `ROLE_CHANGE`).
  * `limit` (Optional, int, default 50)
  * `offset` (Optional, int, default 0)
* **Response (200 OK):**
```json
{
  "total": 14,
  "limit": 50,
  "offset": 0,
  "logs": [
    {
      "id": 1,
      "admin_account_id": 1,
      "admin_username": "admin_root",
      "action_type": "ACCOUNT_SUSPEND",
      "target_type": "account",
      "target_id": 2,
      "reason": "Suspected speed hacking",
      "details": {
        "previous_state": "active",
        "username": "alpha_warrior"
      },
      "created_at": "2026-11-13T22:47:00Z"
    }
  ]
}
```
