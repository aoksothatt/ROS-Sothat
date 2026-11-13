# Synthetic Validation Plan
## Comprehensive Offline Testing Strategy for Remediated Gateway
**Project:** ROS Sothat — Legacy iOS Client Private Server  
**Phase:** 6.2B.8.4 (Planning Only — Strict Read-Only)  
**Target:** Remediation Validation for `phase6B_8_local_gateway/`  
**Reference Evidence:** `ros_phase6B_8_2_native_evidence_closure_report.md`, `ros_phase6B_8_3_native_flag_compatibility_audit_report.md`  

---

## 1. Executive Summary & Purpose

This document specifies an offline synthetic test harness and validation plan designed to verify the correctness of the gateway remediation planned in Phase 6.2B.8.4.

The validation strategy ensures:
1. **Mathematical Invariance:** The low-level cryptographic pipeline (Blowfish PBC, single-byte trailer padding, and 32-bit SIMD XOR checksum) remains 100% compliant with native ARM64 evidence.
2. **Wire Protocol Conformance:** All 10 native Mercury header flags, the reverse footer layout, the 28-bit circular sequence window, and the channel activation gate operate strictly according to native BigWorld Mercury control flow.
3. **Independent Derivation:** All expected outputs and golden vectors are calculated independently using standard Python cryptographic primitives (`cryptography.hazmat.primitives.ciphers`) and struct packing, completely decoupled from the gateway implementation under test.
4. **Zero Live Environment Footprint:** All tests execute entirely offline in memory or over localhost (`127.0.0.1`), with zero external network traffic, zero database connections, and zero IPA modifications.

---

## 2. Test Suite Structure & Coverage Matrix

The validation test suite is organized into 10 structured test domains:

| Domain | Description | Target Component | Test Count |
|---|---|---|---|
| **Domain 1** | Individual Flag Isolation Tests | `packet_parser.py` | 10 Tests |
| **Domain 2** | Valid Flag Combination Matrix | `packet_parser.py`, `protocol_engine.py` | 10 Tests |
| **Domain 3** | Negative Reserved-Bit & Illegal State Tests | `packet_parser.py`, `gateway.py` | 6 Tests |
| **Domain 4** | 28-Bit Sequence Wraparound & Modular Math | `channel_manager.py` | 6 Tests |
| **Domain 5** | Half-Window Duplicate & Out-of-Order Tests | `channel_manager.py` | 6 Tests |
| **Domain 6** | Piggybacked ACK Queue Mechanics | `channel_manager.py`, `gateway.py` | 4 Tests |
| **Domain 7** | Channel Creation & Activation State Gate | `channel_manager.py`, `gateway.py` | 5 Tests |
| **Domain 8** | Bundle Fragment Footer Parsing | `packet_parser.py`, `protocol_engine.py` | 5 Tests |
| **Domain 9** | Malformed Footer & Truncation Bounds | `packet_parser.py` | 8 Tests |
| **Domain 10** | Independent Golden Vectors & Cryptographic Invariance | Full Stack Integration | 6 Tests |
| **TOTAL** | **Comprehensive Automated Verification** | | **66 Tests** |

---

## 3. Detailed Test Domain Specifications

---

### Domain 1: Individual Flag Isolation Tests (Bits 0 through 9)

Each test constructs a minimal plaintext datagram carrying exactly ONE flag bit and its required footer, verifying correct parsing and offset computation:

1. **Test 1.0 (Bit 0 — `0x0001` `FLAG_HAS_REQUESTS`):**
   - Header: `0x0001`. Footer: 2-byte uint16 First Request Offset (`<H`, e.g., `0x0010`).
   - Assertion: `unpacked["first_request_offset"] == 0x0010`, `len(unpacked["payload"]) == expected`.
2. **Test 1.1 (Bit 1 — `0x0002` `FLAG_HAS_PIGGYBACKS`):**
   - Header: `0x0002`. Footer: `b"PIGGYBACK_DATA"` + 2-byte signed length (`<h`, `14`).
   - Assertion: `unpacked["piggyback"] == b"PIGGYBACK_DATA"`.
3. **Test 1.2 (Bit 2 — `0x0004` `FLAG_HAS_ACKS`):**
   - Header: `0x0004`. Footer: `[101, 102]` (2x `<I`) + 1-byte count (`0x02`).
   - Assertion: `unpacked["acks"] == [101, 102]`.
