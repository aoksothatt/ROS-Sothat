# ROS Sothat — Phase 6.1: Server Discovery & Mercury UDP Transport Prototype Report

**Date**: November 11, 2026  
**Auditor & Implementation Agent**: Antigravity (Advanced Agentic Coding Assistant)  
**Target Platform**: iOS Only (`RoS-Legacy-iOS.ipa`)  
**Objective**: Build the initial network foundation for ROS Sothat private server: Server Discovery service, Mercury UDP transport prototype, RSA handshake research and test harness, and backend adapter.  
**Mode**: Strict Clean-Room Implementation. Original IPA unchanged. No database records modified. No database migrations run. Localhost and private test traffic only.

---

## 1. Executive Summary

Phase 6.1 establishes the technical foundation for connecting the original Rules of Survival (ROS) Legacy iOS client to our private server. This phase bridges the architectural gap between the existing Phase 5 HTTP/REST backend and the client's native networking stack:

1. **Server Discovery (`server_list_ios.txt`)**: Implemented the discovery service generating the 11-column server list format parsed by the iOS client (`common/serverlist_utils.py` and `ui/UILogin.py`). Server IP and UDP ports are fully configurable via environment variables. Every response is verified against the recovered client-side parser.
2. **Mercury UDP Transport Prototype**: Implemented an asynchronous UDP listener (`asyncio.DatagramProtocol`) supporting the BigWorld Mercury datagram framing recovered from native ARM64 disassembly (`neox::bwclient::Mercury`). Features reverse-order footer unpacking, checksum verification, 16-bit flags validation, sliding window sequencing, and window overflow enforcement (256 unacked packets).
3. **RSA Handshake Research & Test Harness**: Documented the LoginApp two-tier authentication handshake, identifying known architectural facts versus NetEase proprietary unknowns. Built a local test harness utilizing 2048-bit RSA encryption to verify the handshake flow in isolation.
4. **Backend Adapter**: Implemented an in-memory session registry and adapter connecting Mercury player sessions to existing account and lobby presence services without database migrations or schema alterations.
5. **Testing & Regression**: Executed 72 automated tests (48 new tests + 24 regression tests). All 72 passed with 100% success.

---

## 2. Files Created and Modified

### New Directories
- `ros-private-server/discovery/` — Discovery configuration, client parser, service, and FastAPI router.
- `ros-private-server/mercury/` — Mercury UDP protocol constants, packet framing, message multiplexer, virtual channel, and transport listener.
- `ros-private-server/gateway/` — LoginApp RSA handshake specification/harness and backend session adapter.
- `ros-private-server/docs/` — Protocol specifications.

### Files Created
| File Path | Subsystem | Purpose |
|---|---|---|
| `discovery/config.py` | Discovery | `ServerEntry` data model and `DiscoverySettings` with validation. |
| `discovery/parser.py` | Discovery | Exact client-side parser replicating `parseSAServerInfo` and `parseSAServerList`. |
| `discovery/service.py` | Discovery | Generates `server_list_ios.txt` and self-validates against client parser. |
| `discovery/router.py` | Discovery | FastAPI router serving `/server_list_ios.txt`, `/server_list_all.txt`, and notices. |
| `discovery/__init__.py` | Discovery | Package exports. |
| `mercury/constants.py` | Mercury | Protocol constants, 16-bit flag bitmasks, MTU, window limits, and length types. |
| `mercury/packet.py` | Mercury | `MercuryPacket` serialization, footer backward-unpacking, and malformed rejection. |
| `mercury/message.py` | Mercury | `MercuryMessage` bundle payload framing (fixed and variable lengths). |
| `mercury/channel.py` | Mercury | `MercuryChannel` sliding window sequencing, ACKs, and overflow guards. |
| `mercury/transport.py` | Mercury | `MercuryTransportServer` and `MercuryProtocol` async UDP socket manager. |
| `mercury/__init__.py` | Mercury | Package exports. |
| `gateway/constants.py` | Gateway | Status codes (`LOGON_STATUS_OK = 0`) and session lifecycle states. |
| `gateway/handshake.py` | Gateway | LoginApp handshake specifications and `LocalRSATestHarness`. |
| `gateway/adapter.py` | Gateway | `SessionRegistry` and `BackendAdapter` connecting to `LobbyService`/`AccountService`. |
| `gateway/__init__.py` | Gateway | Package exports. |
| `docs/protocol_specification.md`| Docs | Formal specification of wire formats, flags, and discovery layouts. |
| `tests/test_discovery.py` | Tests | 14 unit and integration tests for discovery formats, parser, and endpoints. |
| `tests/test_mercury_protocol.py`| Tests | 16 tests for packet encoding, footers, checksums, and malformed rejection. |
| `tests/test_mercury_transport.py`| Tests | 7 integration tests for live localhost UDP sockets, sequencing, and ACKs. |
| `tests/test_handshake.py` | Tests | 6 tests for RSA test harness, payload encryption, and response parsing. |
| `tests/test_gateway_adapter.py` | Tests | 5 tests for session indexing, lobby presence sync, and disconnect cleanup. |

