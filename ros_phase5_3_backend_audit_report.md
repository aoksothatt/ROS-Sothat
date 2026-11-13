# Phase 5.3 — Read-Only Backend Audit Report

**Date**: November 11, 2026  
**Auditor**: Antigravity (Advanced Agentic Coding Assistant)  
**Target Project**: `ros-private-server/` (ROS Legacy Private Backend Prototype)  
**Scope**: Comprehensive read-only audit of project structure, database safety, Phase 5.2 remediations, API inventory, game feature readiness, test results, and iOS client compatibility.  
**Mode**: Strict READ-ONLY audit. No source code, database records, or original IPA assets were modified.

---

## 1. Executive Summary

This Phase 5.3 audit independently inspects the current state of the independent Rules of Survival (ROS) Legacy private server foundation. 

### Key Audit Conclusions
1. **Remediation Integrity**: All six critical and high-priority fixes claimed in the Phase 5.2 remediation report (SEC-01 through SEC-06) have been verified directly in the source code and are actively enforced and tested.
2. **Test Suite Health**: All 24 automated unit and integration tests passed cleanly in **3.86 seconds** (`24 passed, 0 failed, 0 skipped`).
3. **Database State & Safety**: The configured default database `ros_private.db` **does not exist yet on disk**; tests run exclusively in-memory (`:memory:`) with zero persistent disk footprint. Migration `001_add_device_id.sql` is well-formed, non-destructive, and has not been executed against any persistent store.
4. **Game Feature Readiness**: Core web/backend infrastructure (account authentication, guest identity persistence, player profiles, custom rooms, and matchmaking queues) is **implemented and tested**. In-game item catalogs, administrator diamond grants, and real-time battle gameplay simulation remain **not implemented or partially implemented**.
5. **iOS Compatibility Reality Check**: The existing backend is a **pure HTTP/REST API** service. The original ROS Legacy iOS client communicates using NetEase UniSDK (HTTPS) for authentication and BigWorld **Mercury UDP packets** for lobby, entity RPCs, inventory, and battle simulation. **The original iOS client cannot natively connect to this REST backend without an intermediary Mercury protocol bridge or client patch.**

---

## 2. Project Architecture & Structure

The backend foundation is implemented in **Python 3.11** using **FastAPI**, **AsyncIO**, and **SQLAlchemy 2.0**.

### 2.1 Complete Directory Layout
```
ros-private-server/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings, env variables, rate limits & TTLs
│   ├── logging_config.py         # Standardized logging setup
│   ├── main.py                   # FastAPI app, lifespan, worker guard & periodic cleanup
│   │
│   ├── database/                 # SQLAlchemy AsyncIO layer
│   │   ├── __init__.py
│   │   ├── base.py               # DeclarativeBase class
│   │   └── session.py            # Async engine, sessionmaker & init_db
│   │
│   ├── account/                  # Account & Authentication module
│   │   ├── __init__.py
│   │   ├── models.py             # Account ORM entity (includes device_id)
│   │   ├── schemas.py            # AccountRegister, AccountLogin, GuestRegister, TokenResponse
│   │   ├── repository.py         # Account CRUD operations
│   │   ├── service.py            # PBKDF2 password hashing & HMAC token issuance
│   │   ├── rate_limiter.py       # Sliding-window in-memory rate limiter (SEC-06)
│   │   └── router.py             # /api/v1/account endpoints
│   │
│   ├── player/                   # Character Profile module
│   │   ├── __init__.py
│   │   ├── models.py             # Character ORM entity (cosmetics, settings, stats)
│   │   ├── schemas.py            # Pydantic schemas with strict payload validators (SEC-05)
│   │   ├── repository.py         # Character database queries
│   │   ├── service.py            # Character creation & profile management
│   │   └── router.py             # /api/v1/player endpoints
│   │
│   ├── lobby/                    # Lobby Presence module
│   │   ├── __init__.py
│   │   ├── models.py             # PlayerPresence dataclass
│   │   ├── schemas.py            # Lobby status & online listing schemas
│   │   ├── service.py            # In-memory presence tracking & timeout cascade (SEC-04)
│   │   └── router.py             # /api/v1/lobby endpoints
│   │
│   ├── room/                     # Custom Room module
│   │   ├── __init__.py
│   │   ├── models.py             # Room & RoomMember dataclasses
│   │   ├── schemas.py            # Room request/response schemas
│   │   ├── service.py            # Room lifecycle, host migration & stale room pruning (SEC-03)
│   │   └── router.py             # /api/v1/room endpoints
│   │
│   └── matchmaking/              # Matchmaking Engine module
│       ├── __init__.py
│       ├── schemas.py            # Queue tickets & match response schemas
│       ├── service.py            # Pairing engine, ticket TTL & queue timeout pruning (SEC-03)
│       └── router.py             # /api/v1/matchmaking endpoints
│
├── migrations/                   # SQL migration scripts
│   └── 001_add_device_id.sql     # Non-destructive schema migration for SEC-02
│
├── tests/                        # Automated Pytest suite (24 tests)
│   ├── __init__.py
│   ├── conftest.py               # In-memory DB fixture & test dependency overrides
│   ├── test_account.py           # Account registration, login & token tests (4 tests)
│   ├── test_player.py            # Character creation & profile tests (3 tests)
│   ├── test_lobby.py             # Lobby presence & heartbeat tests (2 tests)
│   ├── test_room.py              # Custom room lifecycle tests (1 test)
│   ├── test_matchmaking.py       # Pairing engine tests (2 tests)
│   └── test_remediation.py       # Phase 5.2 security & edge-case tests (12 tests)
│
├── pytest.ini                    # Pytest AsyncIO configuration
├── requirements.txt              # Core Python dependencies
└── README.md                     # Deployment and architecture manual
```

