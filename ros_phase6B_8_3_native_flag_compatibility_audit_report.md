# ROS Sothat — Phase 6.2B.8.3
# Native Mercury Flag Mapping and Gateway Compatibility Audit Report

**Auditor:** Google DeepMind Agentic AI Assistant (Antigravity)  
**Target:** NetEase Rules of Survival (iOS Legacy Client, Mach-O ARM64) & Phase 6.2B.8 Synthetic Gateway  
**Date:** November 13, 2026  
**Audit Classification:** READ-ONLY TECHNICAL AUDIT & INSTRUCTION-LEVEL CLOSURE  
**Primary Deliverables Generated:**
- [`phase6B_8_3_audit/native_mercury_flag_specification.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_3_audit/native_mercury_flag_specification.md)
- [`phase6B_8_3_audit/gateway_compatibility_matrix.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_3_audit/gateway_compatibility_matrix.md)
- [`ros_phase6B_8_3_native_flag_compatibility_audit_report.md`](file:///d:/ROS-Legacy-Analysis/ros_phase6B_8_3_native_flag_compatibility_audit_report.md)

---

## 1. Executive Summary

This phase was executed under strict read-only constraints to independently discover, trace, and formalize the complete native Mercury packet flag specification from the pristine iOS client binary (`extracted/Payload/client.app/client`), and to rigorously audit the existing local synthetic UDP gateway (`phase6B_8_local_gateway/`) against this ground truth.

### Key Audit Breakthroughs:
1. **Complete 16-Bit Flag Space Accounted For:**
   Every bit of the 16-bit Header Flags word was mapped directly from native ARM64 instructions in both receive routines (`Nub::processFilteredPacket`, `Nub::processPacket`, `Channel::handlePacket`) and send/formatting routines (`Packet` construction, `Channel::send`, `Nub::send`).
2. **Resolution of Flag Misallocations:**
   The preliminary hypothesis from Phase 6.2B.8.2 was completely verified and expanded:
   - **Sequence Number:** Strictly **Bit 6 (`0x0040`)**, tested at `0x10092299c: tbz w8, #6`. The synthetic gateway previously misallocated this to Bit 2 (`0x0004`).
   - **Piggybacked ACKs:** Strictly **Bit 2 (`0x0004`)**, tested at `0x100922994: tbnz w8, #2`. The synthetic gateway previously misallocated this to Bit 3 (`0x0008`).
   - **Create Channel:** Strictly **Bit 9 (`0x0200`)**, tested at `0x1009228b8: tbz w8, #9` and `0x100923208: tbnz w8, #9`. The synthetic gateway previously misallocated this to Bit 0 (`0x0001`).
   - **On Channel (Address):** Strictly **Bit 3 (`0x0008`)**, tested at `0x100922984: tbnz w8, #3`. The synthetic gateway previously misallocated this to Bit 5 (`0x0020`).
   - **First Request Offset:** Strictly **Bit 0 (`0x0001`)**, tested at `0x100923908: tbz w8, #0`. The synthetic gateway previously misallocated this to Bit 6 (`0x0040`).
   - **Bundle Fragments:** Strictly **Bit 5 (`0x0020`)**, tested at `0x100923948: tbnz w8, #5`. This footer carries 8 bytes (`fragBegin` 4B + `fragEnd` 4B) and was previously unmapped in the gateway.
   - **Reliability Request:** Strictly **Bit 4 (`0x0010`)**, tested at `0x100922f70: tbnz w8, #4`. Requires an accompanying sequence number (`0x0040`).
   - **Checksum:** Confirmed as **Bit 8 (`0x0100`)**, 100% matching the gateway.
   - **Indexed Channel:** Confirmed as **Bit 7 (`0x0080`)**, 100% matching the gateway.
   - **Piggybacks:** Confirmed as **Bit 1 (`0x0002`)**, 100% matching the gateway.
   - **Reserved Upper Bits:** Bits 10–15 (`0x0400`–`0x8000`) are strictly forbidden, rejected at `0x100922898: cmp w8, #0x400; b.hs`.
3. **Channel Activation Lifecycle Formally Decoded:**
   Disassembly at `0x1009231fc`–`0x100923368` establishes that a new channel is initialized with `isWantingCreateChannel = 1` (`[x22, #0x105]`). The first arriving datagram MUST carry `FLAG_CREATE_CHANNEL` (`0x0200`); receipt of this flag executes `strb wzr, [x22, #0x105]`, activating the channel. Datagrams lacking `0x0200` are dropped with `"Dropping packet on channel wanting FLAG_CREATE_CHANNEL"`.

---

## 2. Overall Audit Verdict

### Final Verdict: **PASS WITH ISSUES**

**Justification:**
- **Passing Research Criteria:** The native Mercury flag enumeration is 100% resolved, supported by instruction-level disassembly, verified control-flow branches, and binary error strings.
- **Identified Issues in Gateway Prototype:**
  - The gateway implementation (`packet_parser.py`) is internally consistent with its synthetic client, but **incompatible with the native ROS client** due to the 5 inverted/misallocated flag bits (`0x0001`, `0x0004`, `0x0008`, `0x0020`, `0x0040`, `0x0200`).
  - Datagrams from the gateway sent to an original physical iOS client will cause the client to parse sequence numbers as ACKs and reject channel creation.
  - Payloads remain synthetic UTF-8 JSON rather than native BigWorld binary RPC bundles.

---

## 3. Complete Native Flag Mapping

```
+===================================================================================================+
|                             NATIVE BIGWORLD MERCURY HEADER FLAGS (16-BIT)                         |
+---------------------------------------------------------------------------------------------------+
| Bit | Hex Mask | Native Constant Name       | Presence  | Footer Format      | Reverse Order Pos  |
+-----+----------+----------------------------+-----------+--------------------+--------------------+
|  0  |  0x0001  | FLAG_HAS_REQUESTS          | Optional  | 2B uint16 (<H)     | 7th (Deepest)      |
|  1  |  0x0002  | FLAG_HAS_PIGGYBACKS        | Optional  | 2B len + M bytes   | 2nd                |
|  2  |  0x0004  | FLAG_HAS_ACKS              | Optional  | 1B cnt + N*4B seqs | 4th                |
|  3  |  0x0008  | FLAG_ON_CHANNEL            | Optional  | None (Addr lookup) | N/A                |
|  4  |  0x0010  | FLAG_IS_RELIABLE           | Optional  | None (State check) | N/A                |
|  5  |  0x0020  | FLAG_HAS_FRAGMENTS         | Optional  | 8B (2x uint32 <I)  | 6th                |
|  6  |  0x0040  | FLAG_HAS_SEQUENCE_NUMBER   | Optional  | 4B uint32 (<I)     | 5th                |
|  7  |  0x0080  | FLAG_INDEXED_CHANNEL       | Optional  | 4B uint32 (<I)     | 3rd                |
|  8  |  0x0100  | FLAG_HAS_CHECKSUM          | Optional  | 4B uint32 (<I)     | 1st (Tail-most)    |
|  9  |  0x0200  | FLAG_CREATE_CHANNEL        | Optional  | None (Activation)  | N/A                |
|10-15| >=0x0400 | RESERVED / ILLEGAL         | FORBIDDEN | N/A                | N/A                |
+===================================================================================================+
```

---

## 4. Instruction Addresses and Control-Flow Branch Analysis

### 4.1 Flags Header Parsing Entry (`Nub::processFilteredPacket`)
```assembly
0x100922890:  mov      x28, x2                    ; x28 = Packet*
0x100922894:  ldrh     w8, [x28, #0x60]!          ; x28 += 0x60 (start of packet payload)
                                                  ; w8 = 16-bit Header Flags word
0x100922898:  cmp      w8, #0x400                 ; Validate flags upper bound (< 0x0400)
0x10092289c:  b.hs     #0x1009228dc               ; If flags >= 0x0400, reject as bad flags!
```

### 4.2 Receive Branch Analysis by Bit
1. **Bit 9 (`0x0200`, `FLAG_CREATE_CHANNEL`):**
   - Check on external nub: `0x1009228b8: tbz w8, #9, #0x100922904`. If set on external nub, logs `"Got FLAG_CREATE_CHANNEL on external nub"` (`0x1030a2db5`).
   - Check on pending channel: `0x100923208: tbnz w8, #9, #0x100923360`. If NOT set on a channel wanting creation (`[x22, #0x105] == 1`), drops packet with `"Dropping packet on channel wanting FLAG_CREATE_CHANNEL"` (`0x1030a31cb`).
   - Activation execution: `0x100923368: strb wzr, [x22, #0x105]` clears pending flag, making the channel active.
2. **Bit 8 (`0x0100`, `FLAG_HAS_CHECKSUM`):**
   - Branch: `0x100922970: tbnz w8, #8, #0x1009229d0`.
   - Execution: At `0x100922a38`, subtracts 4 from remaining length, reads tail checksum into `w11`, zeroes field in-place (`0x100922a54: str wzr, [x10]`), executes 32-bit NEON XOR loop (`0x100922bfc`), restores checksum (`0x100922c44: str w11, [x10]`), and compares `cmp w22, w11`.
3. **Bit 7 (`0x0080`, `FLAG_INDEXED_CHANNEL`):**
   - Branch: `0x100922980: tbnz w8, #7, #0x100922dc0`.
   - Execution: Subtracts 4 from remaining length (`0x100922dd4`), reads 4-byte Channel ID (`0x100922dec: ldr w1, [x11, #0x60]`), and performs channel lookup in `nub->channelsById_` (`0x100922dc0`).
4. **Bit 3 (`0x0008`, `FLAG_ON_CHANNEL`):**
   - Branch: `0x100922984: tbnz w8, #3, #0x100922c88`.
   - Execution: Resolves channel via remote socket IP and port in `nub->channelsByAddress_` (`0x100922c88`–`0x100922d0c`).
5. **Bit 2 (`0x0004`, `FLAG_HAS_ACKS`):**
   - Branch: `0x100922994: tbnz w8, #2, #0x100922e4c`.
   - Execution: Reads 1-byte count (`0x100922efc: ldrb w10, [x10, #0x60]`), asserts count $> 0$, multiplies by 4 (`0x100922f08: lsl w23, w10, #2`), and reads sequence numbers.
6. **Bit 6 (`0x0040`, `FLAG_HAS_SEQUENCE_NUMBER`):**
   - Branch: `0x10092299c: tbz w8, #6, #0x100922f70`.
   - Execution: If set, subtracts 4 from remaining length (`0x100922f50`), reads 4-byte sequence number (`0x100922f68: ldr w9, [x9, #0x60]`), and stores in `packet->seq_num_`.
7. **Bit 4 (`0x0010`, `FLAG_IS_RELIABLE`):**
   - Branch: `0x100922f70: tbnz w8, #4, #0x100923090`.
   - Execution: Asserts packet sequence number is not `0x10000000` (`SEQ_NULL`). If reliable without sequence number, drops packet with `"Dropping packet due to illegal request for reliability without related sequence number"` (`0x1030a3411`).
8. **Bit 0 (`0x0001`, `FLAG_HAS_REQUESTS` in `Nub::processPacket`):**
   - Branch: `0x100923908: tbz w8, #0, #0x100923948`.
   - Execution: Subtracts 2 from remaining length, reads 2-byte uint16 First Request Offset (`0x100923940: ldrh w9, [x9, #0x60]`), stores in `packet->firstRequestOffset_`.
9. **Bit 5 (`0x0020`, `FLAG_HAS_FRAGMENTS` in `Nub::processPacket`):**
   - Branch: `0x100923948: tbnz w8, #5, #0x100923974`.
   - Execution: Subtracts 8 from remaining length, reads 4-byte `fragEnd` and 4-byte `fragBegin` (`0x1009239bc: stp w9, w10, [x22, #0x54]`), and verifies fragment count.

---

## 5. Channel Creation and Activation Behavior

Investigation B addressed all 8 required channel lifecycle questions:

1. **What happens when a create-channel packet is received?**  
   The client verifies that `FLAG_CREATE_CHANNEL` (`0x0200`) is present. At `0x100923368`, the instruction `strb wzr, [x22, #0x105]` clears `channel->isWantingCreateChannel`, immediately transitioning the channel to the `ESTABLISHED` (active) state.
2. **What fields are required to create a channel?**  
   - Header Flags word with Bit 9 (`0x0200`) and Bit 7 (`0x0080` for indexed channel) or Bit 3 (`0x0008` for regular channel).
   - 4-byte uint32 Channel ID footer (`FLAG_INDEXED_CHANNEL`).
   - 4-byte uint32 Checksum footer (`FLAG_HAS_CHECKSUM`).
3. **When is a channel considered active?**  
   A channel is active when `channel->isWantingCreateChannel` is `0` and `channel->isDead` (`[x22, #0xf8]`) is `0`.
4. **Distinguishing new vs. existing channel:**  
   The client maintains an indexed channel map (`nub->channelsById_` at `[x21, #0x4208]`). If the Channel ID exists in the map, the packet is bound to the existing `Channel*`. If it does not exist, the channel finder fails with `"Couldn't get indexed channel for id %d"` (`0x1030a30dd`).
5. **Channel ID width:**  
   Strictly **32-bit uint32 little-endian** (`<I`, 4 bytes), loaded via `0x100922dec: ldr w1, [x11, #0x60]`.
6. **Handling of invalid / duplicate Channel IDs:**  
   - Unregistered ID: Packet discarded with error at `0x1030a30dd`.
   - Channel wanting creation receiving packet without `0x0200`: Packet discarded with error at `0x1030a31cb`.
7. **Packet arriving before channel creation:**  
   Discarded immediately with `REASON_CORRUPTED_PACKET` (`-4`).
8. **Interaction between channel state and encryption:**  
   Decryption operates at the `PacketFilter` layer before channel resolution. However, session keys are bound to channels/endpoints. If `isKeyValid` (`[x0, #0x2c]`) is false, the filter returns `-3` and the datagram never enters the channel state machine.

---

## 6. Sequence Number and ACK Behavior

Investigation C established the native reliability architecture:

1. **Sequence Number Flag:** Bit 6 (`0x0040`).
2. **Sequence Number Width & Format:** 32-bit uint32 little-endian (`<I`, 4 bytes).
3. **Per-Channel Tracking:** Sequence numbers are tracked independently per channel. In `Channel::handlePacket`, `channel->inSeqAt_` is maintained at `[x19, #0xc4]`.
4. **28-Bit Modular Window Mask:**  
   Instruction `0x10091b6b8: and w9, w9, #0xfffffff` masks sequence differences to 28 bits ($2^{28} = 0x10000000$). Sequence numbers wrap at $2^{28}$. The half-window threshold is $2^{27} = 0x08000000$ (`0x10091b6c0: movk w10, #0x800, lsl #16`).
5. **Window Check:** If an incoming sequence number exceeds `inSeqAt` by more than the window threshold, the client logs `"Sequence number #%u is way above window #%u!"` (`0x1030a1e08`).
6. **Piggybacked ACKs (`0x0004`):**  
   In `Channel::queueAckForPacket`, when a sequenced packet is processed, instruction `0x10091b788: str w20, [x8], #4` pushes its sequence number directly into `channel->ackQueue_`. When outgoing packets are constructed, ACKs are popped and written to the packet tail preceded by a 1-byte ACK count.
7. **Duplicates & Out-of-Order:**  
   - Duplicate packets ($seq < inSeqAt$) are acknowledged but not re-dispatched to application handlers.
   - Out-of-order packets ($seq > inSeqAt$) are buffered in the channel packet chain until missing packets arrive.
8. **Gateway Compatibility:** The gateway's discrete integer sequence progression is functionally acceptable for basic single-packet prototype transactions, but must eventually incorporate 28-bit modular difference masking (`seq & 0x0FFFFFFF`) for complete native interoperability.

---

## 7. Piggyback and Fragmentation Behavior

Investigation D decoded bundle fragmentation and multi-message semantics:

1. **Piggyback Flag (`0x0002`):**  
   Unpacks a 2-byte signed length (`<h`) followed by $M$ bytes of bundle data. Used by BigWorld to coalesce control messages or sub-channel updates onto primary transport datagrams.
2. **Fragment Spec Flag (`0x0020`):**  
   When a message bundle exceeds the maximum UDP packet size (typically ~1400 bytes), the sender divides the bundle into fragments and sets Bit 5 (`0x0020`).
   - Footer Width: Exactly **8 bytes**.
   - Structure: `fragBegin` (4 bytes, `<I`) and `fragEnd` (4 bytes, `<I`).
   - Fragment Count: Calculated at `0x1009239c0` as $\text{fragEnd} - \text{fragBegin} + 1$.
   - Validation: If count exceeds limits, logs `"Dropping fragment due to illegal bundle fragment count (%d)"` (`0x1030a3588`).
3. **First Request Offset Flag (`0x0001`):**  
   Contains a 2-byte uint16 offset pointing to the first pending request in the bundle body, allowing request dispatchers to locate request IDs without scanning preceding messages.

---

## 8. Valid and Unknown Flag Combinations

Based on direct inspection of branch conditions and packet formatting routines, the following combinations are evaluated:

| Flag Combination | Hex Value | Native Status | Verified Context / Use Case |
|---|---|---|---|
| **Checksum Only** | `0x0100` | **VALID** | Minimal unsequenced datagram (e.g., stateless ping) |
| **Checksum + Piggybacks** | `0x0102` | **VALID** | Explicitly emitted in client send routine (`0x10092b524`) |
| **Indexed Channel + Checksum** | `0x0180` | **VALID** | Unsequenced message on indexed channel |
| **Create Channel + Indexed + Seq + Checksum**| `0x03C0` | **VALID (CORRECTED)**| Initial channel establishment packet (was `0x0185` in gateway) |
| **On-Channel + Seq + Reliable + Checksum** | `0x0158` | **VALID** | Reliable sequenced packet on regular address channel |
| **Indexed + Seq + Reliable + Checksum** | `0x01D0` | **VALID** | Reliable sequenced application datagram on indexed channel |
| **Indexed + Seq + ACKs + Checksum** | `0x01C4` | **VALID** | Sequenced message piggybacking sequence ACKs |
| **Indexed + Seq + Frag + Checksum** | `0x01E0` | **VALID** | Fragmented multi-packet bundle datagram |
| **Reliable without Sequence Number** | `0x0010` (no `0x0040`)| **FORBIDDEN** | Explicitly dropped at `0x100923098` (`0x1030a3411`) |
| **Any Flag >= 0x0400** | `>= 0x0400` | **FORBIDDEN** | Explicitly rejected at `0x100922898` (`0x1030a2d6c`) |

---

## 9. Gateway Compatibility Matrix

A detailed compatibility breakdown is documented in [`phase6B_8_3_audit/gateway_compatibility_matrix.md`](file:///d:/ROS-Legacy-Analysis/phase6B_8_3_audit/gateway_compatibility_matrix.md).

### Summary Matrix:
- **Low-Level Crypto (Blowfish PBC, Padding, 32-bit XOR Checksum):** **100% MATCH**
- **Flag Bits (0, 2, 3, 5, 6, 9):** **MISMATCH** (Inverted between client and gateway)
- **Flag Bits (1, 7, 8, >=10):** **100% MATCH**
- **Reliability Flag (Bit 4):** **NOT IMPLEMENTED**
- **Fragment Footers (Bit 5):** **NOT IMPLEMENTED**
- **Application Payload Layer:** **SYNTHETIC ONLY** (JSON instead of BigWorld RPC)

---

## 10. Required Future Corrections (Phase 6.2B.8.4 Roadmap)

When authorized, the gateway must be corrected to conform to native ARM64 flags:

1. **`phase6B_8_local_gateway/packet_parser.py`:**
   ```python
   class MercuryPacketFlags:
       FLAG_HAS_REQUESTS        = 0x0001  # Bit 0 (was 0x0040)
       FLAG_HAS_PIGGYBACKS      = 0x0002  # Bit 1 (unchanged)
       FLAG_HAS_ACKS            = 0x0004  # Bit 2 (was 0x0008)
       FLAG_ON_CHANNEL          = 0x0008  # Bit 3 (was 0x0020)
       FLAG_IS_RELIABLE         = 0x0010  # Bit 4 (new)
       FLAG_HAS_FRAGMENTS       = 0x0020  # Bit 5 (was On-Channel)
       FLAG_HAS_SEQUENCE_NUMBER = 0x0040  # Bit 6 (was 0x0004)
       FLAG_INDEXED_CHANNEL     = 0x0080  # Bit 7 (unchanged)
       FLAG_HAS_CHECKSUM        = 0x0100  # Bit 8 (unchanged)
       FLAG_CREATE_CHANNEL      = 0x0200  # Bit 9 (was 0x0001)
   ```
2. **`phase6B_8_local_gateway/synthetic_client.py`:**
   - Update `send_init()` flags: `0x0200 | 0x0080 | 0x0040 | 0x0100 = 0x03C0`.
   - Update `send_message()` flags: `0x0008 | 0x0080 | 0x0040 | 0x0100 = 0x01C8`.
3. **`phase6B_8_local_gateway/channel_manager.py`:**
   - Adopt 28-bit sequence difference masking (`seq & 0x0FFFFFFF`).
4. **Automated Regression Suite (`tests/`):**
   - Update all golden vector flag assertions to reflect corrected values.

---

## 11. Remaining Unknowns

1. **Dynamic RSA Handshake Envelope:**  
   The precise RSA-OAEP envelope layout used by `LoginConnection::sendLogin` to transmit the 56-byte Blowfish key to the server before Mercury encryption activates.
2. **BigWorld Binary RPC Message Schema:**  
   The binary schema of the payload body (Entity IDs, method indices, and variable length BigWorld parameter streams) for authenticating a client session once the Mercury transport channel is established.

---

## 12. Recommendation for the Next Phase

**Recommended Next Step:**
Execute **Phase 6.2B.8.4 — Gateway Flag Alignment & Automated Regression Suite** (Offline, Read-Only / Local Code Update Only).
- Apply corrected native flag constants to `phase6B_8_local_gateway/`.
- Update independent golden reconstruction vectors in `phase6B_8_1_audit/`.
- Execute all 28 automated tests and verify 100% pass rate under native flag masks.
- Keep the gateway isolated to `127.0.0.1` with zero external network activity.

---

## 13. Stop Condition

In accordance with strict safety instructions:
- **No gateway or backend source files were modified.**
- **No database connections were opened or modified.**
- **No network sockets were bound or datagrams transmitted.**
- **The original IPA and Mach-O binary remain pristine and unaltered.**

Antigravity is stopped and awaiting explicit user instruction.