4. **Test 1.3 (Bit 3 — `0x0008` `FLAG_ON_CHANNEL`):**
   - Header: `0x0008`. Footer: None (0 bytes).
   - Assertion: Flags parsed with `FLAG_ON_CHANNEL` set, payload starts at Offset 2.
5. **Test 1.4 (Bit 4 — `0x0010` `FLAG_IS_RELIABLE` with Bit 6):**
   - Header: `0x0050` (`0x0010 | 0x0040`). Footer: 4-byte sequence number (`<I`, `500`).
   - Assertion: `unpacked["is_reliable"] is True`, `unpacked["seq_num"] == 500`.
6. **Test 1.5 (Bit 5 — `0x0020` `FLAG_HAS_FRAGMENTS`):**
   - Header: `0x0020`. Footer: `fragBegin = 0`, `fragEnd = 3` (2x `<I`, 8 bytes).
   - Assertion: `unpacked["fragments"] == (0, 3)`, fragment count is 4.
7. **Test 1.6 (Bit 6 — `0x0040` `FLAG_HAS_SEQUENCE_NUMBER`):**
   - Header: `0x0040`. Footer: 4-byte sequence number (`<I`, `12345`).
   - Assertion: `unpacked["seq_num"] == 12345`.
8. **Test 1.7 (Bit 7 — `0x0080` `FLAG_INDEXED_CHANNEL`):**
   - Header: `0x0080`. Footer: 4-byte channel ID (`<I`, `42`).
   - Assertion: `unpacked["channel_id"] == 42`.
9. **Test 1.8 (Bit 8 — `0x0100` `FLAG_HAS_CHECKSUM`):**
   - Header: `0x0100`. Footer: 4-byte checksum placeholder (`<I`).
   - Assertion: `unpacked["has_checksum"] is True`.
10. **Test 1.9 (Bit 9 — `0x0200` `FLAG_CREATE_CHANNEL`):**
    - Header: `0x0200`. Footer: None (0 bytes).
    - Assertion: Flags parsed with `FLAG_CREATE_CHANNEL` set.

---

### Domain 2: Valid Flag Combination Matrix

Verifies legitimate flag combinations observed in native ARM64 disassembly:

1. **`0x0100` (Checksum Only):** Minimal unsequenced ping or keep-alive datagram.
2. **`0x0102` (Checksum + Piggyback):** Bundled keep-alive observed at `0x10092b524`.
3. **`0x0180` (Indexed Channel + Checksum):** Unsequenced control datagram on indexed channel.
4. **`0x03C0` (Create Channel + Indexed + SeqNum + Checksum):**
   - Value: `0x0200 | 0x0080 | 0x0040 | 0x0100 = 0x03C0`.
   - Native Use Case: Initial client handshake packet establishing channel.
5. **`0x0158` (On-Channel + SeqNum + Reliable + Checksum):**
   - Value: `0x0008 | 0x0040 | 0x0010 | 0x0100 = 0x0158`.
   - Native Use Case: Regular address-routed reliable message.
6. **`0x01D0` (Indexed Channel + SeqNum + Reliable + Checksum):**
   - Value: `0x0080 | 0x0040 | 0x0010 | 0x0100 = 0x01D0`.
   - Native Use Case: Standard sequenced application packet on indexed channel.
7. **`0x01C4` (Indexed Channel + SeqNum + ACKs + Checksum):**
   - Value: `0x0080 | 0x0040 | 0x0004 | 0x0100 = 0x01C4`.
   - Native Use Case: Application packet piggybacking ACKs for received sequence numbers.
8. **`0x01CC` (On-Channel + Indexed Channel + SeqNum + ACKs + Checksum):**
   - Value: `0x0008 | 0x0080 | 0x0040 | 0x0004 | 0x0100 = 0x01CC`.
   - Native Use Case: Gateway response datagram acknowledging client message.
9. **`0x01E0` (Indexed Channel + SeqNum + Fragments + Checksum):**
   - Value: `0x0080 | 0x0040 | 0x0020 | 0x0100 = 0x01E0`.
   - Native Use Case: Fragmented multi-datagram bundle stream.
10. **`0x03D5` (Full Complex Datagram):**
    - Value: `0x0200 | 0x0100 | 0x0080 | 0x0040 | 0x0010 | 0x0004 | 0x0001 = 0x03D5`.
    - Native Use Case: Stress test packing and unpacking with all 7 footers present simultaneously.

---

### Domain 3: Negative Reserved-Bit & Illegal State Tests

Verifies immediate rejection of forbidden bit patterns and invalid flag states:

1. **Boundary Rejection at `0x0400`:** Header flags `0x0400` raises `PacketFramingError` (`cmp w8, #0x400; b.hs`).
2. **High Bit Rejection (`0x0800`, `0x1000`, `0x8000`):** Each reserved bit independently rejected.
3. **Illegal Reliability Request:** `FLAG_IS_RELIABLE` (`0x0010`) present without `FLAG_HAS_SEQUENCE_NUMBER` (`0x0040`) raises `PacketFramingError` (matches `0x100923098` drop).
4. **Empty Datagram Rejection:** 0-byte UDP datagram raises `PacketDecryptionError`.
5. **Non-Block Multiple Datagram:** Length not divisible by 8 raises `PacketDecryptionError`.
6. **Undersized Plaintext:** Decrypted plaintext `< 2` bytes raises `PacketFramingError`.

---

### Domain 4: 28-Bit Sequence Wraparound & Modular Math

Verifies circular arithmetic in `channel_manager.py` adhering to native `0x10091b6b8: and w9, w9, #0xfffffff`:

1. **Direct Sequential Increment:** `expected_seq = 100` receives `100` -> advances to `101`.
2. **Wraparound at $2^{28}$ Boundary:**
   - Client is at `seq = 0x0FFFFFFF` ($268,435,455$).
   - Arriving datagram carries `0x0FFFFFFF` -> advances `expected_seq` to `0x00000000`.
3. **Forward Modular Progression across 0:**
   - Client is at `expected_seq = 0x00000000`.
   - Arriving datagram carries `0x00000000` -> advances to `0x00000001`.
4. **Modular Difference Computation:**
   - Current: `0x0FFFFFFF`. Incoming: `0x00000002`.
   - Computation: `(0x00000002 - 0x0FFFFFFF) & 0x0FFFFFFF = 3`.
   - Valid gap of 3 packets detected; acknowledged as out-of-order.
5. **Mask Compliance (`SEQ_NULL`):**
   - Value `0x10000000` masked to 28 bits equals `0x00000000`, distinguishing unsequenced sentinel from valid sequences.
6. **Maximum Monotonic Stress Test:** $100,000$ simulated packets crossing boundary without overflow.

---

### Domain 5: Half-Window Duplicate & Out-of-Order Tests

Verifies window boundary comparisons against half-window threshold $2^{27} = 0x08000000$ (`0x10091b6c0: movk w10, #0x800, lsl #16`):

1. **Immediate Duplicate:** Same sequence repeated returns `"DUPLICATE"`, leaves `expected_seq` unchanged.
2. **Old Sequence within Window:**
   - `expected_seq = 100`. Incoming `seq = 95`.
   - Difference: `(95 - 100) & 0x0FFFFFFF = 0x0FFFFFFB > 0x08000000`.
   - Identified as old packet -> returns `"DUPLICATE"`.
3. **Forward Gap within Half-Window:**
   - `expected_seq = 100`. Incoming `seq = 150`.
   - Difference: `50 <= 0x08000000`.
   - Identified as future packet -> returns `"OUT_OF_ORDER"`, records `150` in `seen_seqs`.
4. **Boundary Step-Down Test:**
   - `expected_seq = 0x00000010`. Incoming `seq = 0x0FFFFFE0`.
   - Difference: `(0x0FFFFFE0 - 0x00000010) & 0x0FFFFFFF = 0x0FFFFFD0 > 0x08000000`.
   - Correctly recognized as older packet from previous epoch -> returns `"DUPLICATE"`.
5. **Extreme Half-Window Edge Test:**
   - Difference exactly equal to `0x08000000` vs `0x08000001`.
6. **Immunity to State Corruption:** Processing duplicate/out-of-order never alters other active channels.

---

### Domain 6: Piggybacked ACK Queue Mechanics

Verifies outgoing ACK accumulation and consumption adhering to native `Channel::queueAckForPacket`:

1. **Single ACK Piggybacking:**
   - Incoming packet with sequence `10` is processed.
   - Channel queues ACK for `10`.
   - Outgoing response datagram carries `FLAG_HAS_ACKS` (`0x0004`), footer contains count `1` and sequence `10`.
2. **Multiple ACK Coalescing:**
   - Channel processes sequences `1`, `2`, `3` in succession.
   - Outgoing datagram carries count `3` and `[1, 2, 3]`.
3. **Queue Draining Verification:**
   - Calling `pop_pending_acks()` retrieves all queued ACKs and resets queue to empty.
   - Subsequent packet sent carries no ACK footer.
