# ROS Sothat — Phase 6.2A.1.1: Admin RBAC Security Verification Report

**Date**: November 11, 2026  
**Auditor & Security Reviewer**: Antigravity (Advanced Agentic Coding Assistant)  
**Target Platform**: Independent Private Server Backend (`ros-private-server`)  
**Scope**: Focused security audit of Milestone 6.2A.1 (Admin Role-Based Access Control)  
**Mode**: Strict Read-Only Audit. No source code modified. No database records changed. No migrations executed. Original iOS IPA untouched.

---

## 1. Executive Summary

A comprehensive, read-only security audit of the Admin RBAC implementation was conducted across `app/account/`, `app/admin/`, `migrations/`, and `tests/`.

The audit evaluated all critical threat vectors: privilege escalation via registration, token tampering, bypass of admin guards, self-demotion/self-ban lockouts, banned account handling, and schema migration integrity.

### Audit Verdict
**STATUS: PASS**

The RBAC implementation meets all security, authorization, and data-integrity requirements. All 83 automated unit and integration tests passed with 100% success (3.68s execution time). Zero privilege-escalation vulnerabilities were identified.

---

## 2. Answers to Critical Security Questions

### 1. How is the very first admin account securely created?
- **Current State**: There is **no public API or default credential** that can create an admin account. In tests and initial setups, an admin is created by registering a normal account and elevating it directly within the database (`UPDATE accounts SET role = 'admin' WHERE username = '...'`).
- **Security Assessment**: This is fundamentally secure because it prevents remote attackers from creating an admin account over the network.
- **Operational Recommendation**: To avoid requiring operators to execute raw SQL, a local-only CLI bootstrap script (`python -m app.cli.admin promote <username>`) is proposed in Section 4.

### 2. Can an unauthenticated user promote themselves?
- **Verdict**: **NO. Cryptographically and architecturally impossible.**
- **Evidence**:
  - The promotion endpoint `POST /api/v1/admin/accounts/{account_id}/role` is protected by `Depends(get_current_admin)`.
  - `get_current_admin` depends on `get_current_account`, which validates the Bearer token. Requests without an Authorization header immediately terminate with `HTTP 401 Unauthorized` (`WWW-Authenticate: Bearer`).
  - Public registration (`POST /api/v1/account/register`) uses `AccountRegister`, which explicitly defines `model_config = ConfigDict(extra="forbid")`. Any attempt to pass `"role": "admin"` in the JSON body is rejected at the HTTP schema validation layer with `HTTP 422 Unprocessable Entity`.
  - Guest registration (`POST /api/v1/account/guest`) only accepts `device_id` and hardcodes `role="player"`.

### 3. Can a normal player access any admin endpoint?
- **Verdict**: **NO. Universally rejected with HTTP 403 Forbidden.**
- **Evidence**:
  - Every route in `app/admin/router.py` (`/me`, `/accounts`, `/accounts/{id}/role`, `/accounts/{id}/ban`, `/stats`) requires `admin: Account = Depends(get_current_admin)`.
  - When a normal player provides a valid token, `get_current_admin` queries the database model and checks `account.role == "admin"`.
  - If `account.role != "admin"`, it raises `HTTPException(status_code=403, detail="Admin privileges required.")`.
  - Verified by automated tests `test_player_attempting_admin_access_rejected` and `test_player_apis_cannot_change_own_role`.

### 4. Can an admin manipulate another account's role without authorization?
- **Verdict**: **NO.**
- **Evidence**:
  - Only an account already verified as `role == "admin"` in the database can call `/api/v1/admin/accounts/{account_id}/role`.
  - The endpoint validates that the target role is either `"player"` or `"admin"` (invalid strings return `HTTP 400 Bad Request`).
  - An admin cannot demote themselves (`admin.id == account_id and clean_role != "admin"` returns `HTTP 400 Bad Request: "Cannot revoke your own admin privileges."`).
  - Target account existence is validated; non-existent IDs return `HTTP 404 Not Found`.

### 5. Can a banned admin continue using admin endpoints?
- **Verdict**: **NO. Banned accounts are completely locked out.**
- **Evidence**:
  - In `app/account/service.py`, `get_current_account` executes:
    ```python
    account = await service.repository.get_by_id(account_id, load_character=True)
    if not account:
        raise HTTPException(status_code=404, detail="User account not found.")
    if account.is_banned:
        raise HTTPException(status_code=403, detail="Account is banned.")
    return account
    ```
  - Because `get_current_admin` depends on `get_current_account`, the ban check occurs **before** the role check.
  - If an admin account has `is_banned = True`, any request immediately returns `HTTP 403 Forbidden ("Account is banned.")`.
  - Verified by automated test `test_admin_moderation_ban_and_unban`.

