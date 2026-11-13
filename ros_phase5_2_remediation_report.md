# Phase 5.2 — Critical & High-Priority Remediation Report

**Date**: November 9, 2026  
**Auditor & Implementation Agent**: Antigravity (Advanced Agentic Coding Agent)  
**Target Repository**: `ros-private-server/`  
**Status**: All 6 Critical and High vulnerabilities remediated and verified with 24 passing automated tests.

---

## 1. Executive Summary

In accordance with the Phase 5.2 mandate, all six Critical and High severity issues identified during the Phase 5.1 quality and security audit have been systematically reviewed, verified, and remediated in controlled groups. 

The test suite was expanded from 12 to **24 automated tests**, covering guest account persistence, concurrency safety, single-worker deployment safeguards, disconnected player cascade purges, memory leak cleanup, input payload rejection, and rate limiting. All 24 tests are passing.

---

## 2. Issues Verified & Fixed

### Group A: Critical Issues

#### 1. SEC-02 — Guest Account Persistence & Concurrency
- **Root Cause Verified**: `AccountService.register_guest` accepted an optional `device_id` string, but immediately discarded it and generated a random `guest_<hex4>` username with a new database row. Returning guests lost their character profiles, gold, settings, and progress every time they reconnected. Furthermore, the `accounts` table lacked a `device_id` column and unique constraint.
- **Remediation**:
  - Added `device_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)` to `Account` entity in `app/account/models.py`.
  - Added `get_by_device_id(device_id)` in `AccountRepository`.
  - Updated `register_guest()` in `AccountService`:
    - Validates the `device_id` format (4–64 characters, regex `^[a-zA-Z0-9_\-\.:]+$`).
    - If `device_id` exists: updates `last_login`, checks ban status, and returns the existing account and bearer token.
    - If `device_id` is new: creates a new account associated with that `device_id`.
    - Handles concurrent registration races by catching database `IntegrityError`, rolling back, and retrieving the concurrently created account.
    - Device IDs and raw credentials are never printed or logged.
- **Verification Tests**: `test_guest_registration_and_returning_login`, `test_different_device_ids_create_different_accounts`, `test_concurrent_guest_registration_same_device_id`.

#### 2. SEC-01 — Multi-Worker State Desynchronization Safeguard
- **Root Cause Verified**: `LobbyService`, `RoomService`, and `MatchmakingService` rely on process-local in-memory state. Running with multiple Uvicorn worker processes (e.g., `--workers 4`) creates isolated state partitions where players connected to different workers cannot find each other's rooms, share presence, or match together.
- **Remediation**:
  - Maintained single-worker architecture for the current phase without introducing external dependencies (Redis/KeyDB).
  - Implemented `validate_single_worker_configuration()` in `app/main.py` which inspects ASGI/WSGI environment variables (`WEB_CONCURRENCY`, `UVICORN_WORKERS`, `WORKERS`) and raises a descriptive `RuntimeError` preventing server boot if configured with `workers > 1`.
  - Updated `README.md` to specify `--workers 1` in production systemd unit configurations and documented the external coordinator requirements necessary before multi-worker scaling.
- **Verification Test**: `test_single_worker_deployment_safeguard`.

---

### Group B: High-Priority Issues

#### 3. SEC-04 — Stale Disconnected Player Cascade Cleanup
- **Root Cause Verified**: When a player disconnected or stopped sending heartbeats, `cleanup_stale_presences` deleted the player from `LobbyService._presences`, but did not notify `RoomService` or `MatchmakingService`. The player remained indefinitely as an active slot in custom rooms (even as an abandoned host) and could be matched into battle games while offline.
- **Remediation**:
  - Implemented `handle_player_disconnect(gid: int)` in `RoomService` which safely departs the player from any active rooms, triggers host migration if the disconnected player was host, and closes rooms that become empty.
  - Implemented `handle_player_disconnect(gid: int)` in `MatchmakingService` which transitions queued tickets to `TIMEOUT` and releases the queue slot.
  - Connected `LobbyService.cleanup_stale_presences()` to automatically invoke both handlers whenever a player times out past `LOBBY_HEARTBEAT_TIMEOUT_SECONDS`.
