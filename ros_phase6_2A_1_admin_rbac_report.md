# ROS Sothat — Phase 6.2A.1: Admin RBAC Implementation Report

**Date**: November 11, 2026  
**Auditor & Implementation Agent**: Antigravity (Advanced Agentic Coding Assistant)  
**Target Platform**: Independent Private Server Backend (`ros-private-server`)  
**Milestone**: Phase 6.2A.1 (Admin Role-Based Access Control)  
**Mode**: Strict Clean-Room Implementation. Original iOS IPA untouched. No client patching. No key replacement. No original-client compatibility claims. Zero database migrations executed on production. Localhost and in-memory test traffic only.

---

## 1. Executive Summary

Milestone 6.2A.1 establishes the foundational **Role-Based Access Control (RBAC)** infrastructure for the ROS Sothat private server backend. This milestone secures the administrative control plane, preventing unauthorized access, privilege escalation, and unintended role modification.

Key achievements:
1. **Server-Side Account Role Invariant**: Added `role` field to `Account` model with default `"player"`. Supported roles: `"player"` and `"admin"`. Public registration cannot create admin accounts (`extra="forbid"` on `AccountRegister`), and player APIs cannot escalate privileges.
2. **Dynamic Server-Side RBAC Guard**: Implemented `get_current_admin` FastAPI dependency. Authentication verifies bearer tokens, but role checks query the fresh, authoritative database record directly (`Account.role == "admin"`), neutralizing token-tampering and client-side claims.
3. **Admin Control Plane**: Created dedicated `app/admin/` router offering protected management endpoints (`/api/v1/admin/me`, `/api/v1/admin/accounts`, `/api/v1/admin/accounts/{id}/role`, `/api/v1/admin/accounts/{id}/ban`, `/api/v1/admin/stats`). Added self-demotion and self-ban protection guards for active admins.
4. **Complete Regression Safety**: All 72 existing baseline tests passed, and 11 new comprehensive RBAC unit and integration tests passed (83 total passed in 5.48s, 100% success rate).

---

## 2. Files Changed and Created

### 2.1 Modified Existing Files

| File Path | Component | Changes Made |
|---|---|---|
| `app/account/models.py` | Account Model | Added `role: Mapped[str] = mapped_column(String(16), default="player", nullable=False)`. |
| `app/account/schemas.py` | Account Schemas | Added `role` to `AccountOut`; configured `extra="forbid"` on `AccountRegister`; added `RoleUpdateRequest` and `BanUpdateRequest`. |
| `app/account/repository.py` | Repository | Added `role="player"` parameter to `create()`; implemented `update_role()`, `set_banned()`, and `list_accounts()`. |
| `app/account/service.py` | Account Service | Propagated `role` in `create_token` and `AccountOut` mappings; implemented `get_current_admin` security dependency checking trusted DB state. |
| `app/account/router.py` | Account Router | Updated `/me` response to map `role=current_account.role`. |
| `app/main.py` | Application Entry | Imported and mounted `admin_router` under `/api/v1/admin`. |

### 2.2 New Files Created

| File Path | Purpose |
|---|---|
| `app/admin/__init__.py` | Admin package export. |
| `app/admin/router.py` | Dedicated administrative router protected by `Depends(get_current_admin)`. |
| `migrations/002_add_account_role.sql` | Documented migration script for SQLite and PostgreSQL schema evolution. |
| `tests/test_admin_rbac.py` | 11 comprehensive automated tests covering authentication rejection, RBAC enforcement, dynamic promotion/demotion, and admin operations. |

---

## 3. Authorization & Security Architecture

```
+--------------------------------------------------------------------------------------------------+
|                                    RBAC Authorization Pipeline                                   |
+--------------------------------------------------------------------------------------------------+
| Client Request with Bearer Token                                                                 |
|   |                                                                                              |
|   v                                                                                              |
| 1. security: HTTPBearer(auto_error=False)                                                        |
|    - IF missing / no credentials -> HTTP 401 Unauthorized ("Missing Bearer token")               |
|    |                                                                                             |
|    v                                                                                             |
| 2. service.verify_token(token)                                                                   |
|    - Validates HMAC-SHA256 signature against SECRET_KEY                                          |
|    - Checks expiration timestamp (exp > time.time())                                             |
|    - IF invalid / expired / tampered -> HTTP 401 Unauthorized ("Invalid or expired token")       |
|    |                                                                                             |
|    v                                                                                             |
| 3. service.repository.get_by_id(account_id) [CRITICAL SECURITY INVARIANT]                         |
|    - Loads fresh Account entity from authoritative SQL database (ignores any client claims)      |
|    - IF account not found -> HTTP 404 Not Found                                                  |
|    - IF account.is_banned == True -> HTTP 403 Forbidden ("Account is banned")                    |
|    |                                                                                             |
|    +-----------------------------------------------+                                             |
|    | Endpoint Requires Standard Player Access:     | Endpoint Requires Admin Access:             |
|    | Returns Account model (HTTP 200)             | Passes Account to get_current_admin         |
|    +-----------------------------------------------+                                             |
|                                                            |                                     |
|                                                            v                                     |
|                                            4. get_current_admin dependency:                      |
|                                               - Evaluates: account.role == "admin"               |
|                                               - IF role != "admin" -> HTTP 403 Forbidden         |
|                                                 ("Admin privileges required.")                   |
|                                               - IF role == "admin" -> Access Granted (HTTP 200)  |
+--------------------------------------------------------------------------------------------------+
```

