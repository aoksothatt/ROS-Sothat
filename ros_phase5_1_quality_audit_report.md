# Phase 5.1 — Private Server Foundation Quality & Security Audit Report

**Date**: November 9, 2026  
**Auditor**: Antigravity (Advanced Agentic Coding Agent)  
**Target Repository**: `ros-private-server/`  
**Scope**: Full architectural, security, concurrency, and test coverage audit of the Phase 5 backend foundation.  
**Mode**: READ-ONLY Audit. No source code or database records were modified.

---

## 1. Executive Summary & Overall Audit Result

The Phase 5 backend foundation provides a clean, well-structured, and modular starting point for an independent Rules of Survival private backend. It successfully implements the core REST endpoints for account authentication, player profile management, in-memory lobby presence, custom rooms, and matchmaking queues using FastAPI, AsyncIO, and SQLAlchemy 2.0.

All 12 automated unit and integration tests are currently **PASSING** (`12 passed in 1.79s`).

### Overall Audit Verdict: **CONDITIONAL PASS (NEEDS HARDENING BEFORE PRODUCTION & MERCURY BRIDGE)**

While the architecture is well-organized for local single-developer testing, this audit identified **2 Critical**, **4 High**, **6 Medium**, and **5 Low** severity vulnerabilities and architectural gaps that must be addressed before multi-user deployment or Phase 6 (Battle Server & Protocol Bridge).

Most notably:
1. **Multi-Worker Desynchronization**: The in-memory state architecture for Lobby, Room, and Matchmaking breaks when scaled across multiple Uvicorn worker processes (as recommended in the deployment guide), requiring an external state coordinator (e.g., Redis) or single-process sticky routing.
2. **Guest Account Device ID Ignored**: Guest login accepts a `device_id` but discards it, generating an isolated orphan account on every request, resulting in complete player progression loss upon client re-login.
3. **Unbounded Payloads & Memory Leaks**: User settings and cosmetics accept arbitrary unvalidated JSON of unlimited size, and completed/cancelled matchmaking tickets are never pruned from memory.

---

## 2. Actual Test Results

The test suite was executed against the isolated in-memory test database in the workspace environment:

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0 -- C:\Users\MSI\AppData\Local\Programs\Python\Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server
configfile: pytest.ini
plugins: anyio-4.16.0, platformdirs-4.13.0, asyncio-1.4.1.post1
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... collected 12 items

tests/test_account.py::test_health_check PASSED                          [  8%]
tests/test_account.py::test_account_register_and_login PASSED            [ 16%]
tests/test_account.py::test_guest_login PASSED                           [ 25%]
tests/test_account.py::test_authenticated_me_endpoint PASSED             [ 33%]
tests/test_lobby.py::test_lobby_lifecycle PASSED                         [ 41%]
tests/test_lobby.py::test_lobby_entry_without_character PASSED           [ 50%]
tests/test_matchmaking.py::test_matchmaking_queue_and_cancel PASSED      [ 58%]
tests/test_matchmaking.py::test_matchmaking_pairing PASSED               [ 66%]
tests/test_player.py::test_character_creation_and_profile PASSED         [ 75%]
tests/test_player.py::test_duplicate_nickname_across_accounts PASSED     [ 83%]
tests/test_player.py::test_update_settings_and_appearances PASSED        [ 91%]
tests/test_room.py::test_room_management PASSED                          [100%]

