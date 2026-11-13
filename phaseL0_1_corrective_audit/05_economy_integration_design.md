# ROS Sothat — Phase L0.1 Audit Deliverable 5
## Economy Integration Design: Admin Dashboard to Game Client

**Phase:** Phase L0.1 (Corrective Audit & Master Architecture)  
**Audit Target:** End-to-End Economy Synchronization Pipeline  
**Audit Date:** 2026-11-13  
**Status:** COMPLETE — INTEGRATION SPECIFICATION & GAP ANALYSIS  

---

### 1. Executive Summary

This report defines the end-to-end technical pipeline governing how administrative economy actions (such as granting diamonds or items from the Admin Dashboard) propagate from the web platform to the player's wallet and ultimately into the running original Rules of Survival Legacy game client.

### Core Architectural Principle:
> **DATABASE CHANGES DO NOT AUTOMATICALLY APPEAR IN THE GAME CLIENT.**  
> Updating a row in the relational database updates the player's persistent wallet balance. However, the original game client does not poll or communicate with REST/SQL databases. It communicates strictly via **Mercury UDP RPC messages** with the game server (`BaseApp`). For diamonds to be visible in the game UI, the game server must synchronize the updated balance to the client over the native Mercury entity property protocol.

---

### 2. End-to-End 7-Stage Propagation Lifecycle

Below is the concrete lifecycle of an economy transaction:

```
+---------------------------------------------------------------------------------------------------------------+
|                                      7-STAGE ECONOMY PROPAGATION LIFECYCLE                                    |
+---------------------------------------------------------------------------------------------------------------+
|                                                                                                               |
|  [ STAGE 1: ADMIN ACTION ]                                                                                    |
|  Administrator logs into Admin Dashboard, searches for Player "PlayerOne" (Account ID 1001, GID 5001),        |
|  inputs "+1,000 Diamonds", selects Reason: "Tournament Reward", and clicks [ Confirm Grant ].                 |
|                                                                                                               |
|                                  |                                                                            |
|                                  v                                                                            |
|  [ STAGE 2: RBAC AUTHORIZATION & VALIDATION ]                                                                 |
|  FastAPI endpoint `POST /api/v1/admin/characters/5001/diamonds/grant` validates:                             |
|  1. Bearer JWT token belongs to an active Admin account (role == "admin" or "superadmin").                    |
|  2. Target character exists and is not banned.                                                               |
|  3. Delta amount is positive integer (amount > 0).                                                           |
|                                                                                                               |
|                                  |                                                                            |
|                                  v                                                                            |
|  [ STAGE 3: ACID DATABASE TRANSACTION & AUDIT LOG ]                                                           |
|  `EconomyService.grant_diamonds()` initiates a relational database transaction:                              |
|  1. `SELECT * FROM character_wallets WHERE character_gid = 5001 FOR UPDATE;` (Row-level lock).                |
|  2. Balance is incremented: `balance_after = balance_before + 1000`.                                          |
|  3. Writes immutable record to `diamond_transactions`:                                                        |
|     - `character_gid = 5001`, `admin_account_id = admin.id`, `amount = 1000`, `reason = "Tournament Reward"`|
|  4. Commits SQL transaction.                                                                                  |
|                                                                                                               |
|                                  |                                                                            |
|                                  v                                                                            |
|  [ STAGE 4: PLAYER WALLET & DASHBOARD UPDATE ]                                                                |
|  The player's persistent record is updated. If the player refreshes their web Player Dashboard,              |
|  the new balance (e.g. 2,000 diamonds) is immediately reflected via `GET /api/v1/player/character`.          |
|                                                                                                               |
|                                  |                                                                            |
|                                  v                                                                            |
|  [ STAGE 5: GAME SERVER (BaseApp) NOTIFICATION / RETRIEVAL ]                                                  |
|  Case A: Player is OFFLINE:                                                                                   |
|  - The updated balance remains safely in the database.                                                        |
|  - When the player next connects to BaseApp, BaseApp reads `character_wallets` during entity instantiation.   |
|  Case B: Player is ONLINE:                                                                                    |
|  - FastAPI publishes an internal IPC notification (via Redis pub/sub or local socket) to BaseApp:            |
|    `{"event": "DIAMOND_UPDATE", "character_gid": 5001, "new_balance": 2000}`                                 |
|  - BaseApp updates the in-memory Entity property: `playerEntity.diamonds = 2000`.                            |
|                                                                                                               |
|                                  |                                                                            |
|                                  v                                                                            |
|  [ STAGE 6: NATIVE MERCURY ENTITY SYNCHRONIZATION ]                                                           |
|  BaseApp packages a BigWorld entity property update datagram:                                                 |
|  - Message ID: `updateEntityProperty` (or `set_diamonds` entity call).                                        |
|  - Encrypted using the active session's 56-byte Blowfish session key.                                         |
|  - Transmitted over UDP port 20014 to the client's socket.                                                     |
|                                                                                                               |
|                                  |                                                                            |
|                                  v                                                                            |
|  [ STAGE 7: CLIENT UI DISPLAY ]                                                                               |
|  The genuine iOS client receives the UDP datagram:                                                            |
|  - BigWorld Python script engine (`scripts/entities/avatar.pyc`) receives property change event.              |
|  - UI script (`scripts/ui/UIMall.pyc` / `UITopBar.pyc`) updates the diamond icon text counter to "2,000".   |
|                                                                                                               |
+---------------------------------------------------------------------------------------------------------------+
```