### Key Security Safeguards
1. **Zero Client Authority Over Roles**: The client cannot specify a role in registration (`extra="forbid"` on `AccountRegister` rejects requests with extra fields with HTTP 422).
2. **Server-Side Trust Model**: Even though JWT/token payloads include `"role"`, the `get_current_admin` dependency performs authorization exclusively against the fresh database record fetched by ID (`account.role == "admin"`). Token tampering is completely ineffective.
3. **Dynamic Revocation / Immediate Propagation**: If an admin demotes a user in the database, that user's next request is immediately rejected with HTTP 403 without waiting for the JWT access token to expire.
4. **Admin Self-Protection Failsafes**: An authenticated admin cannot demote their own account (`admin.id == account_id`) or ban their own account, preventing accidental total lockout of administrative access.

---

## 4. Database & Schema Impact

### 4.1 Schema Modification
The `accounts` table definition was updated to include the `role` column:

```sql
-- SQLite (and in-memory test engine):
ALTER TABLE accounts ADD COLUMN role VARCHAR(16) NOT NULL DEFAULT 'player';

-- PostgreSQL:
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS role VARCHAR(16) NOT NULL DEFAULT 'player';
```

### 4.2 Database Safety Verification
- **In-Memory Testing**: Automated test suites use isolated in-memory SQLite instances (`sqlite+aiosqlite:///:memory:`) using `Base.metadata.create_all`, which automatically creates the updated table schema.
- **Production Safety**: No migration was executed automatically. The migration file `migrations/002_add_account_role.sql` is provided strictly as reference documentation. No existing persistent database records were altered.

---

## 5. Test Results & Verification

All automated tests were executed using `pytest -v` within the isolated backend environment.

### Summary
- **Total Tests Collected**: 83
- **Passed**: 83 (100%)
- **Failed**: 0
- **Execution Time**: 5.48 seconds

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
tests/test_remediation.py::test_single_worker_deployment_safeguard PASSED [ 89%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_rooms PASSED [ 90%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_matchmaking PASSED [ 91%]
tests/test_remediation.py::test_expired_ticket_cleanup PASSED            [ 92%]
tests/test_remediation.py::test_expired_room_cleanup PASSED              [ 93%]
tests/test_remediation.py::test_active_rooms_and_valid_tickets_surviving_cleanup PASSED [ 95%]
tests/test_remediation.py::test_oversized_and_malformed_appearance_settings_payload_rejection PASSED [ 96%]
tests/test_remediation.py::test_login_rate_limiting PASSED               [ 97%]
tests/test_remediation.py::test_registration_rate_limiting PASSED        [ 98%]
tests/test_room.py::test_room_management PASSED                          [100%]

============================= 83 passed in 5.48s ==============================
```

---

## 6. Security Review & Unresolved Risks

### 6.1 Security Review
1. **Confidentiality & Credential Safety**: No hardcoded passwords, tokens, or private keys exist in the codebase.
2. **Access Control**: Every endpoint mounted under `/api/v1/admin` is guarded by `Depends(get_current_admin)`. Ordinary player accounts receive `403 Forbidden` on every admin route.
3. **Privilege Escalation Neutralized**: Registration models strictly forbid extra fields (`model_config = ConfigDict(extra="forbid")`). Attempts to send `{"role": "admin"}` fail at the HTTP validation layer.
4. **No Replay or Token Tampering Vulnerability**: Because `get_current_admin` directly queries `Account.role` from the database, altering a token payload on the client side cannot bypass authorization.

### 6.2 Unresolved Risks & Next Phase Considerations
1. **Initial Admin Provisioning**: When deploying a clean production database, the first admin account must be provisioned via an administrative CLI script or direct database seed, as no public endpoint permits role creation. A standard CLI seed utility will be provided in a future operations milestone.
2. **Admin Audit Logging**: Administrative actions (bans, promotions) currently emit structured debug/info logs. For compliance and full auditing, subsequent phases will write admin events to an immutable database audit log alongside diamond transaction ledgers.

---

## 7. Next Milestone: Diamond Currency Ledger & Safeguards

With the admin RBAC infrastructure fully operational and verified, the next implementation milestone in the Phase 6.2A roadmap is:
- **Milestone 6.2A.2: Diamond Currency Ledger & Transaction Engine**:
  - Implement `DiamondTransaction` database model.
  - Implement atomic credit/debit operations with negative balance prevention (`balance_after >= 0`).
  - Implement idempotency key deduplication.
  - Expose `/api/v1/admin/characters/{gid}/diamonds/grant` and `/revoke` endpoints.

---

## 8. Conclusion and Gate Status

Milestone 6.2A.1 is **fully complete**. All acceptance criteria have been met with zero regressions across the 83-test suite.

In strict compliance with instructions:
- **Diamond transactions have not been implemented yet**.
- **No inventory or room changes have been made**.
- **The original IPA remains untouched**.
- **All further development is stopped awaiting your review and approval**.