### Files Modified
| File Path | Changes Made |
|---|---|
| `app/main.py` | Registered `discovery_router` so `/server_list_ios.txt` and `/notice_ios_hw.txt` are served at root endpoints matching client expectations. |

---

## 3. Architecture & Implementation Details

```
+---------------------------------------------------------------------------------------+
|                                ROS Private Server                                     |
+---------------------------------------------------------------------------------------+
| 1. HTTP Discovery Plane (Port 50010 / 8000)                                           |
|    - GET /server_list_ios.txt -> Formats 11-column cluster table                      |
|    - Round-trip validated against recovered client parser                            |
+---------------------------------------------------------------------------------------+
| 2. Mercury UDP Transport Plane (Port 20001)                                           |
|    - MercuryTransportServer (AsyncIO DatagramProtocol socket)                        |
|    - Packet Filter: Flags validation (flags < 0x0400), size >= 3                      |
|    - Footer Unpacker (unpacks from packet tail: Checksum -> Channel -> ACKs -> Seq)   |
|    - Sliding Window: largeOutSeqAt, oldestUnackedSeq, sendWindUsage <= 256           |
|    - Channel state: INITIALIZING -> ESTABLISHED -> DISCONNECTED                       |
+---------------------------------------------------------------------------------------+
| 3. Gateway & Adapter Interface                                                        |
|    - LocalRSATestHarness (2048-bit RSA OAEP encryption/decryption)                   |
|    - SessionRegistry (In-memory lookup by sessionKey, accountId, socketAddr)         |
|    - BackendAdapter (Bridges to AccountService & LobbyService presence)               |
+---------------------------------------------------------------------------------------+
| 4. Existing REST & Database Layer (Untouched)                                         |
|    - AccountService, LobbyService, RoomService, MatchmakingService                    |
|    - SQLite / PostgreSQL async session (Zero migrations, zero DB changes)             |
+---------------------------------------------------------------------------------------+
```

### 3.1 Server Discovery Subsystem
- **Format Verification**: The client script `common/serverlist_utils.py` executes `parseSAServerInfo(line)` by splitting the line by spaces (`line.split(' ')`) and requiring strictly 11 items.
- **Dynamic Configuration**: Addresses (`LOGIN_UDP_HOST`, `LOGIN_UDP_PORT`, `BATTLE_UDP_PORT`) and cluster names are configurable via environment variables or `discovery_settings`. No hardcoded production IPs exist.
- **Fail-Safe Generation**: `DiscoveryService.generate_server_list_content()` runs the generated text through `parse_sa_server_list()` before returning. If any entry fails client parser validation, generation aborts with a runtime error.

### 3.2 Mercury UDP Protocol Subsystem
- **Header & Footer Symmetry**: Disassembly of `neox::bwclient::Mercury::Nub::processFilteredPacket` revealed that Mercury places metadata as footers at the *end* of the datagram:
  - Header: 2 bytes little-endian `flags` (`uint16`).
  - Tail $-4$: Checksum (`FLAG_HAS_CHECKSUM = 0x0100`).
  - Tail $-4$: Indexed Channel ID (`FLAG_INDEXED_CHANNEL = 0x0080`).
  - Tail $-1$ and $-4 \times N$: ACK array and count byte (`FLAG_HAS_ACKS = 0x0004`).
  - Tail $-4$: Sequence number (`FLAG_HAS_SEQUENCE_NUMBER = 0x0040`).
  - Body: Bytes between header offset 2 and footer start.