### 6. Does account registration reject all attempts to submit privileged fields?
- **Verdict**: **YES.**
- **Evidence**:
  - In `app/account/schemas.py`:
    ```python
    class AccountRegister(BaseModel):
        username: str = Field(..., min_length=3, max_length=32, description="Unique username")
        password: str = Field(..., min_length=6, max_length=64, description="Raw password")
        model_config = ConfigDict(extra="forbid")
    ```
  - Submitting `{"username": "attacker", "password": "password123", "role": "admin"}` triggers Pydantic's `extra_forbidden` error and returns `HTTP 422`.
  - In `app/account/service.py`, `repository.create` explicitly passes `role="player"`.
  - Verified by automated test `test_registration_cannot_create_admin`.

### 7. Does the migration preserve existing accounts as players?
- **Verdict**: **YES.**
- **Evidence**:
  - In `migrations/002_add_account_role.sql`:
    ```sql
    -- SQLite:
    ALTER TABLE accounts ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'player';

    -- PostgreSQL:
    ALTER TABLE accounts ADD COLUMN IF NOT EXISTS role VARCHAR(16) NOT NULL DEFAULT 'player';
    ```
  - Both database engines assign `'player'` to all existing rows when the column is added.
  - Zero existing accounts are promoted; all existing accounts remain players by default.

### 8. Does the role field work correctly with existing database initialization and migration strategy?
- **Verdict**: **YES.**
- **Evidence**:
  - For new or in-memory databases (`test_database`), `Base.metadata.create_all` automatically creates the `accounts` table with `role: Mapped[str] = mapped_column(String(16), default="player", nullable=False)`.
  - For existing persistent databases, the non-destructive SQL in `002_add_account_role.sql` can be applied without table recreation.
  - All 83 automated tests execute against in-memory SQLite and pass cleanly without schema errors.

---

## 3. Required Checks Matrix

| Security Check | Inspected Component | Finding | Status |
|---|---|---|---|
| **Admin Endpoints Protected** | `app/admin/router.py` | All 5 routes (`/me`, `/accounts`, `/role`, `/ban`, `/stats`) guarded by `Depends(get_current_admin)`. | **VERIFIED** |
| **Token Validation & Auth** | `app/account/service.py` | HMAC-SHA256 signature and expiration timestamps strictly verified. Expired/corrupted tokens return 401. | **VERIFIED** |
| **Server-Side Trust Model** | `get_current_admin` | Queries `Account.role` directly from SQL database; ignores client token payload tampering. | **VERIFIED** |
| **Dynamic Role Propagation** | `service.repository.get_by_id` | Role changes in DB take effect immediately on next request with identical token (zero caching lag). | **VERIFIED** |
| **No Insecure Defaults** | `app/config.py` | No hardcoded admin accounts; no default backdoor passwords exist in repository. | **VERIFIED** |
| **Self-Demotion Guard** | `app/admin/router.py:72` | Admin cannot demote their own account (`HTTP 400 Bad Request`). | **VERIFIED** |
| **Self-Ban Guard** | `app/admin/router.py:107`| Admin cannot ban their own account (`HTTP 400 Bad Request`). | **VERIFIED** |
| **Migration Integrity** | `migrations/002_add_account_role.sql` | Non-destructive column addition with `DEFAULT 'player'`. | **VERIFIED** |
| **Persistent Audit Logging** | `app/admin/router.py` | Admin actions currently emit structured application logs, but are **not yet written to a database audit ledger**. | **GAP IDENTIFIED** (Addressed in Phase 6.2A.2) |

---

## 4. Proposed First-Admin Bootstrap Mechanism (Design Only)

Because no public API permits admin creation, clean production deployments require a secure, operator-controlled bootstrap tool.

### Proposed CLI Design: `app/cli/admin.py`

```python
# Design Proposal for Phase 6.2A Operations Toolkit:
# Usage: python -m app.cli.admin promote <username>

import asyncio
import sys
from sqlalchemy import select, update
from app.database.session import AsyncSessionLocal
from app.account.models import Account

async def promote_user_to_admin(username: str):
    async with AsyncSessionLocal() as session:
        stmt = select(Account).where(Account.username == username)
        result = await session.execute(stmt)
        account = result.scalars().first()
        if not account:
            print(f"Error: Account '{username}' not found. Register the account first.")
            sys.exit(1)
        
        stmt_up = update(Account).where(Account.id == account.id).values(role="admin")
        await session.execute(stmt_up)
        await session.commit()
        print(f"Success: Account '{username}' (ID: {account.id}) promoted to 'admin'.")

if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] != "promote":
        print("Usage: python -m app.cli.admin promote <username>")
        sys.exit(1)
    asyncio.run(promote_user_to_admin(sys.argv[2]))
```