### 2.2 Dependencies & Configurations
- **FastAPI** (`0.110.0+`): Primary async web framework.
- **Uvicorn** (`0.28.0+`): ASGI server.
- **SQLAlchemy** (`2.0.0+`) & **Greenlet** (`3.0.0+`): Modern asynchronous ORM.
- **aiosqlite** (`0.20.0+`): SQLite asynchronous database driver (development default).
- **asyncpg** (`0.29.0+`): PostgreSQL asynchronous driver (production optional).
- **Pydantic** (`2.6.0+`): Data validation and settings management.
- **Pytest** (`8.0.0+`) & **pytest-asyncio** (`0.23.0+`): Automated test harness.

---

## 3. Database Configuration & Safety Findings

### 3.1 Database Engine & Location
- **Configured Engine**: SQLAlchemy 2.0 AsyncEngine.
- **Default Database URL**: `sqlite+aiosqlite:///./ros_private.db` (configured via `app/config.py`).
- **Disk State**: **`ros_private.db` does not currently exist on disk.** The SQLite file is only created when the server is booted via `uvicorn app.main:app`. During all test runs, tests override the connection to use in-memory SQLite (`sqlite+aiosqlite:///:memory:`).
- **Database Safety Compliance**: No databases were created, deleted, reset, or altered during this audit.

### 3.2 Models and Schema Relationships
1. **`Account` (`accounts` table)**:
   - Primary Key: `id` (`Integer`, autoincrement, indexed).
   - `username`: `String(64)`, unique, indexed, non-null.
   - `device_id`: `String(64)`, unique, indexed, nullable (supports guest identity persistence).
   - `password_hash`: `String(128)`, non-null.
   - `salt`: `String(64)`, non-null.
   - `is_banned`: `Boolean`, default `False`.
   - `ban_reason`: `String(255)`, nullable.
   - `created_at`: `DateTime`, non-null.
   - `last_login`: `DateTime`, nullable.
   - Relationship: One-to-one with `Character` (`uselist=False`, `cascade="all, delete-orphan"`).