- **Sliding Window Invariant**: Channels track `large_out_seq_at` and `oldest_unacked_seq`. When unacknowledged packets reach 256 (`MAX_WINDOW_SIZE`), the channel disconnects with the string found in the client binary:
  `"ServerConnection::send: Disconnecting since channel has overflowed largeOutSeqAt %d, oldestUnackedSeq %d, sendWindUsage %d"`.
- **Fault-Tolerant Socket**: Corrupted packets, bad flags ($\ge 0x0400$), checksum failures, or truncated footers raise `MalformedPacketError`, are logged as warnings, update telemetry counters, and are rejected without interrupting the socket event loop.

### 3.3 Gateway Adapter
- **Clean Separation**: The Mercury layer does not perform SQL queries or modify database state.
- **SessionRegistry**: Maintains active player sessions in memory, indexed by random 32-bit `session_key`, `account_id`, and UDP address.
- **Lobby Integration**: Maps authenticated player sessions to `LobbyService.enter_lobby()` and handles cleanup on socket disconnect via `LobbyService.leave_lobby()`.

---

## 4. Verified Protocol Facts vs Assumptions and Unknowns

| Category | Protocol Item | Status | Source / Evidence |
|---|---|---|---|
| **Discovery** | URL `/server_list_ios.txt` | **Verified Fact** | `extconfigs.py.raw` string table. |
| **Discovery** | Access Server Port `50010` | **Verified Fact** | `ExtConfigs::getServiceAccessPoint` (`https://%s:50010`). |
| **Discovery** | 11-field Line Structure | **Verified Fact** | Disassembled `parseSAServerInfo` in `common/serverlist_utils.py.raw`. |
| **Transport** | Header 16-bit Flags | **Verified Fact** | Disassembly of `0x100922894: ldrh w8, [x28, #0x60]!`. |
| **Transport** | Flag Bound `flags < 0x0400` | **Verified Fact** | Disassembly of `0x100922898: cmp w8, #0x400` -> bad flags jump. |
| **Transport** | Reverse Footer Packing | **Verified Fact** | Disassembly of `sub w9, w9, #4` and `ldrb` from packet tail in `processFilteredPacket`. |
| **Transport** | Window Overflow limit = 256 | **Verified Fact** | String literal in client binary (`ServerConnection::send`). |
| **Transport** | Fixed vs Variable Length | **Verified Fact** | Disassembly of `InterfaceElement::expandLength` and `Mercury::Bundle::newMessage`. |
| **Handshake** | 2-Tier Handshake Flow | **Verified Fact** | Strings `ServerConnection::logOnBegin` and `sending base app request to %s`. |
| **Handshake** | Status Code `LOGON_STATUS_OK = 0`| **Verified Fact** | String literal `status==LOGGED_ON` and `logOnComplete`. |
| **Handshake** | Session Key is 32-bit uint32 | **Verified Fact** | Disassembly of `BaseAppLoginRequest::setNubAndSend`. |
| **Security** | NetEase RSA Private Key | **Unknown** | NetEase's private key matching embedded `loginapp.pubkey` is proprietary and unknown. |
| **Security** | Plaintext Logon Format | **Hypothesis** | Native ARM64 packing structure of credentials before RSA encryption is not fully mapped. |
| **Client** | Debug Plaintext Fallback | **Hypothesis** | Unverified whether client build has debug flags to accept unencrypted login. |

---

## 5. Test Results

All automated tests were run using `pytest -v` within the isolated environment.

### Summary
- **Total Tests Collected**: 72
- **Passed**: 72
- **Failed**: 0
- **Execution Time**: 4.98 seconds

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server
configfile: pytest.ini
collected 72 items