- **Verification Tests**: `test_disconnected_player_cleanup_from_rooms`, `test_disconnected_player_cleanup_from_matchmaking`.

#### 4. SEC-03 — Ephemeral Memory Leak & Room/Ticket Pruning
- **Root Cause Verified**: `MatchmakingService._tickets` retained cancelled, timed-out, and matched tickets indefinitely. Similarly, `RoomService._rooms` retained closed or abandoned rooms. In addition, cleanup only ran on user requests (`/enter` or `/online`), meaning idle servers never freed memory.
- **Remediation**:
  - Implemented `cleanup_expired_tickets()` in `MatchmakingService` with configurable TTL (`MATCHMAKING_TICKET_TTL_SECONDS = 300`) and queue timeout (`MATCHMAKING_TICKET_TIMEOUT_SECONDS = 300`).
  - Implemented `cleanup_stale_rooms()` in `RoomService` using timezone-safe UTC elapsed calculations (`(datetime.utcnow() - room.created_at).total_seconds()`).
  - Implemented `perform_system_cleanup()` and integrated a controlled, cancelable background asyncio loop in `app/main.py` lifespan that automatically prunes memory every `CLEANUP_INTERVAL_SECONDS = 15`.
- **Verification Tests**: `test_expired_ticket_cleanup`, `test_expired_room_cleanup`, `test_active_rooms_and_valid_tickets_surviving_cleanup`.

#### 5. SEC-05 — Input Validation & Payload Size Limits
- **Root Cause Verified**: `CharacterUpdateSettings` and `CharacterUpdateAppearances` accepted arbitrary unvalidated `Dict[str, Any]` without size restrictions, allowing multi-megabyte payloads, deeply nested dictionaries, or malformed data types to corrupt database storage.
- **Remediation**:
  - Added strict Pydantic field validators in `app/player/schemas.py`:
    - Enforced a hard limit of 16 KB (16,384 bytes) on serialized JSON payloads.
    - `settings`: limited to max 30 keys, valid identifier names (1–32 chars), max string lengths of 128 characters, max nested dict depth of 1 level (up to 15 subkeys with numeric values).
    - `appearances`: limited to max 20 keys, valid identifier names, cosmetic item lists limited to max 50 items with non-negative integer IDs (0 to 9,999,999), and weapon skin IDs bounded to valid ranges.
    - Malformed or oversized payloads are rejected immediately with HTTP 422 Unprocessable Entity.
- **Verification Test**: `test_oversized_and_malformed_appearance_settings_payload_rejection`.

#### 6. SEC-06 — In-Memory Rate Limiting & Brute-Force Protection
- **Root Cause Verified**: Authentication endpoints had no request throttling, allowing password brute-forcing, credential stuffing, and guest account spam.
- **Remediation**:
  - Created `app/account/rate_limiter.py` implementing a high-performance in-memory sliding-window rate limiter with automatic historical pruning.
  - Added configurable settings in `app/config.py`:
    - `RATE_LIMIT_LOGIN_MAX_REQUESTS = 5` per 60-second rolling window.
    - `RATE_LIMIT_REGISTER_MAX_REQUESTS = 3` per 60-second rolling window.
  - Applied rate limiting dependencies to `/api/v1/account/login`, `/api/v1/account/register`, and `/api/v1/account/guest`.
  - Exceeded thresholds return `HTTP 429 Too Many Requests` with a standard `Retry-After` header indicating seconds until unlock.
- **Verification Tests**: `test_login_rate_limiting`, `test_registration_rate_limiting`.

---

## 3. Exact Files Modified or Created