============================= 12 passed in 1.79s ==============================
```

---

## 3. Detailed Audit Findings by Component

### 3.1 Account & Authentication Security
- **Password Hashing**: Implements `PBKDF2-HMAC-SHA256` with 100,000 iterations and a cryptographically secure 16-byte random salt (`secrets.token_hex(16)`). Passwords are verified using constant-time comparison (`hmac.compare_digest`). While functional, current OWASP guidelines recommend 600,000 iterations for PBKDF2-HMAC-SHA256 or migrating to Argon2id.
- **Token Signing & Verification**: Custom compact signed token format: `<base64url_payload>.<base64url_hmac_signature>`. Uses `hmac.new(SECRET_KEY, ..., hashlib.sha256)` with `hmac.compare_digest`. Avoids `{"alg": "none"}` attacks, but does not follow RFC 7519 JWT standards (missing JWT header segment).
- **Token Expiration**: Checked against current timestamp (`payload.get("exp")`). Default expiration is 1,440 minutes (24 hours). No token revocation/blacklist mechanism exists for logout or credential compromise.
- **Secret Key Configuration**: Defaults to `"ros-private-insecure-dev-secret-key-change-in-prod-32bytes"`. If the environment variable `SECRET_KEY` is omitted in production, the server starts up without a warning or error.
- **Guest Account Handling**: In `app/account/service.py` (`register_guest`), the `device_id` parameter is received but completely discarded. Every guest call generates a new account (`guest_<hex4>`), preventing mobile clients from resuming their guest character.
- **Login Rate Limiting**: Completely absent. There is no protection against credential brute-forcing, password spraying, or account registration flooding.

### 3.2 Player Management
- **Ownership Validation**: Validated via `get_current_account`. A player cannot read or modify another player's private character settings or appearances.
- **Nickname Uniqueness Concurrency**: `PlayerService.create_character` performs a check (`get_by_nickname`), followed by `repository.create()`. Under high concurrent load, two simultaneous registrations with the same nickname cause an unhandled database `IntegrityError`, returning HTTP 500 instead of a clean HTTP 409 Conflict.
- **GID Allocation**: Sequential integer (`BigInteger().with_variant(Integer, "sqlite")`). Allows predictable enumeration and userbase size scraping via `/api/v1/player/{gid}`.
- **Appearance & Settings Validation**: Unvalidated `Dict[str, Any]` inputs. A client can send arbitrarily nested dictionaries, 50MB strings, or non-existent inventory items, with no ownership checks against unlocked cosmetic IDs.

### 3.3 Lobby and Presence
- **Heartbeat Expiration & Cleanup**: Stale presences are cleaned up only when `enter_lobby` or `list_online_players` is called. There is no background asyncio worker running periodically to purge stale entries.
- **Orphaned State on Timeout**: When a presence expires in `LobbyService`, neither `RoomService` nor `MatchmakingService` is notified. If a player disconnects while in a room or queue, they remain stuck as an active participant indefinitely.
- **Multi-Worker Desynchronization**: `LobbyService` maintains an in-memory dictionary `_presences`. When running Uvicorn with `--workers 4`, each OS process has its own isolated memory space. A player who registered on Worker 1 will appear offline to Worker 2.

### 3.4 Room Management
- **Capacity Enforcement**: Handled via `len(room.members) >= room.capacity`.
- **Password Security**: Room passwords use unsalted SHA-256 and are compared using standard `!=` string equality rather than `hmac.compare_digest`.
- **Cross-Room Membership**: `RoomService.join_room` checks if the user is already in the target room, but fails to check if the user is currently in a *different* room. A player can join multiple rooms simultaneously.
- **Minimum Player Validation on Match Start**: `start_room_match` checks player readiness, but does not check if `len(room.members) >= 2`. A solo player in a custom squad room can launch a match alone.
- **Host Migration**: Oldest remaining member inherits host privileges. However, if the host disconnects without calling `/leave`, the room remains permanently blocked because heartbeat timeout does not trigger room departure.

### 3.5 Matchmaking Engine
- **Duplicate Queue Protection**: Properly checks if the player already has a ticket in `QUEUED` status and returns the active ticket.
- **Unbounded Ticket Memory Growth**: Cancelled and matched tickets remain in `self._tickets` forever, leaking memory over server uptime.
- **Ghost Player Matching**: Matchmaking does not verify whether queued players are still actively sending lobby heartbeats. Offline/crashed players can be matched into active games.
- **Lack of Level / Skill Brackets**: Match pairing is strictly FIFO; player level is ignored.

### 3.6 Database Architecture
- **SQLite vs. PostgreSQL**: Seamlessly compatible via SQLAlchemy 2.0 async engine and `with_variant` mapping on `characters.gid`.
- **SQLite Foreign Key Enforcement**: SQLite does not enforce foreign keys by default. The engine connection listener for `PRAGMA foreign_keys = ON;` is missing, allowing orphaned records in local SQLite development.
- **Transaction Rollback**: Repositories lack explicit `await session.rollback()` on exceptions.
- **Migrations**: No Alembic configuration. Schema changes require manual SQL execution or dropping tables.

---

## 4. Issue Severity Classification

| Issue ID | Severity | Component | Summary |
|---|---|---|---|
| **SEC-01** | **CRITICAL** | Architecture / Lobby | Multi-worker process desynchronization due to in-memory state singletons. |
| **SEC-02** | **CRITICAL** | Account / Auth | `device_id` discarded in `register_guest`, causing permanent progression loss on re-login. |
| **SEC-03** | **HIGH** | Matchmaking / Room | Ephemeral memory leak: tickets and closed rooms never pruned from memory. |
| **SEC-04** | **HIGH** | Lobby / Room / MM | Stale disconnected players remain stuck in rooms and matched into battle games. |
| **SEC-05** | **HIGH** | Player Profile | Unbounded and unvalidated `Dict[str, Any]` payload for settings and cosmetics. |
| **SEC-06** | **HIGH** | Account / Auth | Missing rate limiting and brute-force protection on authentication endpoints. |
| **SEC-07** | **MEDIUM** | Database / Repos | Unhandled `IntegrityError` on concurrent nickname/username registration returns HTTP 500. |
| **SEC-08** | **MEDIUM** | Room Management | A player can join multiple different custom rooms simultaneously without leaving. |
| **SEC-09** | **MEDIUM** | Room Management | Room host can launch a match with only 1 player regardless of team mode. |
| **SEC-10** | **MEDIUM** | Application / CORS | CORS configured with `allow_origins=["*"]` and `allow_credentials=True` (spec violation). |
| **SEC-11** | **MEDIUM** | Security / Config | Production starts silently with hardcoded insecure default `SECRET_KEY`. |
| **SEC-12** | **MEDIUM** | Database / SQLite | Missing `PRAGMA foreign_keys = ON;` listener for SQLite connections. |
| **SEC-13** | **LOW** | Room Management | Room password verification uses standard string comparison `!=` instead of `compare_digest`. |
| **SEC-14** | **LOW** | Account / Auth | Non-standard token structure (2 segments instead of 3-segment RFC 7519 JWT). |
| **SEC-15** | **LOW** | Account / Auth | PBKDF2 iteration count is 100,000 (below OWASP recommended 600,000). |
| **SEC-16** | **LOW** | Database | Alembic database migration tooling not initialized. |
| **SEC-17** | **LOW** | Player Profile | Sequential autoincrement GID allows user enumeration. |

---

## 5. Missing Test Coverage

The existing 12 tests verify the happy path and primary validation failures, but lack coverage for adversarial and edge-case scenarios:

1. **Account Security**:
   - Verification that banned accounts (`is_banned=True`) receive HTTP 403 on login and authenticated calls.
   - Verification that tampered tokens, malformed signatures, or expired tokens receive HTTP 401.
   - Minimum/maximum length validation for username and password schemas.
2. **Player Management**:
   - Nickname regex boundary tests (emojis, whitespace, special characters, SQL injection attempts).
   - Calling character update endpoints when no character exists (verifying HTTP 404).
   - Attempting to update another player's character profile.
3. **Lobby & Presence**:
   - Heartbeat timeout expiration: advancing time past 60s and verifying removal from `/online`.
   - Heartbeat call when player has not entered lobby (verifying HTTP 404).
   - Idempotent repeated lobby leave calls.
4. **Room Management**:
   - Host kicking a player (`/room/{id}/kick/{gid}`).
   - Non-host attempting to kick a member (verifying HTTP 403).
   - Room full capacity rejection (capacity 2, third player joins, verifying HTTP 400).
   - Host migration verification (host leaves, second player becomes host).
5. **Matchmaking Engine**:
   - Region mismatch isolation: Player A in `asia` and Player B in `us` do not pair.
   - Mode mismatch isolation: Player A in `solo` and Player B in `squad` do not pair.
   - Cancelling an already matched ticket (verifying HTTP 400).
   - Accessing another user's match ticket status.

---

## 6. Recommended Action Plan & Target Files

### Recommended Fixes

1. **Guest Device ID Mapping (`SEC-02`)**:
   - Add `device_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True, nullable=True)` to `accounts`.
   - In `register_guest`, check if `device_id` already exists. If found, authenticate and return that existing account instead of creating an orphan.
2. **State Coordination Architecture (`SEC-01`)**:
   - For multi-worker Linux production, either:
     - Document that backend must run in single-worker mode (`workers = 1`) behind an event loop, OR
     - Integrate Redis / KeyDB as the backing store for `LobbyService`, `RoomService`, and `MatchmakingService`.
3. **Payload Sanitization & Size Limits (`SEC-05`)**:
   - Add explicit Pydantic schema validation or max byte size checks on `CharacterUpdateSettings` and `CharacterUpdateAppearances`.
4. **Stale Session Cascade (`SEC-04`)**:
   - Implement an AsyncIO background task in `lifespan` that periodically calls a unified cleanup function: removes stale presences from lobby, cascades departure to rooms, and cancels stale matchmaking tickets.
5. **Duplicate Room Membership Guard (`SEC-08`)**:
   - In `RoomService.join_room`, iterate through active rooms or check `lobby_service.get_presence(gid).room_id` to ensure the player is not already in another room.
6. **Graceful Database Integrity Handling (`SEC-07`)**:
   - Catch `sqlalchemy.exc.IntegrityError` in `AccountRepository.create` and `PlayerRepository.create`, rolling back the session and raising `HTTPException(409 Conflict)`.
7. **Security Baseline Adjustments (`SEC-06`, `SEC-10`, `SEC-11`, `SEC-12`)**:
   - Fix CORS middleware: specify exact origins or set `allow_credentials=False`.
   - Enforce non-default `SECRET_KEY` when `ENVIRONMENT=production`.
   - Add SQLite connection listener for `PRAGMA foreign_keys = ON;`.
   - Add slowapi or Redis rate limiter on `/account/login` and `/account/register`.

### Affected Files Requiring Modifications in Future Remediation
- `app/config.py` (Production secret key validation)
- `app/main.py` (CORS fix, periodic background cleanup task)
- `app/database/session.py` (SQLite foreign key pragma listener)
- `app/account/models.py` (Add `device_id` column)
- `app/account/repository.py` (Add `get_by_device_id`, catch `IntegrityError`)
- `app/account/service.py` (Resume existing guest account, increase PBKDF2 iterations)
- `app/player/schemas.py` (Structured settings & appearance schemas)
- `app/player/repository.py` (Catch `IntegrityError` on duplicate nicknames)
- `app/lobby/service.py` (Periodic cleanup trigger, cascade cleanup)
- `app/room/service.py` (Check cross-room membership, constant-time pwd compare, min player check)
- `app/matchmaking/service.py` (Prune completed/cancelled tickets, timeout ghost tickets)
- `tests/test_account.py` (Add banned user, malformed token, device ID resumption tests)
- `tests/test_player.py` (Add invalid nickname format, non-existent character tests)
- `tests/test_room.py` (Add member kick, room full, host migration tests)
- `tests/test_matchmaking.py` (Add region/mode isolation, cancel matched ticket tests)

---

## 7. Status & Next Steps

This quality and security audit is complete. In accordance with the project instructions, no source files or databases have been altered. 

Awaiting your review and approval before proceeding.