tests/test_account.py::test_health_check PASSED                          [  1%]
tests/test_account.py::test_account_register_and_login PASSED            [  2%]
tests/test_account.py::test_guest_login PASSED                           [  4%]
tests/test_account.py::test_authenticated_me_endpoint PASSED             [  5%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_valid_single_entry PASSED [  6%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_valid_without_battle_port PASSED [  8%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_comments_and_empty_lines PASSED [  9%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_invalid_field_count PASSED [ 11%]
tests/test_discovery.py::TestDiscoveryParser::test_parse_corrupted_numerical_values PASSED [ 12%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_valid PASSED [ 13%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_invalid_ports PASSED [ 15%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_invalid_names PASSED [ 16%]
tests/test_discovery.py::TestDiscoveryService::test_server_entry_validation_invalid_status PASSED [ 18%]
tests/test_discovery.py::TestDiscoveryService::test_generate_server_list_content_roundtrip PASSED [ 19%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_server_list_ios_endpoint PASSED [ 20%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_server_list_all_endpoint PASSED [ 22%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_system_notice_endpoint PASSED [ 23%]
tests/test_discovery.py::TestDiscoveryEndpoints::test_discovery_servers_json_endpoint PASSED [ 25%]
tests/test_gateway_adapter.py::TestSessionRegistry::test_register_and_lookup_session PASSED [ 26%]
tests/test_gateway_adapter.py::TestSessionRegistry::test_remove_session PASSED [ 27%]
tests/test_gateway_adapter.py::TestBackendAdapter::test_create_guest_session PASSED [ 29%]
tests/test_gateway_adapter.py::TestBackendAdapter::test_bind_lobby_presence PASSED [ 30%]
tests/test_gateway_adapter.py::TestBackendAdapter::test_close_session_cleans_lobby_presence PASSED [ 31%]
tests/test_handshake.py::TestLoginHandshakePayloads::test_request_serialization_roundtrip PASSED [ 33%]
tests/test_handshake.py::TestLoginHandshakePayloads::test_response_serialization_roundtrip PASSED [ 34%]
tests/test_handshake.py::TestLocalRSATestHarness::test_key_generation_and_export PASSED [ 36%]
tests/test_handshake.py::TestLocalRSATestHarness::test_encryption_and_decryption_flow PASSED [ 37%]
tests/test_handshake.py::TestLocalRSATestHarness::test_process_handshake_success PASSED [ 38%]
tests/test_handshake.py::TestLocalRSATestHarness::test_process_handshake_corrupted_ciphertext PASSED [ 40%]
tests/test_lobby.py::test_lobby_lifecycle PASSED                         [ 41%]
tests/test_lobby.py::test_lobby_entry_without_character PASSED           [ 43%]
tests/test_matchmaking.py::test_matchmaking_queue_and_cancel PASSED      [ 44%]
tests/test_matchmaking.py::test_matchmaking_pairing PASSED               [ 45%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_basic_packet PASSED [ 47%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_sequenced_packet PASSED [ 48%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_with_acks PASSED [ 50%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_with_indexed_channel PASSED [ 51%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_encode_decode_with_checksum PASSED [ 52%]
tests/test_mercury_protocol.py::TestMercuryPacketFraming::test_full_packet_with_all_footers PASSED [ 54%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_undersized_packet PASSED [ 55%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_bad_flags PASSED [ 56%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_checksum_failure PASSED [ 58%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_packet_too_short_for_checksum PASSED [ 59%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_flag_has_acks_with_zero_count PASSED [ 61%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_truncated_acks PASSED [ 62%]
tests/test_mercury_protocol.py::TestMercuryMalformedPacketRejection::test_reject_truncated_sequence_number PASSED [ 63%]
tests/test_mercury_protocol.py::TestMercuryMessageFraming::test_variable_length_message PASSED [ 65%]
tests/test_mercury_protocol.py::TestMercuryMessageFraming::test_multiple_bundled_messages PASSED [ 66%]
tests/test_mercury_protocol.py::TestMercuryMessageFraming::test_fixed_length_message PASSED [ 68%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_sequence_number_progression PASSED [ 69%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_ack_processing_advances_window PASSED [ 70%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_window_overflow_guard PASSED [ 72%]
tests/test_mercury_transport.py::TestMercuryChannelLogic::test_duplicate_incoming_packet_detection PASSED [ 73%]
tests/test_mercury_transport.py::TestMercuryTransportServer::test_udp_listener_startup_and_shutdown PASSED [ 75%]
tests/test_mercury_transport.py::TestMercuryTransportServer::test_receive_and_acknowledge_reliable_datagram PASSED [ 76%]
tests/test_mercury_transport.py::TestMercuryTransportServer::test_malformed_packet_rejection_over_socket PASSED [ 77%]
tests/test_player.py::test_character_creation_and_profile PASSED         [ 79%]
tests/test_player.py::test_duplicate_nickname_across_accounts PASSED     [ 80%]
tests/test_player.py::test_update_settings_and_appearances PASSED        [ 81%]
tests/test_remediation.py::test_guest_registration_and_returning_login PASSED [ 83%]
tests/test_remediation.py::test_different_device_ids_create_different_accounts PASSED [ 84%]
tests/test_remediation.py::test_concurrent_guest_registration_same_device_id PASSED [ 86%]
tests/test_remediation.py::test_single_worker_deployment_safeguard PASSED [ 87%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_rooms PASSED [ 88%]
tests/test_remediation.py::test_disconnected_player_cleanup_from_matchmaking PASSED [ 90%]
tests/test_remediation.py::test_expired_ticket_cleanup PASSED            [ 91%]
tests/test_remediation.py::test_expired_room_cleanup PASSED              [ 93%]
tests/test_remediation.py::test_active_rooms_and_valid_tickets_surviving_cleanup PASSED [ 94%]
tests/test_remediation.py::test_oversized_and_malformed_appearance_settings_payload_rejection PASSED [ 95%]
tests/test_remediation.py::test_login_rate_limiting PASSED               [ 97%]
tests/test_remediation.py::test_registration_rate_limiting PASSED        [ 98%]
tests/test_room.py::test_room_management PASSED                          [100%]

============================= 72 passed in 4.98s ==============================
```

---

## 6. Security Considerations

1. **Isolation from Official Services**: The prototype operates entirely on localhost and private subnets (`127.0.0.1` / private test IP). No packets are sent to or accepted from official NetEase or VNG servers.
2. **Protection of Credentials**: No actual passwords, tokens, or private keys are hardcoded, extracted, or logged. The RSA test harness generates ephemeral keys in memory.
3. **No Unauthenticated DB Access**: The Mercury transport does not expose direct database queries or raw SQL execution.
4. **Denial of Service Resistance**:
   - Oversized datagrams and illegal flags are rejected at the socket boundary before allocation.
   - Sliding window buffer exhaustion is capped at 256 unacknowledged packets.

---

## 7. Remaining Blockers to Connecting an Original iOS Client

While the technical foundation is proven in code and unit tests, three technical blockers remain before an unmodified iOS device running `RoS-Legacy-iOS.ipa` can fully enter the 3D lobby:

1. **RSA Public Key Matching (Critical)**:
   - *Blocker*: The original iOS client binary encrypts its login datagram using the public key embedded at `entities/loginapp.pubkey`. To decrypt this datagram on our private server, our backend needs the matching private key (which is proprietary to NetEase and unavailable).
   - *Resolution Options for Phase 6.2*:
     - *Option A (Sideload Patch)*: Swap `entities/loginapp.pubkey` inside the decrypted `.ipa` with our server's generated public key before signing and installing on test devices via AltStore/TrollStore.
     - *Option B (Plaintext Probe)*: Test whether the client allows an unencrypted logon packet if the LoginApp replies with a specific probe flag.
2. **Access Server Redirection & TLS (Medium)**:
   - *Blocker*: The client attempts to fetch `https://as-h45na.easebar.com:50010/server_list_ios.txt`.
   - *Resolution Options*:
     - Local Wi-Fi DNS redirection (e.g. Pi-hole / dnsmasq) redirecting `as-h45na.easebar.com` to private server LAN IP.
     - Installing a local self-signed root certificate authority (CA) on the iOS device, or configuring an HTTP proxy (mitmproxy / Charles).
3. **BigWorld Entity RPC Blueprint Implementation (Medium-High)**:
   - *Blocker*: After LoginApp issues `LOGON_STATUS_OK` and BaseApp coordinates, the client expects the BaseApp to instantiate the `Account` entity and respond to `Account.handshake` and `Account.onChannelLogin`.
   - *Resolution Planned for Phase 6.2*: Implement `LoginApp` and `BaseApp` entity lifecycle managers using the 632 recovered XML `.def` entity schemas.

---

## 8. Status and Next Steps

Phase 6.1 is **fully complete**. All objectives have been achieved, verified with automated tests, and documented.

In strict compliance with instructions:
- Phase 6.2 will not be started automatically.
- No further implementation will proceed until you review this report and give explicit approval.