| File | Status | Description of Changes |
|---|---|---|
| `app/config.py` | Modified | Added worker guard, cleanup intervals, ticket/room TTL, and rate limiting settings. |
| `app/main.py` | Modified | Added `validate_single_worker_configuration`, `perform_system_cleanup`, periodic background task in lifespan, and CORS fix. |
| `app/account/models.py` | Modified | Added `device_id` column with unique index to `Account`. |
| `app/account/repository.py` | Modified | Added `device_id` to `create()`, added `get_by_device_id()`, added rollback on `IntegrityError`. |
| `app/account/schemas.py` | Modified | Added regex validation and length bounds on `GuestRegister.device_id`. |
| `app/account/service.py` | Modified | Implemented guest re-login by `device_id`, concurrent race recovery, and safe logging. |
| `app/account/rate_limiter.py` | **Created** | In-memory sliding-window rate limiter with `Retry-After` headers and IP resolution. |
| `app/account/router.py` | Modified | Applied rate-limiting dependencies to `/register`, `/login`, and `/guest`. |
| `app/player/schemas.py` | Modified | Added size and structure validators for `settings` and `appearances` payloads. |
| `app/lobby/service.py` | Modified | Cascaded heartbeat timeout disconnects to `RoomService` and `MatchmakingService`. |
| `app/room/service.py` | Modified | Added `handle_player_disconnect`, `cleanup_stale_rooms`, cross-room join checks, constant-time pwd compare. |
| `app/matchmaking/service.py` | Modified | Added `handle_player_disconnect`, `cleanup_expired_tickets`, and queue timeout transitions. |
| `migrations/001_add_device_id.sql` | **Created** | Non-destructive SQL migration script for SQLite and PostgreSQL. |
| `README.md` | Modified | Updated production deployment configuration to `--workers 1` with architectural notes. |
| `tests/conftest.py` | Modified | Updated test client database session scoping for concurrent request isolation and rate-limiter resets. |
| `tests/test_remediation.py` | **Created** | 12 automated unit and integration tests verifying all remediations. |

---

## 4. Database Migration Requirements & Safety Analysis

### Migration Script Created
[`migrations/001_add_device_id.sql`](file:///c:/Users/MSI/Downloads/Telegram%20Desktop/ROS-Legacy-Analysis/ros-private-server/migrations/001_add_device_id.sql):

```sql
-- SQLite Syntax:
ALTER TABLE accounts ADD COLUMN device_id VARCHAR(64);
CREATE UNIQUE INDEX IF NOT EXISTS ix_accounts_device_id ON accounts (device_id);

-- PostgreSQL Syntax:
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS device_id VARCHAR(64) UNIQUE;
CREATE INDEX IF NOT EXISTS ix_accounts_device_id ON accounts (device_id);
```

### Safety & Risk Assessment
- **Zero Data Loss**: The column is `NULLable`, meaning all existing standard registered user accounts remain valid with `device_id = NULL`.
- **Existing Databases**: In accordance with user instructions, no existing database files were modified or deleted. For fresh installations, SQLAlchemy's `Base.metadata.create_all` includes the new column automatically.

---

## 5. Actual Test Execution Results

All 24 automated tests passed without errors or warnings:

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

============================= 24 passed in 6.23s ==============================
```

---

## 6. Remaining Issues & Security Limitations

The following items from the Medium/Low severity tiers remain as documented limitations for future roadmap consideration:
1. **Multi-Node / Distributed Scaling**: The backend is explicitly constrained to single-worker execution (`workers = 1`). Scaling horizontally across multiple processes or machines will require integrating an external distributed coordinator (Redis/KeyDB) for lobby presence, custom rooms, and matchmaking pools.
2. **Token Format**: Bearer tokens use a custom 2-segment signed HMAC token rather than 3-segment RFC 7519 JWT.
3. **Password Hash Work Factor**: PBKDF2 iterations are currently set to 100,000 for development responsiveness; production deployment should elevate this to 600,000 iterations or migrate to Argon2id.
4. **Rate Limiting Persistence**: The sliding-window rate limiter stores history in process memory; restarts reset rate-limiting windows.

---

## 7. Instructions for Running the Server Safely

### Local Development (Windows)
```powershell
cd ros-private-server
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests -v
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Production Execution (Linux)
Run with single-worker mode to maintain state coherence:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

---

## 8. Completion & Next Steps

Phase 5.2 remediation is complete. No gameplay, battle server, or network protocol features were added.

I will now wait for your review and approval before proceeding further.