### Security Benefits of the CLI Bootstrap Approach:
1. **Zero Attack Surface**: Operates completely outside the HTTP network plane; cannot be triggered by remote requests.
2. **Strict Operator Control**: Requires local shell/SSH access to the hosting server or container.
3. **No Hardcoded Passwords**: The operator registers an account through normal registration with a strong password, then elevates it locally.

*(Note: Per instructions, this has NOT been implemented yet and will be added during an operations/tooling milestone.)*

---

## 5. Automated Test Suite Results

The full test suite was executed in read-only mode to verify current stability:
- **Command**: `cd ros-private-server; python -m pytest -v`
- **Total Tests**: 83 collected
- **Passed**: 83 (100% success rate)
- **Failed**: 0
- **Duration**: 3.68 seconds

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server
configfile: pytest.ini
collected 83 items

tests/test_account.py::test_health_check PASSED                          [  1%]
tests/test_account.py::test_account_register_and_login PASSED            [  2%]
tests/test_account.py::test_guest_login PASSED                           [  3%]
tests/test_account.py::test_authenticated_me_endpoint PASSED             [  4%]
tests/test_admin_rbac.py::test_unauthenticated_access_rejected PASSED    [  6%]
tests/test_admin_rbac.py::test_invalid_bearer_token_rejected PASSED      [  7%]
tests/test_admin_rbac.py::test_expired_token_rejected PASSED             [  8%]
tests/test_admin_rbac.py::test_player_attempting_admin_access_rejected PASSED [  9%]
tests/test_admin_rbac.py::test_admin_accessing_protected_routes PASSED   [ 10%]
tests/test_admin_rbac.py::test_registration_cannot_create_admin PASSED   [ 12%]
tests/test_admin_rbac.py::test_player_apis_cannot_change_own_role PASSED [ 13%]
tests/test_admin_rbac.py::test_server_side_role_verification_dynamically_enforced PASSED [ 14%]
tests/test_admin_rbac.py::test_admin_can_promote_and_demote_accounts PASSED [ 15%]
tests/test_admin_rbac.py::test_admin_self_protection_guards PASSED       [ 16%]
tests/test_admin_rbac.py::test_admin_moderation_ban_and_unban PASSED     [ 18%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_valid_single_entry PASSED [ 19%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_valid_without_battle_port PASSED [ 20%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_comments_and_empty_lines PASSED [ 21%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_invalid_field_count PASSED [ 22%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_corrupted_numerical_values PASSED [ 24%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_valid PASSED [ 25%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_invalid_ports PASSED [ 26%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_invalid_names PASSED [ 27%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_invalid_status PASSED [ 28%]
tests/test_discovery.py::TestDiscoveryService::test_generate_server_list_content_roundtrip PASSED [ 30%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_server_list_ios_endpoint PASSED [ 31%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_server_list_all_endpoint PASSED [ 32%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_system_notice_endpoint PASSED [ 33%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_discovery_servers_json_endpoint PASSED [ 34%]
tests/test_gateway_adapter.py::TestSessionRegistry::test_register_and_lookup_session PASSED [ 36%]
tests/test_gateway_adapter.py::TestSessionRegistry::test_remove_session PASSED [ 37%]
tests/test_gateway_adapter.py::TestBackendAdapter::test_create_guest_session PASSED [ 38%]
tests/test_gateway_adapter.py::TestBackendAdapter::test_bind_lobby_presence PASSED [ 39%]
tests/test_gateway_adapter.py::TestBackendAdapter::test_close_session_cleans_lobby_presence PASSED [ 40%]
tests/test_handshake.py::TestLoginHandshakePayloads::test_request_serialization_roundtrip PASSED [ 42%]
tests/test_handshake.py::TestLoginHandshakePayloads::test_response_serialization_roundtrip PASSED [ 43%]
tests/test_handshake.py::TestLocalRSATestHarness::test_key_generation_and_export PASSED [ 44%]
tests/test_handshake.py::TestLocalRSATestHarness::test_encryption_and_decryption_flow PASSED [ 45%]
tests/test_handshake.py::TestLocalRSATestHarness::test_process_handshake_success PASSED [ 46%]
tests/test_handshake.py::TestLocalRSATestHarness::test_process_handshake_corrupted_ciphertext PASSED [ 48%]
tests/test_lobby.py::test_lobby_lifecycle PASSED                         [ 49%]
tests/test_lobby.py::test_lobby_entry_without_character PASSED           [ 50%]
tests/test_matchmaking.py::test_matchmaking_queue_and_cancel PASSED      [ 51%]
tests/test_matchmaking.py::test_matchmaking_pairing PASSED               [ 53%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_basic_packet PASSED [ 54%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_sequenced_packet PASSED [ 55%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_with_acks PASSED [ 56%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_with_indexed_channel PASSED [ 57%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_with_checksum PASSED [ 59%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_full_packet_with_all_footers PASSED [ 60%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_undersized_packet PASSED [ 61%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_bad_flags PASSED [ 62%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_checksum_failure PASSED [ 63%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_packet_too_short_for_checksum PASSED [ 65%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_flag_has_acks_with_zero_count PASSED [ 66%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_truncated_acks PASSED [ 67%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_truncated_sequence_number PASSED [ 68%]
tests/test_mercury_protocol.py::TestMercuryMessageFraming::test_variable_length_message PASSED [ 69%]
tests/test_mercury_protocol.py::TestMercuryMessageFraming::test_multiple_bundled_messages PASSED [ 71%]
tests/test_mercury_protocol.py::TestMercuryMessageFraming::test_fixed_length_message PASSED [ 72%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_sequence_number_progression PASSED [ 73%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_ack_processing_advances_window PASSED [ 74%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_window_overflow_guard PASSED [ 75%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_duplicate_incoming_packet_detection PASSED [ 77%]
tests/test_mercury_transport.py::TestMercuryTransportServer::test_udp_listener_startup_and_shutdown PASSED [ 78%]
tests/test_mercury_transport.py::TestMercuryTransportServer::test_receive_and_acknowledge_reliable_datagram PASSED [ 79%]
tests/test_mercury_transport.py::TestMercuryTransportServer::test_malformed_packet_rejection_over_socket PASSED [ 80%]
tests/test_player.py::test_character_creation_and_profile PASSED         [ 81%]
tests/test_player.py::test_duplicate_nickname_across_accounts PASSED     [ 83%]
tests/test_player.py::test_update_settings_and_appearances PASSED        [ 84%]
tests/test_remediation.py::test_guest_registration_and_returning_login PASSED [ 85%]
tests/test_remediation.py::test_different_device_ids_create_different_accounts PASSED [ 86%]
tests/test_remediation.py::test_concurrent_guest_registration_same_device_id PASSED [ 87%]
tests/test_single_worker_deployment_safeguard PASSED                     [ 89%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_rooms PASSED [ 90%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_matchmaking PASSED [ 91%]
tests/test_remediation.py::test_expired_ticket_cleanup PASSED            [ 92%]
tests/test_remediation.py::test_expired_room_cleanup PASSED              [ 93%]
tests/test_remediation.py::test_active_rooms_and_valid_tickets_surviving_cleanup PASSED [ 95%]
tests/test_remediation.py::test_oversized_and_malformed_appearance_settings_payload_rejection PASSED [ 96%]
tests/test_remediation.py::test_login_rate_limiting PASSED               [ 97%]
tests/test_remediation.py::test_registration_rate_limiting PASSED        [ 98%]
tests/test_room.py::test_room_management PASSED                          [100%]

============================= 83 passed in 3.68s ==============================
```

---

## 6. Final Audit Verdict

```
+-------------------------------------------------------------------------------+
|                               AUDIT VERDICT: PASS                             |
+-------------------------------------------------------------------------------+
| - RBAC authorization correctly implemented.                                   |
| - Privilege escalation vectors neutralized.                                   |
| - Banned accounts strictly blocked from all protected routes.                 |
| - Dynamic server-side role evaluation confirmed.                              |
| - Self-protection failsafes verified.                                         |
| - Schema migration syntax documented and non-destructive.                     |
| - 83 of 83 automated tests passed.                                            |
+-------------------------------------------------------------------------------+
```

---

## 7. Next Milestone Readiness

The backend is fully verified and ready for:
**Milestone 6.2A.2: Diamond Currency Ledger & Transaction Engine**:
- Relational `DiamondTransaction` ledger with balance invariants (`balance_after >= 0`).
- Idempotency key tracking.
- Protected admin endpoints (`/api/v1/admin/characters/{gid}/diamonds/grant` and `/revoke`).

Awaiting your review and explicit approval before starting Milestone 6.2A.2.