---

### 3. Implementation Gap Analysis: Existing Backend vs Native Game Server

```
+-----------------------------------------------------------------------------------------------+
|                                 ECONOMY IMPLEMENTATION AUDIT MATRIX                           |
+-----------------------------------+-------------------+---------------------------------------+
| Pipeline Component                | Current Status    | Implementation Location               |
+-----------------------------------+-------------------+---------------------------------------+
| 1. Admin RBAC & JWT Verification  | **IMPLEMENTED**   | `app/account/service.py:126`          |
|                                   |                   | `app/admin/router.py:156`             |
+-----------------------------------+-------------------+---------------------------------------+
| 2. Row-Level Locking (Concurrency)| **IMPLEMENTED**   | `app/economy/repository.py:44`        |
|    (SELECT FOR UPDATE in SQLite/PG)|                  | ACID concurrency tested.              |
+-----------------------------------+-------------------+---------------------------------------+
| 3. Immutable Transaction Ledger   | **IMPLEMENTED**   | `app/economy/models.py:35`            |
|    (diamond_transactions table)   |                   | Auditable history stored.             |
+-----------------------------------+-------------------+---------------------------------------+
| 4. Player Dashboard REST API      | **IMPLEMENTED**   | `app/player/router.py:20`             |
|                                   |                   | Returns character profile & wallet.   |
+-----------------------------------+-------------------+---------------------------------------+
| 5. IPC Bridge (FastAPI -> BaseApp)| **MISSING**       | Requires Redis pub/sub or internal    |
|    (Online Player Notification)   |                   | IPC socket in Phase 14 / L2.          |
+-----------------------------------+-------------------+---------------------------------------+
| 6. BaseApp In-Memory Entity Sync  | **MISSING**       | BaseApp entity definition & Mercury   |
|    (Entity Property Management)   |                   | property serializer deferred to Ph 14.|
+-----------------------------------+-------------------+---------------------------------------+
| 7. Client Script Event Binding    | **REVERSE ENGIN.**| Disassembly of `extracted/scripts/`   |
|    (UI Refresh in Client)         |                   | identifies `UIMall` & `DtsAccount`.   |
+-----------------------------------+-------------------+---------------------------------------+
```

---

### 4. Critical Engineering Realities

1. **Never Conflate Web Balances with Client Balances:**
   A player who receives diamonds via the Admin Dashboard while playing will not see their in-game diamond counter increment unless the game server issues a Mercury property update packet to their client.
2. **Offline Player Safety:**
   Because all wallet balances are persisted in the database, offline players are completely safe. When the player next initiates a login handshake, BaseApp loads the latest balance directly from the database during character attachment.
3. **Double-Spend Prevention:**
   Purchases in the game shop (e.g. buying a skin) must be verified and deducted through BaseApp by querying the database ledger with row locks, preventing in-memory balance desynchronization.