4. **ACK Count Overflow Guard:**
   - If queued ACKs exceed 255, parser raises `PacketFramingError("ACK count cannot exceed 255")`.

---

### Domain 7: Channel Creation & Activation State Gate

Verifies client-server channel establishment adhering to native `isWantingCreateChannel` lifecycle:

1. **Activation Handshake Success:**
   - Fresh channel initialized with `is_wanting_create_channel = True`.
   - Arriving datagram carries `FLAG_CREATE_CHANNEL` (`0x0200`).
   - Channel transitions to active (`is_wanting_create_channel = False`).
2. **Rejection of Unactivated Message:**
   - Arriving datagram on pending channel lacks `FLAG_CREATE_CHANNEL` (`0x0200`).
   - Gateway drops packet immediately (error: `"Dropping packet on channel wanting FLAG_CREATE_CHANNEL"`).
3. **Creation Flag on Established Channel:**
   - Packet carrying `0x0200` arrives on already active channel.
   - Cleanly resets sequence counters without crashing or dropping.
4. **Unknown Channel Rejection:**
   - Packet arrives with unmapped Channel ID.
   - Gateway drops packet with `UNKNOWN_CHANNEL`.
5. **Channel Isolation Verification:**
   - Activating Channel 1 does not activate or reset Channel 2.

---

### Domain 8: Bundle Fragment Footer Parsing

Verifies multi-packet fragment footer unpacking adhering to native `0x100923948`:

1. **Standard 8-Byte Fragment Footer:**
   - Flag `0x0020` set. Footer: `fragBegin = 0`, `fragEnd = 2` (3 fragments total).
   - Unpacker extracts `frag_begin == 0`, `frag_end == 2`, remaining payload intact.
2. **Fragment Calculation Verification:**
   - Verification formula: $\text{count} = \text{fragEnd} - \text{fragBegin} + 1 = 3$.
3. **Malformed Fragment Inversion:**
   - `fragBegin = 5`, `fragEnd = 2` ($\text{fragEnd} < \text{fragBegin}$).
   - Unpacker raises `PacketFramingError("Illegal fragment range")`.
4. **Reverse-Order Alignment with Sequence & Checksum:**
   - Datagram with `Checksum (4B)` + `SeqNum (4B)` + `Fragments (8B)` correctly unpacks all three footers in reverse order.
5. **Oversized Bundle Count Rejection:**
   - Fragment count exceeding configured maximum bundle size rejected.

---

### Domain 9: Malformed Footer & Truncation Bounds

Verifies resilience against corrupted or truncated packet tails:

1. **Truncated Checksum Footer:** Flag `0x0100` present, but total packet length `< 6` bytes (need 2B header + 4B checksum).
2. **Truncated Sequence Number Footer:** Flag `0x0040` present, but remaining tail `< 4` bytes.
3. **Truncated Channel ID Footer:** Flag `0x0080` present, but remaining tail `< 4` bytes.
4. **Truncated ACK Count Footer:** Flag `0x0004` present, but remaining tail `< 1` byte.
5. **Zero ACK Count Error:** Flag `0x0004` present, but ACK count byte is `0x00` (violates native constraint).
6. **Truncated ACK Sequence Array:** ACK count is 3, but remaining tail has fewer than 12 bytes.
7. **Truncated Fragment Footer:** Flag `0x0020` present, but remaining tail `< 8` bytes.
8. **Truncated Request Offset Footer:** Flag `0x0001` present, but remaining tail `< 2` bytes.

---

### Domain 10: Independent Golden Vectors & Cryptographic Invariance

Derived 100% independently using `cryptography.hazmat.primitives.ciphers.Cipher(Blowfish(KEY), modes.ECB())` and pure Python struct packing (see `calc_vectors.py`):

```
Master Key (56 bytes):
b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"
Hex: 524f535f534f544841545f44455445524d494e49535449435f53594e5448455449435f424c4f57464953485f53455353494f4e5f4b455921
```

#### Vector A: Login Request Datagram (Corrected Flag `0x01C0`)
- **Flags:** `FLAG_HAS_CHECKSUM (0x0100) | FLAG_INDEXED_CHANNEL (0x0080) | FLAG_HAS_SEQUENCE_NUMBER (0x0040) = 0x01C0`
- **Payload (47B):** `b'{"account":"test_user","token":"syn_token_123"}'`
- **Sequence Number:** `1001` (`<I: 0xe9030000`)
- **Channel ID:** `1` (`<I: 0x01000000`)
- **Raw Length:** `61` bytes
- **Golden 32-bit XOR Checksum:** `0x7b76bada`
- **Padded Length:** `64` bytes (3 bytes padding: `0x00 0x00 0x03`)
- **Independent Ciphertext Hex (64 bytes):**
  ```
  b7036a2c2f2da84561b21f7f1c52e9f6d145579be893d283d5cad5d289475c08ed1c1caaa342ecce31155d44b60ba67bc8519d3fbcf2c7df57d9371d16c659e8
  ```

