# ROS Sothat — Phase 6.2B.8.4
# Native Mercury Gateway Remediation Planning Report
**Strict Read-Only Technical Planning & Architectural Roadmap**

**Auditor:** Google DeepMind Agentic AI Assistant (Antigravity)  
**Project:** ROS Sothat — Rules of Survival Legacy iOS Client Private Server  
**Date:** November 13, 2026  
**Classification:** STRICT READ-ONLY PROTOCOL REMEDIATION PLANNING  
**Deliverables Produced:**
1. [`phase6B_8_4_remediation_plan/gateway_remediation_plan.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_4_remediation_plan/gateway_remediation_plan.md)
2. [`phase6B_8_4_remediation_plan/synthetic_validation_plan.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_4_remediation_plan/synthetic_validation_plan.md)
3. [`phase6B_8_4_remediation_plan/unresolved_protocol_questions.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_4_remediation_plan/unresolved_protocol_questions.md)
4. [`ros_phase6B_8_4_remediation_planning_report.md`](file:///d:/ROS-Legacy-Analysis/ros_phase6B_8_4_remediation_planning_report.md)

---

## 1. Executive Summary & Mandate

During Phase 6.2B.8.2 and Phase 6.2B.8.3, instruction-level reverse engineering of the pristine Rules of Survival iOS Mach-O binary (`extracted/Payload/client.app/client`) resolved the native NetEase BigWorld Mercury UDP wire protocol. That audit confirmed that while the prototype gateway's low-level cryptographic pipeline (Blowfish PBC, single-byte wastage count padding, and 32-bit SIMD XOR checksum) is 100% bit-for-bit identical to the native client, the prototype contains critical flag misallocations, missing footer handlers, and incomplete reliability semantics that would prevent communication with an original, unmodified physical client.

The mandate for **Phase 6.2B.8.4** is **STRICT READ-ONLY PLANNING**. Under this mandate:
- **Zero code files have been modified.** The existing implementation in `phase6B_8_local_gateway/` remains untouched, fully functional, and self-consistent for isolated testing.
- **Zero sockets or network operations were initiated.**
- **Zero database interactions occurred.**
- An exhaustive, file-by-file engineering plan, offline synthetic validation matrix, and technical gap analysis have been authored to govern the future Phase 6.2B.8.5 implementation.

---

## 2. Comprehensive Discrepancy Breakdown

The table below contrasts the native BigWorld Mercury protocol with the prototype gateway (`phase6B_8_local_gateway/`), specifying the exact remediation required:

| Protocol Feature | Native ARM64 Disassembly Ground Truth | Synthetic Gateway Current State | Status | Required Remediation Action |
|---|---|---|---|---|
| **Header Flags Width** | 16-bit uint16 `<H` at Offset 0 (`0x100922894`) | 16-bit uint16 `<H` at Offset 0 (`packet_parser.py:131`) | **MATCH** | None |
| **Upper Bound Check** | Discard if $\ge 0x0400$ (`0x100922898: cmp w8, #0x400`) | Discard if `flags >= 0x0400` (`packet_parser.py:132`) | **MATCH** | None |
| **Flag: Checksum** | Bit 8 (`0x0100`, VA `0x100922970`) | `FLAG_HAS_CHECKSUM = 0x0100` (`packet_parser.py:32`) | **MATCH** | None |
| **Flag: Indexed Channel** | Bit 7 (`0x0080`, VA `0x100922980`) | `FLAG_INDEXED_CHANNEL = 0x0080` (`packet_parser.py:31`) | **MATCH** | None |
| **Flag: Piggybacks** | Bit 1 (`0x0002`, VA `0x10092297c`) | `FLAG_HAS_PIGGYBACKS = 0x0002` (`packet_parser.py:26`) | **MATCH** | None |
| **Flag: Sequence Number** | Bit 6 (`0x0040`, VA `0x10092299c: tbz w8, #6`) | `FLAG_HAS_SEQUENCE_NUMBER = 0x0004` (Bit 2) | **MISMATCH** | Change `FLAG_HAS_SEQUENCE_NUMBER` to `0x0040` |
| **Flag: Piggybacked ACKs** | Bit 2 (`0x0004`, VA `0x100922994: tbnz w8, #2`) | `FLAG_HAS_ACKS = 0x0008` (Bit 3) | **MISMATCH** | Change `FLAG_HAS_ACKS` to `0x0004` |
| **Flag: On Channel (Addr)** | Bit 3 (`0x0008`, VA `0x100922984: tbnz w8, #3`) | `FLAG_ON_CHANNEL = 0x0020` (Bit 5) | **MISMATCH** | Change `FLAG_ON_CHANNEL` to `0x0008` |
| **Flag: Request Offset** | Bit 0 (`0x0001`, VA `0x100923908: tbz w8, #0`) | `FLAG_HAS_REQUESTS = 0x0040` (Bit 6) | **MISMATCH** | Change `FLAG_HAS_REQUESTS` to `0x0001` |
| **Flag: Create Channel** | Bit 9 (`0x0200`, VA `0x1009228b8`, `0x100923208`)| `FLAG_CREATE_CHANNEL = 0x0001` (Bit 0) | **MISMATCH** | Change `FLAG_CREATE_CHANNEL` to `0x0200` |
| **Flag: Reliability Req** | Bit 4 (`0x0010`, VA `0x100922f70: tbnz w8, #4`)| Missing from flag enum | **MISSING** | Add `FLAG_IS_RELIABLE = 0x0010` |
| **Flag: Bundle Fragments**| Bit 5 (`0x0020`, VA `0x100923948: tbnz w8, #5`)| Misallocated to `FLAG_ON_CHANNEL` | **MISMATCH** | Add `FLAG_HAS_FRAGMENTS = 0x0020` + 8B footer |
| **Sequence Difference** | 28-bit modular difference `& 0x0FFFFFFF` (`0x10091b6b8`)| Monotonic linear integer arithmetic | **PARTIAL** | Implement `(seq - expected) & 0x0FFFFFFF` |
| **Half-Window Threshold** | $2^{27} = 0x08000000$ (`0x10091b6c0: movk w10, #0x800`)| Unbounded integer check | **MISSING** | Check duplicate/old if diff $> 0x08000000$ |
| **Channel Activation** | Arriving `0x0200` clears `isWantingCreateChannel`| Transitions state on `0x0001` | **MISMATCH** | Enforce `0x0200` gate; drop unactivated pkts |
| **Blowfish PBC Mode** | $C_0 = E(P_0)$, $C_i = E(P_i \oplus P_{i-1})$ (`0x10091c82c`)| $C_0 = E(P_0)$, $C_i = E(P_i \oplus P_{i-1})$ | **MATCH** | Retain without modification |
| **Single-Byte Padding** | Trailer wastage count $1 \le L \le 8$ at `buf[-1]` | Trailer wastage count $1 \le L \le 8$ at `buf[-1]` | **MATCH** | Retain without modification |
| **32-Bit XOR Checksum** | 32-bit bitwise XOR over `<I` dwords with zero tail | 32-bit bitwise XOR over `<I` dwords with zero tail | **MATCH** | Retain without modification |

---

## 3. File-by-File Remediation Roadmap

The remediation plan details specific modifications across 6 gateway source files and test modules:

### 1. `phase6B_8_local_gateway/packet_parser.py`
- **Current Lines 24–38:**
  Update `MercuryPacketFlags` enumeration:
  ```python
  class MercuryPacketFlags:
      FLAG_HAS_REQUESTS        = 0x0001  # Bit 0 (was 0x0040)
      FLAG_HAS_PIGGYBACKS      = 0x0002  # Bit 1 (unchanged)
      FLAG_HAS_ACKS            = 0x0004  # Bit 2 (was 0x0008)
      FLAG_ON_CHANNEL          = 0x0008  # Bit 3 (was 0x0020)
      FLAG_IS_RELIABLE         = 0x0010  # Bit 4 (NEW)
      FLAG_HAS_FRAGMENTS       = 0x0020  # Bit 5 (was On-Channel)
      FLAG_HAS_SEQUENCE_NUMBER = 0x0040  # Bit 6 (was 0x0004)
      FLAG_INDEXED_CHANNEL     = 0x0080  # Bit 7 (unchanged)
      FLAG_HAS_CHECKSUM        = 0x0100  # Bit 8 (unchanged)
      FLAG_CREATE_CHANNEL      = 0x0200  # Bit 9 (was 0x0001)
  ```
- **Current Lines 66–115 (`pack`):**
  - Add `fragments: Optional[Tuple[int, int]] = None` (`fragBegin`, `fragEnd`).
  - Assemble footers in physical forward order such that reverse unwinding matches native unpacking order.
- **Current Lines 130–210 (`unpack_footers`):**
  - Add unpacking step for `FLAG_HAS_FRAGMENTS` (8 bytes: 2x `<I`).
  - Add semantic assertion: if `flags & FLAG_IS_RELIABLE` (`0x0010`) is present, `seq_num` must NOT be `None`.

### 2. `phase6B_8_local_gateway/channel_manager.py`
- **Current Lines 41–62 (`ChannelState.__init__`):**
  - Add `self.is_wanting_create_channel = True` to track channel activation lifecycle.
- **Current Lines 81–103 (`process_incoming_packet`):**
  - Define `SEQ_MASK = 0x0FFFFFFF` (28 bits) and `HALF_WINDOW = 0x08000000` ($2^{27}$).
  - Calculate modular difference: `diff = (seq_num - self.expected_seq) & SEQ_MASK`.
  - If `diff == 0`: Sequential advance `expected_seq = (self.expected_seq + 1) & SEQ_MASK`.
  - If `diff > HALF_WINDOW`: Older packet / duplicate -> return `"DUPLICATE"`.
  - If `0 < diff <= HALF_WINDOW`: Gap detected -> return `"OUT_OF_ORDER"`, queue ACK.

### 3. `phase6B_8_local_gateway/synthetic_client.py`
- **Current Lines 54–67 (`send_init`):**
  - Update flag calculation: `0x0200 | 0x0080 | 0x0040 | 0x0100 = 0x03C0` (was `0x0185`).
  - Advance `current_seq = (self.current_seq + 1) & 0x0FFFFFFF`.
- **Current Lines 87–102 (`send_message`):**
  - Update flag calculation: `0x0008 | 0x0080 | 0x0040 | 0x0100 = 0x01C8` (or `0x01D8` if reliable).
  - Advance `current_seq = (self.current_seq + 1) & 0x0FFFFFFF`.

### 4. `phase6B_8_local_gateway/gateway.py`
- **Current Lines 212–215 (`_handle_datagram`):**
  - Check `flags & MercuryPacketFlags.FLAG_CREATE_CHANNEL` (`0x0200`).
  - Enforce drop rule if channel is wanting creation and packet lacks `0x0200`.
  - Enforce drop rule if `FLAG_IS_RELIABLE` is set without `FLAG_HAS_SEQUENCE_NUMBER`.
- **Current Lines 305–320 and 350–365 (Response datagram assembly):**
  - Update response flags to `0x0008 | 0x0080 | 0x0040 | 0x0004 | 0x0100 = 0x01CC` (or `0x01DC` if reliable).

### 5. `phase6B_8_local_gateway/protocol_engine.py`
- Add pass-through support for `fragments` tuple and `is_reliable` boolean.

### 6. `phase6B_8_local_gateway/tests/`
- Update golden vector constants in `test_unit.py`.
- Add test cases in `test_channel_state.py` for 28-bit wraparound, half-window comparisons, and channel activation gates.
- Update expected wire flags across all 14 integration scenarios in `test_udp_integration.py`.

---

## 4. Reverse Footer Layout Specification

Native BigWorld Mercury unrolls footers strictly from the datagram tail backwards. To achieve this, the forward assembly and reverse unpacking layouts are defined as follows:

```
+===================================================================================================+
|                                    FORWARD WIRE PACKET LAYOUT                                     |
+---------------------------------------------------------------------------------------------------+
| Offset 0           Offset 2                                                                  Tail |
| [Header Flags 2B]  [Payload Body]  [Footers in Forward Assembly Order..........................] |
+===================================================================================================+

FOOTERS FORWARD ASSEMBLY ORDER (pack()):
1. First Request Offset (Bit 0, 0x0001):  2 bytes uint16 (<H)
2. Bundle Fragments     (Bit 5, 0x0020):  8 bytes (fragBegin 4B <I, fragEnd 4B <I)
3. Sequence Number      (Bit 6, 0x0040):  4 bytes uint32 (<I)
4. Piggybacked ACKs     (Bit 2, 0x0004):  N*4 bytes seqs (<I...) + 1 byte count (<B)
5. Indexed Channel ID   (Bit 7, 0x0080):  4 bytes uint32 (<I)
6. Piggyback Bundle     (Bit 1, 0x0002):  M bytes bundle + 2 bytes signed length (<h)
7. Checksum             (Bit 8, 0x0100):  4 bytes uint32 (<I)

FOOTERS REVERSE UNPACKING ORDER (unpack_footers()):
1. Checksum (Tail - 4B)               <- Pop 4 bytes, verify/clear
2. Piggyback Bundle (Tail - 2B - M)   <- Read length (2B <h), Pop M bytes
3. Indexed Channel ID (Tail - 4B)     <- Pop 4 bytes uint32 (<I)
4. Piggybacked ACKs (Tail - 1B - N*4) <- Read count (1B <B), Pop N*4 bytes
5. Sequence Number (Tail - 4B)        <- Pop 4 bytes uint32 (<I)
6. Bundle Fragments (Tail - 8B)       <- Pop 8 bytes (2x uint32 <I)
7. First Request Offset (Tail - 2B)   <- Pop 2 bytes uint16 (<H)
```

---

## 5. Reliability Window & 28-Bit Sequence Mechanics

Native instructions in `Channel::handlePacket` (`0x10091b6b8`–`0x10091b6c8`) define circular sequence window mechanics:

1. **Modular Sequence Arithmetic:**
   $$\Delta = (\text{incoming\_seq} - \text{expected\_seq}) \pmod{2^{28}}$$
   Evaluated in ARM64 via:
   ```assembly
   sub  w9, w8, w20          ; w9 = incoming_seq - inSeqAt
   and  w9, w9, #0xfffffff   ; 28-bit mask (0x0FFFFFFF)
   ```
2. **Half-Window Comparison:**
   $$\text{Threshold} = 2^{27} = 0x08000000$$
   Evaluated via:
   ```assembly
   movk w10, #0x800, lsl #16 ; w10 = 0x08000000
   cmp  w9, w10
   b.hi #0x10091b704         ; Branch if diff > 0x08000000 (Duplicate / Old packet)
   ```
3. **Sequence Wraparound:**
   When sequence reaches $0x0FFFFFFF$, the next valid sequence is strictly $0x00000000$. The modular difference $(\text{seq} - 0x0FFFFFFF) \pmod{2^{28}}$ yields $1$, seamlessly advancing state without integer overflow.
4. **Piggybacked ACK Queueing:**
   When a sequenced datagram is accepted, instruction `0x10091b788: str w20, [x8], #4` pushes its 32-bit sequence number to `channel->ackQueue_`. Outgoing datagrams pop these sequence numbers and pack them into the ACK footer.

---

## 6. Offline Synthetic Test Plan & Independent Golden Vectors

To ensure that the remediated gateway is verified independently without circular logic, all expected outputs were calculated using raw Python cryptographic primitives and struct packing (documented in [`phase6B_8_4_remediation_plan/synthetic_validation_plan.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_4_remediation_plan/synthetic_validation_plan.md)).

### Independent Golden Vectors Table:
Master Key: `b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"` (56 bytes)

| Vector | Purpose | Corrected Flags | Raw Len | 32-bit XOR Checksum | Padded Len | Trailer | Independent Ciphertext Hex |
|---|---|---|---|---|---|---|---|
| **Vector A** | Login Request (Unit Test 3) | `0x01C0` | 61 B | `0x7b76bada` | 64 B | `0x03` | `b7036a2c2f2da84561b21f7f1c52e9f6...57d9371d16c659e8` |
| **Vector B** | Channel 1 Init Request | `0x03C0` | 65 B | `0x034614e4` | 72 B | `0x07` | `a4888882203c781be215b8e8e5d216a7...c915ca5b5fbc2e38` |
| **Vector C** | Channel 1 App Message | `0x01C8` | 39 B | `0x043f1ec7` | 40 B | `0x01` | `49b5eb66b9bd84a291e6fb8b81d8d485...bdd4a6fa46a65029` |
| **Vector D** | Channel 1 Response + ACK | `0x01CC` | 57 B | `0x71604366` | 64 B | `0x07` | `4a2ecb8a13e4374dfb0d9e35c473f6b4...56cf717fe681381a` |

### Mathematical Proof of Vector A Invariance:
- Prior synthetic flag: `0x0184` $\to$ Checksum was `0x7b76ba9e`.
- Corrected native flag: `0x01C0` $\to$ Difference is `0x01C0 ^ 0x0184 = 0x0044`.
- Checksum linearity: `0x7b76ba9e ^ 0x0044 = 0x7b76bada`.
- The independently calculated checksum matches the theoretical XOR linearity exactly.

---

## 7. Technical Inventory of Unresolved Protocol Questions

As cataloged in [`phase6B_8_4_remediation_plan/unresolved_protocol_questions.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_4_remediation_plan/unresolved_protocol_questions.md), the following protocol layers remain provisional or unknown and are scheduled for future investigation phases:

1. **Dynamic RSA Handshake Envelope (Phase 6.2B.9):**
   - Wire transport: Whether `LoginConnection::sendLogin` opens a TCP stream (`SOCK_STREAM`) to `LoginApp` or transmits raw UDP datagrams.
   - Plaintext structure: Byte alignment of the 56-byte Blowfish key, client nonce, version hash, and username within the RSA-OAEP envelope.
2. **BigWorld Binary RPC Message Schema (Phase 6.2B.10):**
   - The native client transmits binary RPC bundles (entity IDs, method indices, BigWorld binary streams), whereas the current gateway prototype uses UTF-8 JSON payloads.
   - Method dictionary and entity definition files (`.def`) must be extracted or reconstructed to support native in-game RPC dispatch.
3. **Retransmission Timers (RTO) and Congestion Control (Phase 6.2B.11):**
   - Specific native client timer values (initial RTO, min/max RTO, exponential backoff) for packet resends on lossy networks.

---

## 8. Four-Gate Implementation Phasing (Phase 6.2B.8.5 Preview)

When authorized, the remediation will be executed sequentially through 4 gated stages:

```
[ Gate 1: Parser & Flag Enums ]
  - Apply corrected flags and fragment footer to packet_parser.py
  - Update Vector A in tests/test_unit.py
  - Gate Exit: 100% of unit tests pass
         |
         v
[ Gate 2: Sequence & Channel State ]
  - Implement 28-bit modular difference (& 0x0FFFFFFF) in channel_manager.py
  - Implement half-window (0x08000000) duplicate check and isWantingCreateChannel gate
  - Update tests/test_channel_state.py
  - Gate Exit: 100% of channel state tests pass
         |
         v
[ Gate 3: Client & Gateway Dispatch ]
  - Update synthetic_client.py (0x03C0 init, 0x01C8 app)
  - Update gateway.py (0x0200 activation, 0x01CC response)
  - Update tests/test_udp_integration.py
  - Gate Exit: 100% of UDP integration scenarios pass
         |
         v
[ Gate 4: Independent Audit Closure ]
  - Update phase6B_8_1_audit/independent_reconstruction.py
  - Verify complete bit-level agreement between gateway and independent reference
```

---

## 9. Verification & Stop Condition

In strict accordance with the Phase 6.2B.8.4 mandate:
- **NO code modifications were performed on `phase6B_8_local_gateway/`.**
- **NO backend modifications were performed on `ros-private-server/`.**
- **NO sockets were opened, and NO network traffic was sent.**
- **NO database access or migrations were attempted.**
- All 4 required planning artifacts have been authored and verified.
- Execution is halted here. We await formal user review and authorization before proceeding to Phase 6.2B.8.5.
