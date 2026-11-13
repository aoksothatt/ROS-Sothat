# Unresolved Mercury Protocol Questions & Native Unknowns
## Technical Inventory of Layer-2 and Layer-3 Protocol Gaps
**Project:** ROS Sothat — Legacy iOS Client Private Server  
**Phase:** 6.2B.8.4 (Planning Only — Strict Read-Only)  
**Target:** Rules of Survival Legacy iOS Client (ARM64)  
**Status:** EVIDENCE-BASED INVENTORY  

---

## 1. Executive Summary

Phases 6.2B.8.2 and 6.2B.8.3 achieved complete closure on the **Mercury Layer-1 Transport Protocol**:
- Header Flags mapping (all 16 bits accounted for).
- Blowfish Plaintext Block Chaining ($C_i = E(P_i \oplus P_{i-1})$).
- Single-byte trailer wastage padding ($1 \le L \le 8$).
- 32-bit SIMD XOR checksum reduction over `<I` dwords.
- Reverse-order footer parsing from the datagram tail.
- 28-bit circular sequence arithmetic and half-window comparison.

However, full end-to-end communication with an unmodified physical iOS client requires higher-layer protocol mechanics that remain partially unresolved or synthetic. This document establishes a strict, evidence-based technical inventory of all remaining unknown or provisional aspects of the protocol, categorizing them by layer and operational priority.

---

## 2. Inventory of Unresolved Protocol Questions

---

### Category A: Dynamic Cryptographic Handshake & Key Provisioning (Layer 1.5)

#### Question A.1: The RSA Login Handshake Wire Transport
- **Current Gateway Status:** PROVISIONAL / HARDCODED. The prototype uses a static pre-shared master key (`SYNTHETIC_MASTER_KEY` in `config.py`).
- **Native Evidence:** Disassembly identifies `LoginConnection::sendLogin` (`0x1000ab248`) and RSA encryption routines invoking OpenSSL `RSA_public_encrypt` with OAEP padding.
- **The Protocol Gap:**
  - Is the initial RSA handshake transmitted over a dedicated **TCP connection** (e.g., to the `LoginApp` port) or as a raw unencrypted Mercury UDP datagram?
  - In standard BigWorld architecture, the client opens a TCP stream to `LoginApp`, transmits an RSA-encrypted bundle containing credentials and a newly generated 56-byte Blowfish session key, and receives an encrypted session ticket with the UDP endpoint (`BaseApp` IP, Port, and Session Key).
  - *Native Disassembly Requirement:* We must trace the socket creation in `LoginConnection::connect` to determine whether `SOCK_STREAM` (TCP) or `SOCK_DGRAM` (UDP) is opened.

#### Question A.2: RSA Plaintext Payload Structure & Alignment
- **Current Gateway Status:** UNKNOWN.
- **The Protocol Gap:**
  - What is the exact byte-level layout of the RSA plaintext block passed to `RSA_public_encrypt`?
  - Does it contain:
    - 56-byte Blowfish session key?
    - 16-byte nonce / client challenge?
    - Client version string or build hash (e.g., NetEase NeoX engine version)?
    - Account username / token length-prefixed strings?
  - With a 2048-bit RSA key, the maximum OAEP plaintext capacity is $256 - 2 \times 20 - 2 = 214$ bytes. Does the login bundle fit within a single RSA block, or does it use hybrid envelope encryption?

---

### Category B: BigWorld Application RPC Bundle Serialization (Layer 2)

#### Question B.1: Binary RPC Bundle Wire Layout vs. Synthetic JSON
- **Current Gateway Status:** SYNTHETIC ONLY. The prototype sends and receives UTF-8 encoded JSON strings (e.g. `{"action": "INIT_CHANNEL"}`).
- **Native Evidence:** In native BigWorld Mercury, the datagram payload body between Header Flags (Offset 2) and the footers consists of one or more **BigWorld Messages** assembled into a **Bundle**.
- **The Protocol Gap:**
  - A BigWorld Message header typically consists of:
    - `message_id`: 1 byte (0–254) or 2 bytes if extended (`0xFF`).
    - `message_length`: 0 bytes (fixed length defined by protocol interface), 1 byte (variable length $< 256$), 2 bytes (variable length $< 65536$), or 4 bytes.
  - The payload carries entity IDs, method indices, and serialized method parameters using BigWorld binary stream operators (`operator<<` / `operator>>` for integers, floats, vectors, and length-prefixed blobs).
  - We do not currently possess the server-side method dispatch dictionary (`.def` entity definitions) for Rules of Survival Legacy.

#### Question B.2: First Message Request ID & Request Offset Mechanics
- **Current Gateway Status:** PROVISIONAL.
- **Native Evidence:** Disassembly verifies Bit 0 (`0x0001` `FLAG_HAS_REQUESTS`) unpacks a 2-byte uint16 offset into `packet->firstRequestOffset_` at `0x100923940`.
- **The Protocol Gap:**
  - When `firstRequestOffset` points to an offset in the bundle, what is the exact header structure of a Request message?
  - In standard BigWorld, a Request message carries a 4-byte `replyID` and 2-byte `nextRequestOffset` to chain multiple requests within a single bundle.
  - The server response to a request carries a dedicated reply message header matching `replyID`.