2. **`Character` (`characters` table)**:
   - Primary Key: `gid` (`BigInteger().with_variant(Integer, "sqlite")`, autoincrement, indexed).
   - `account_id`: `Integer`, foreign key to `accounts.id`, unique, indexed, non-null.
   - `nickname`: `String(64)`, unique, indexed, non-null.
   - `char_type`: `Integer` (0: Male, 1: Female), default 0.
   - `level`: `Integer`, default 1.
   - `exp`: `Integer`, default 0.
   - `gold`: `BigInteger`, default 1,000.
   - `diamonds`: `BigInteger`, default 100.
   - `appearances`: `JSON`, non-null (stores equipped clothing and weapon skins).
   - `settings`: `JSON`, non-null (stores control mode, FOV, sensitivity).
   - `stats`: `JSON`, non-null (stores matches, wins, kills, damage).
   - `created_at` / `updated_at`: `DateTime`.

### 3.3 Migration `001_add_device_id.sql` Review
- The migration file [`migrations/001_add_device_id.sql`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/migrations/001_add_device_id.sql) contains non-destructive `ALTER TABLE` statements:
  - SQLite: `ALTER TABLE accounts ADD COLUMN device_id VARCHAR(64); CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_device_id ON accounts (device_id);`
  - PostgreSQL: `ALTER TABLE accounts ADD COLUMN IF NOT EXISTS device_id VARCHAR(64) UNIQUE; CREATE INDEX IF NOT EXISTS ix_accounts_device_id ON accounts (device_id);`
- **Execution Policy**: Migrations are **NOT automatically executed** on startup. Startup relies solely on `Base.metadata.create_all`, which creates non-existent tables but does not alter existing tables.
- **SQLite vs. PostgreSQL Compatibility**:
  - SQLite compatibility is maintained via `BigInteger().with_variant(Integer, "sqlite")` for primary key autoincrement.
  - PostgreSQL compatibility is supported with native `BIGINT` and `JSON` types.
  - *Observation*: In SQLite runtime connections, `PRAGMA foreign_keys = ON;` is not yet registered via an engine event listener.

---

## 4. Phase 5.2 Verification

Each of the six remediations claimed in Phase 5.2 was independently verified against the actual source code and automated test execution:

| Issue ID | Remediation Claim | Code Verification Findings | Associated Test(s) | Status |
|---|---|---|---|---|
| **SEC-01** | Single-worker deployment safeguard | In [`app/main.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/main.py), `validate_single_worker_configuration()` checks environment variables (`WEB_CONCURRENCY`, `UVICORN_WORKERS`, `WORKERS`) during lifespan startup and raises a `RuntimeError` if workers > 1. | `test_single_worker_deployment_safeguard` | **VERIFIED** |
| **SEC-02** | Guest account persistence & concurrency | In [`app/account/models.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/account/models.py) and [`app/account/service.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/account/service.py), `device_id` is persisted with unique constraint. Returning guests retrieve existing profiles; concurrent registration races catch `IntegrityError` and safely recover the existing account. | `test_guest_registration_and_returning_login`, `test_different_device_ids_create_different_accounts`, `test_concurrent_guest_registration_same_device_id` | **VERIFIED** |
| **SEC-03** | Ephemeral memory leak & room/ticket pruning | In [`app/matchmaking/service.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/matchmaking/service.py) (`cleanup_expired_tickets`) and [`app/room/service.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/room/service.py) (`cleanup_stale_rooms`), tickets and rooms are pruned based on UTC elapsed time. A background loop in [`app/main.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/main.py) executes cleanup every 15s. | `test_expired_ticket_cleanup`, `test_expired_room_cleanup`, `test_active_rooms_and_valid_tickets_surviving_cleanup` | **VERIFIED** |
| **SEC-04** | Disconnected player cascade cleanup | In [`app/lobby/service.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/lobby/service.py) (`cleanup_stale_presences`), expired heartbeats cascade to `RoomService.handle_player_disconnect()` and `MatchmakingService.handle_player_disconnect()`, leaving rooms, migrating hosts, and timing out matchmaking tickets. | `test_disconnected_player_cleanup_from_rooms`, `test_disconnected_player_cleanup_from_matchmaking` | **VERIFIED** |
| **SEC-05** | Input validation on settings & appearances | In [`app/player/schemas.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/player/schemas.py), `@field_validator` blocks payloads > 16 KB, limits key counts (≤30 settings, ≤20 cosmetics), restricts key names to identifiers, bounds string lengths, and restricts item lists to ≤50 positive integers. | `test_oversized_and_malformed_appearance_settings_payload_rejection` | **VERIFIED** |
| **SEC-06** | In-memory sliding-window rate limiting | In [`app/account/rate_limiter.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/app/account/rate_limiter.py), `InMemoryRateLimiter` enforces limits on `/account/login` (5/min) and `/account/register` (3/min), returning HTTP 429 with `Retry-After` headers. | `test_login_rate_limiting`, `test_registration_rate_limiting` | **VERIFIED** |

---

## 5. Existing API Endpoint Inventory

The server exposes **25 distinct HTTP endpoints**:

| Method | Endpoint | Module | Auth Required | Purpose | Request Schema | Response Schema | Status |
|---|---|---|---|---|---|---|---|
| `GET` | `/health` | Health | None | Service heartbeat & healthcheck | None | JSON `{"status": "online", ...}` | Complete |
| `POST` | `/api/v1/account/register` | Account | None (Rate Limited) | Register standard account | `AccountRegister` (username, password) | `AccountOut` | Complete |
| `POST` | `/api/v1/account/login` | Account | None (Rate Limited) | Authenticate user & issue Bearer token | `AccountLogin` (username, password) | `TokenResponse` | Complete |
| `POST` | `/api/v1/account/guest` | Account | None (Rate Limited) | Instant guest registration / resumption | `GuestRegister` (device_id) | `TokenResponse` | Complete |
| `GET` | `/api/v1/account/me` | Account | Bearer Token | Retrieve authenticated account info | None | `AccountOut` | Complete |
| `POST` | `/api/v1/player/character` | Player | Bearer Token | Create initial character profile | `CharacterCreate` (nickname, char_type) | `CharacterOut` | Complete |
| `GET` | `/api/v1/player/character` | Player | Bearer Token | Retrieve own character profile | None | `CharacterOut` | Complete |
| `GET` | `/api/v1/player/{gid}` | Player | None | Retrieve public profile by GID | Path `gid: int` | `CharacterPublicProfile` | Complete |
| `PUT` | `/api/v1/player/character/settings` | Player | Bearer Token | Update gameplay/control settings | `CharacterUpdateSettings` (validated dict) | `CharacterOut` | Complete |
| `PUT` | `/api/v1/player/character/appearances` | Player | Bearer Token | Update cosmetics/outfit loadout | `CharacterUpdateAppearances` (validated dict) | `CharacterOut` | Complete |
| `POST` | `/api/v1/lobby/enter` | Lobby | Bearer Token | Register presence in active lobby | None (requires character) | `LobbyEnterResponse` | Complete |
| `POST` | `/api/v1/lobby/heartbeat` | Lobby | Bearer Token | Keep player presence alive | None | `HeartbeatResponse` | Complete |
| `GET` | `/api/v1/lobby/online` | Lobby | None | List active online players | Query parameters | `LobbyOnlineListResponse` | Complete |
| `POST` | `/api/v1/lobby/leave` | Lobby | Bearer Token | Leave lobby and mark offline | None | JSON message | Complete |
| `POST` | `/api/v1/room/create` | Room | Bearer Token | Create new custom room | `RoomCreateRequest` (name, map, capacity, mode, pwd) | `RoomOut` | Complete |
| `GET` | `/api/v1/room/list` | Room | None | List open custom rooms | Query `public_only: bool` | `RoomListResponse` | Complete |
| `GET` | `/api/v1/room/{room_id}` | Room | None | Get specific room details | Path `room_id: str` | `RoomOut` | Complete |
| `POST` | `/api/v1/room/{room_id}/join` | Room | Bearer Token | Join custom room (with pwd check) | `RoomJoinRequest` (optional pwd) | `RoomOut` | Complete |
| `POST` | `/api/v1/room/{room_id}/leave` | Room | Bearer Token | Leave custom room | Path `room_id: str` | JSON message | Complete |
| `POST` | `/api/v1/room/{room_id}/ready` | Room | Bearer Token | Toggle member ready state | Query `is_ready: bool` | `RoomOut` | Complete |
| `POST` | `/api/v1/room/{room_id}/kick/{target_gid}` | Room | Bearer Token | Host kick member from room | Path `room_id`, `target_gid` | `RoomOut` | Complete |
| `POST` | `/api/v1/room/{room_id}/start` | Room | Bearer Token | Host launch match & generate token | Path `room_id: str` | `RoomStartResponse` | Complete |
| `POST` | `/api/v1/matchmaking/queue` | Matchmaking | Bearer Token | Enqueue into matchmaking pool | `MatchQueueRequest` (mode, region) | `MatchTicketResponse` | Complete |
| `GET` | `/api/v1/matchmaking/ticket/{ticket_id}` | Matchmaking | Bearer Token | Poll match ticket status | Path `ticket_id: str` | `MatchStatusResponse` | Complete |
| `POST` | `/api/v1/matchmaking/cancel/{ticket_id}` | Matchmaking | Bearer Token | Cancel queued ticket | Path `ticket_id: str` | JSON message | Complete |

---

## 6. Game Feature Readiness Matrix

| Feature | Audit Status | Implementation Details & Missing Gaps |
|---|---|---|
| **Account & Authentication** | **Implemented and tested** | Standard registration, salted PBKDF2 hashing, guest hardware ID persistence, Bearer token signing, and sliding-window rate limiting. Fully tested. |
| **Player Profiles** | **Implemented and tested** | Character profile creation, unique nicknames, GID allocation, public statistics lookup, and validated settings/cosmetic updates. Fully tested. |
| **Player Inventory** | **Partially implemented** | Unlocked items are stored merely as integer lists inside a JSON blob in `Character.appearances`. There is no dedicated inventory database table, no item rarity/metadata system, no item expiration timestamps, and no item acquisition transaction history. |
| **Diamond Currency** | **Partially implemented** | The `diamonds` column exists on `characters` (default: 100). However, there are no endpoints to purchase, award, spend, or transfer diamond balances. |
| **Item & Skin Management** | **Partially implemented** | Equipped clothes and active weapon skin IDs can be submitted via `PUT /player/character/appearances`. However, there is no catalog of available skins, no client asset mapping, and no verification that an item has actually been unlocked before equipping. |
| **Administrator Controls** | **Not implemented** | No administrator role authorization (`is_admin`), no diamond granting endpoints, no ban/unban management endpoints (despite `is_banned` existing on model), and no operator console. |
| **Lobby** | **Implemented and tested** | In-memory presence tracking, status transitions (`idle`, `in_room`, `matchmaking`, `in_battle`), heartbeat keep-alive, stale presence cleanup, and online player listing. Fully tested. |
| **Private Rooms** | **Implemented and tested** | Custom room creation with password hashing, multi-room join guards, member slot allocation, readiness toggles, host migration, host kicks, match launch authorization tokens, and automatic room destruction when empty. Fully tested. |
| **Matchmaking** | **Implemented and tested** | Queue ticket lifecycle, mode/region isolation, cancellation, ticket status polling, threshold-based pair matching, battle token allocation, and ticket timeout/TTL cleanup. Fully tested. |
| **Battle/Gameplay Networking** | **Not implemented** | System generates a simulated match token pointing to `127.0.0.1:20002`, but there is **no UDP Mercury socket listener**, no BigWorld packet serialization/deserialization, no entity cell/base synchronization, and no physics/gameplay world simulation. |

---

## 7. Automated Test Results

### 7.1 Test Execution Output
The automated test suite was executed in an isolated environment against an in-memory SQLite database:

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\MSI\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server
configfile: pytest.ini
plugins: anyio-4.16.0, platformdirs-4.13.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 24 items

tests/test_account.py::test_health_check PASSED                          [  4%]
tests/test_account.py::test_account_register_and_login PASSED            [  8%]
tests/test_account.py::test_guest_login PASSED                           [ 12%]
tests/test_account.py::test_authenticated_me_endpoint PASSED             [ 16%]
tests/test_lobby.py::test_lobby_lifecycle PASSED                         [ 20%]
tests/test_lobby.py::test_lobby_entry_without_character PASSED           [ 25%]
tests/test_matchmaking.py::test_matchmaking_queue_and_cancel PASSED      [ 29%]
tests/test_matchmaking.py::test_matchmaking_pairing PASSED               [ 33%]
tests/test_player.py::test_character_creation_and_profile PASSED         [ 37%]
tests/test_player.py::test_duplicate_nickname_across_accounts PASSED     [ 41%]
tests/test_player.py::test_update_settings_and_appearances PASSED        [ 45%]
tests/test_remediation.py::test_guest_registration_and_returning_login PASSED [ 50%]
tests/test_remediation.py::test_different_device_ids_create_different_accounts PASSED [ 54%]
tests/test_remediation.py::test_concurrent_guest_registration_same_device_id PASSED [ 58%]
tests/test_remediation.py::test_single_worker_deployment_safeguard PASSED [ 62%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_rooms PASSED [ 66%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_matchmaking PASSED [ 70%]
tests/test_remediation.py::test_expired_ticket_cleanup PASSED            [ 75%]
tests/test_remediation.py::test_expired_room_cleanup PASSED              [ 79%]
tests/test_remediation.py::test_active_rooms_and_valid_tickets_surviving_cleanup PASSED [ 83%]
tests/test_remediation.py::test_oversized_and_malformed_appearance_settings_payload_rejection PASSED [ 87%]
tests/test_remediation.py::test_login_rate_limiting PASSED               [ 91%]
tests/test_remediation.py::test_registration_rate_limiting PASSED        [ 95%]
tests/test_room.py::test_room_management PASSED                          [100%]

============================= 24 passed in 3.86s ==============================
```

### 7.2 Test Summary & Isolation Verification
- **Total Tests**: 24
- **Passed**: 24 (100%)
- **Failed**: 0
- **Skipped**: 0
- **Database Isolation**: The test runner utilizes `sqlite+aiosqlite:///:memory:` with `StaticPool`. In [`tests/conftest.py`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/tests/conftest.py), `prepare_database` creates and drops tables per test execution, guaranteeing complete transaction isolation without creating or touching disk databases.

### 7.3 Missing Test Cases Identified
- **Banned User Enforcement**: While `Account.is_banned` is checked in `AccountService.authenticate()` and `get_current_account()`, there is no explicit test verifying that a banned user receives HTTP 403 on login.
- **Tampered Token Handling**: No test verifies that modifying the HMAC signature of a Bearer token triggers HTTP 401.
- **Expired Token Handling**: No test verifies that a token whose `exp` is in the past triggers HTTP 401.
- **Room Capacity Boundary**: Joining a room that is already full (`len(members) >= capacity`) is validated in code, but lacks a dedicated unit test.
- **Admin Endpoints**: Currently untested because the admin module does not exist yet.

---

## 8. Original iOS Client Compatibility Findings

Based on static analysis of the legacy iOS executable (`RoS-Legacy-iOS.ipa`) and previous research reports (Phase 1–4):

### 8.1 What is Known
1. **Authentication Gateway**:
   - The original iOS client uses NetEase's UniSDK framework.
   - Authentication begins with an HTTPS handshake to NetEase login endpoints (`login.mkey.163.com` or similar) exchanging device tokens/credentials for a temporary session ticket.
2. **Server Discovery**:
   - The game client downloads a server list configuration (JSON/XML) providing the display names, operational status, and IP:port endpoints of available game clusters.
3. **BigWorld / Mercury Protocol Architecture**:
   - The iOS client's native binary implements the BigWorld engine Mercury networking stack over **UDP** (classes: `Mercury::Bundle`, `Mercury::Packet`, `Mercury::Channel`, `BinaryOStream`, `BinaryIStream`).
   - The client speaks to a `LoginApp` UDP port (e.g. 20013) to present the login ticket. Upon validation, the `LoginApp` provides a session key and redirects the client to a `BaseApp` UDP address.
4. **Entity RPC Communication**:
   - All client-server game interactions (lobby presence, inventory, custom rooms, matchmaking, and battle entities) operate via **BigWorld Entity Remote Procedure Calls (RPCs)** running over Mercury UDP streams.
   - Extracted client scripts confirm entities: `Account` (lobby, role info), `iRosMatch` / `iRosMatchAvatar` (matchmaking queues), `DtsCustomRoom` (custom rooms), and `PlayerAvatar` / `PlayerAthlete` (in-game battle simulation).

### 8.2 What is Unknown / Incompatible
1. **REST vs. Mercury Mismatch**:
   - The current `ros-private-server` exposes **only HTTP/REST JSON endpoints**.
   - **The original iOS client cannot natively speak HTTP REST to interact with the lobby, rooms, or matchmaking.** The iOS client expects to send binary Mercury UDP packets to BigWorld entities (`Account`, `iRosMatch`, etc.).
2. **Binary Packet Framing**:
   - The exact bitfield layout of Mercury packet headers, bundle sequencing, acknowledgment flags, and packet fragmentation thresholds on iOS requires protocol bridge emulation.
3. **Method ID Numerical Indexing**:
   - BigWorld RPC methods are invoked over UDP using compact numerical method IDs (e.g., method index 12 on entity type 3). While the entity method names are known from decompiled Python scripts, the exact numerical ID mapping defined in the binary's entity definition tables (`.def` files compiled into the Mach-O binary) remains unmapped.
4. **iOS Binary Certificate Pinning & Host Overrides**:
   - Whether the iOS binary enforces TLS certificate pinning on its auth endpoints, or whether local domain redirection via DNS (e.g., DNS proxy on local Wi-Fi router) is sufficient to route the iOS client to our private server, has not yet been dynamically tested.

---

## 9. Critical Issues & Architectural Gaps

1. **Mercury UDP Protocol Gap (Architectural Blocker for iOS Client)**:
   - The current backend is a modern REST API suitable for a companion web interface or custom game client, but **cannot accept network connections from the unmodified iOS client**.
   - A protocol adapter or Mercury UDP gateway service is mandatory before the iOS game can communicate with this backend.
2. **Lack of Administrator Diamond & Inventory Controls**:
   - Player diamonds are hardcoded to default 100 on creation. There is no API or database service allowing an administrator to grant diamonds, items, or skins to players.
3. **Inventory Data Normalization**:
   - Outfits and weapon skins are currently stored inside a unstructured JSON dictionary in the `characters` table. This prevents catalog queries, item drop tables, skin rarity tiers, or transaction logging.
4. **Single-Worker Scalability Constraint**:
   - While the single-worker safeguard (SEC-01) prevents multi-worker corruption, all lobby, room, and matchmaking state resides in memory. A server restart wipes all active rooms and queues.

---

## 10. Recommended Next Development Phase

To advance from an independent REST foundation toward a functional private server environment for the original iOS client, we recommend dividing the next stage into two sequential milestones:

### Recommended Phase: **Phase 5.4 — Administrative Economy & Companion Web Portal**
Before tackling complex binary UDP Mercury sockets, complete the private server management layer:
1. **Admin Currency & Role Management**:
   - Implement `is_admin` role flag on `Account`.
   - Add admin REST endpoints to grant/revoke diamonds, adjust gold, and ban/unban offending players.
2. **Structured Inventory & Skin Catalog**:
   - Create normalized database tables: `items` (catalog: item_id, name, type, rarity, skin_slot) and `player_inventory` (ownership ledger: account_id, item_id, acquired_at).
   - Add player inventory viewing, cosmetic unlocking, and diamond purchase simulation endpoints.
3. **Mobile-Friendly Player & Admin Web Interface**:
   - Build a lightweight, responsive web dashboard (HTML5/Tailwind or Vue) allowing friends on iOS to register, manage their character, view stats, claim admin-granted diamonds, and browse unlocked skins from their mobile browser.

### Subsequent Phase: **Phase 6 — Mercury UDP Gateway & iOS Authentication Bridge**
1. Implement a lightweight UDP listener (`mercury_gateway.py`) capable of parsing Mercury bundle headers and BigWorld handshake packets.
2. Build an internal bridge mapping Mercury UDP RPC calls to the existing FastAPI services.

---

## 11. Final Status

The Phase 5.3 Read-Only Backend Audit is complete. In accordance with safety constraints, no source code, database tables, migrations, or game client files were altered.

I am stopping here and awaiting your review and approval.