#### Vector B: Channel 1 Initialization Request (Corrected Flag `0x03C0`)
- **Flags:** `FLAG_CREATE_CHANNEL (0x0200) | FLAG_INDEXED_CHANNEL (0x0080) | FLAG_HAS_SEQUENCE_NUMBER (0x0040) | FLAG_HAS_CHECKSUM (0x0100) = 0x03C0`
- **Payload (51B):** `b'{"action": "INIT_CHANNEL", "session_id": "sess_01"}'`
- **Sequence Number:** `1` (`<I: 0x01000000`)
- **Channel ID:** `1` (`<I: 0x01000000`)
- **Raw Length:** `65` bytes
- **Golden 32-bit XOR Checksum:** `0x034614e4`
- **Padded Length:** `72` bytes (7 bytes padding: `0x00*6 + 0x07`)
- **Independent Ciphertext Hex (72 bytes):**
  ```
  a4888882203c781be215b8e8e5d216a7b6a458cd99c422edbc26534e6dde6eeb2993ef333f5a7096f9287dca9ed23679b5829c275d42143efd0ae49515cb7336c915ca5b5fbc2e38
  ```

#### Vector C: Application Message on Channel 1 (Corrected Flag `0x01C8`)
- **Flags:** `FLAG_ON_CHANNEL (0x0008) | FLAG_INDEXED_CHANNEL (0x0080) | FLAG_HAS_SEQUENCE_NUMBER (0x0040) | FLAG_HAS_CHECKSUM (0x0100) = 0x01C8`
- **Payload (25B):** `b"PING_MESSAGE_ON_CHANNEL_1"`
- **Sequence Number:** `2` (`<I: 0x02000000`)
- **Channel ID:** `1` (`<I: 0x01000000`)
- **Raw Length:** `39` bytes
- **Golden 32-bit XOR Checksum:** `0x043f1ec7`
- **Padded Length:** `40` bytes (1 byte padding: `0x01`)
- **Independent Ciphertext Hex (40 bytes):**
  ```
  49b5eb66b9bd84a291e6fb8b81d8d485c8a2ad12404d3c2fe833d666c0acb182bdd4a6fa46a65029
  ```

#### Vector D: Application Response with Piggybacked ACK (Corrected Flag `0x01CC`)
- **Flags:** `FLAG_ON_CHANNEL (0x0008) | FLAG_INDEXED_CHANNEL (0x0080) | FLAG_HAS_SEQUENCE_NUMBER (0x0040) | FLAG_HAS_ACKS (0x0004) | FLAG_HAS_CHECKSUM (0x0100) = 0x01CC`
- **Payload (38B):** `b"ACK_AND_ECHO:PING_MESSAGE_ON_CHANNEL_1"`
- **Sequence Number:** `1001` (`<I: 0xe9030000`)
- **Piggybacked ACKs:** `[2]` (1 byte count `0x01` + 4 bytes `<I: 0x02000000`)
- **Channel ID:** `1` (`<I: 0x01000000`)
- **Raw Length:** `57` bytes
- **Golden 32-bit XOR Checksum:** `0x71604366`
- **Padded Length:** `64` bytes (7 bytes padding: `0x00*6 + 0x07`)
- **Independent Ciphertext Hex (64 bytes):**
  ```
  4a2ecb8a13e4374dfb0d9e35c473f6b4b33c3b2b657dd3d449a88cc671b2ea56a5d6c1a722ecb444f71e579a3df958a32148fcfff038339256cf717fe681381a
  ```

---

## 4. Execution Protocol & Pass Criteria

1. **Pre-Requisite Check:** Verify python environment has `cryptography` installed.
2. **Offline Execution:** Tests must be runnable via `python tests/run_all_tests.py` with zero socket warnings.
3. **100% Pass Threshold:** All 66 tests across the 10 domains must pass with 0 errors, 0 failures, and 0 warnings.
4. **Zero Flakiness:** All tests are deterministic with fixed time inputs and deterministic keys.