---

### Category C: Reliability Window & Packet Resend Mechanics (Layer 2)

#### Question C.1: Retransmission Timer (RTO) and Congestion Control
- **Current Gateway Status:** UNIMPLEMENTED. The prototype is request-response driven on localhost and has no retransmission timers.
- **Native Evidence:** `Channel` contains `resendQueue_` and timer tick routines.
- **The Protocol Gap:**
  - What are the native client's retransmission timeout (RTO) parameters? Initial RTO (e.g., 200ms or 500ms), minimum RTO (e.g., 100ms), maximum RTO (e.g., 5000ms)?
  - Does the native client implement exponential backoff ($RTO \times 2$)?
  - What is the maximum unacknowledged packet window size before transmission stalls?

#### Question C.2: Cumulative vs. Selective Acknowledgments
- **Current Gateway Status:** PROVISIONAL. Gateway uses discrete sequence array piggybacking.
- **Native Evidence:** Bit 2 (`0x0004` `FLAG_HAS_ACKS`) unpacks an array of sequence numbers (`1B count + N*4B seqs`).
- **The Protocol Gap:**
  - Does BigWorld use cumulative ACKs (acknowledging all packets up to sequence $K$) or strictly selective ACKs (acknowledging discrete individual packets)?
  - Disassembly at `0x10091b788` suggests discrete sequences pushed to `ackQueue_`. When an ACK arrives, does it clear that exact sequence from `resendQueue_`, or does `inSeqAt` act as a cumulative lower bound?

---

### Category D: Channel Lifecycle & Session Multiplexing (Layer 2)

#### Question D.1: Channel Index Allocation & Directionality
- **Current Gateway Status:** PROVISIONAL. Hardcoded channel ID `1` used in tests.
- **Native Evidence:** Disassembly verifies Bit 7 (`0x0080` `FLAG_INDEXED_CHANNEL`) uses a 4-byte uint32 Channel ID loaded from tail footer at `0x100922dec`.
- **The Protocol Gap:**
  - Are Channel IDs allocated by the client or assigned by the server during login?
  - Does BigWorld use even/odd Channel IDs to prevent collision between client-initiated and server-initiated indexed channels?
  - Does the game use multiple concurrent indexed channels (e.g., Channel 1 for Entity RPC, Channel 2 for Voice/Chat, Channel 3 for Asset Streaming)?

#### Question D.2: Piggyback Bundle Contents
- **Current Gateway Status:** PROVISIONAL. Gateway unpacks raw byte blob if Bit 1 (`0x0002`) is set.
- **Native Evidence:** Disassembly at `0x10092297c` reads 2-byte signed length `<h` and passes bundle to `Nub::processFilteredPacket`.
- **The Protocol Gap:**
  - Under what exact conditions does the native client attach a piggyback bundle?
  - What constitutes the contents of a piggybacked bundle? Is it sub-channel control messages, cumulative ACKs, or low-priority telemetry?

---

## 3. Risk Assessment & Classification

| Item | Impact on Client Connection | Classification | Remediation Phase |
|---|---|---|---|
| **Header Flag Mappings** | **CRITICAL (100% Drop)** | **RESOLVED** | Phase 6.2B.8.4 Plan / Phase 6.2B.8.5 Fix |
| **Reverse Footer Order** | **CRITICAL (100% Drop)** | **RESOLVED** | Phase 6.2B.8.4 Plan / Phase 6.2B.8.5 Fix |
| **28-bit Sequence Arithmetic** | **CRITICAL (Long-term Desync)** | **RESOLVED** | Phase 6.2B.8.4 Plan / Phase 6.2B.8.5 Fix |
| **Channel Activation Handshake** | **CRITICAL (Handshake Drop)** | **RESOLVED** | Phase 6.2B.8.4 Plan / Phase 6.2B.8.5 Fix |
| **Dynamic RSA Login Handshake** | **CRITICAL (Key Establishment)**| **UNKNOWN (Audit Req)** | Phase 6.2B.9 (Handshake Audit) |
| **BigWorld Binary RPC Bundles** | **CRITICAL (App Data Parse)** | **UNKNOWN (Schema Req)** | Phase 6.2B.10 (RPC Schema Recovery) |
| **RTO & Retransmission Timers** | **MODERATE (Network Resilience)**| **PROVISIONAL** | Phase 6.2B.11 (Transport Hardening) |

---

## 4. Methodological Recommendation

1. **Keep Layer 1 Cleanly Isolated:**
   Remediate the UDP Mercury transport layer (`phase6B_8_local_gateway/`) to achieve 100% native wire conformance on header flags, footers, sequence masking, and channel activation.
2. **Postpone RPC Bundle Emulation:**
   Do NOT attempt to guess or invent BigWorld binary RPC method schemas within the transport gateway. Maintain the clean abstraction where the gateway receives raw datagrams, verifies crypto/framing, and passes unparsed bundle bytes to an upstream application worker.
3. **Target Dynamic RSA Handshake Next:**
   Once the Mercury transport is remediated and validated, the immediate next research priority must be disassembling `LoginConnection::connect` and `LoginConnection::sendLogin` to determine the dynamic session key exchange format.
