# Protocol Assumptions and Ground Truth Mapping
## ROS Sothat — Phase 6.2B.13 Synthetic LoginApp Implementation

---

### 1. Architectural Purpose

This document details the exact protocol specifications, evidence mappings, and explicit assumptions utilized in the isolated synthetic `LoginApp` prototype (`phase6B_13_loginapp_prototype/`).

All protocol fields are categorized strictly into:
- **Directly Verified Ground Truth:** Backed by static ARM64 disassembly instructions, symbol registrations, or binary analysis.
- **Static Inferences:** Derived from BigWorld / Mercury architecture consistent with native disassembly.
- **Explicit Assumptions & Isolations:** Design choices isolated behind modular interfaces where binary evidence leaves ambiguity.

---

### 2. Verified Ground Truth Protocol Fields

| Protocol Element | Wire Specification | Byte Order / Type | Evidence Source (VA / File) | Confidence |
| :--- | :--- | :--- | :--- | :---: |
| **Mercury Transport Flags** | Initial login request uses `0x0041` (`HAS_REQUESTS \| HAS_SEQUENCE_NUMBER`). | 2 bytes uint16 LE | Phase 6.2B.8.5 audit & Mercury spec | **100%** |
| **Mercury Sequence Number** | 28-bit sequence number stored in footer before 4-bit sub-packet index. | 4 bytes uint32 LE | Native footer unpacking (`0x100918000`) | **100%** |
| **Interface Name** | `"LoginInterface"` | ASCII string | Client VA `0x10309d15e` | **100%** |
| **Method Name** | `"login"` | ASCII string | Client VA `0x1030453ed` | **100%** |
| **Message ID** | `0x00` | 1 byte uint8 | Registration at VA `0x1008cde44` | **100%** |
| **Message Length Header** | 2-byte variable length (`VAR(2B)`) | 2 bytes uint16 LE | Registration at VA `0x1008cde4c` (`w3 = 2`) | **100%** |
| **Request ID** | 4-byte correlation ID issued by `Bundle::startRequest` | 4 bytes uint32 LE | Client VA `0x100917c24` | **100%** |
| **`LOGIN_VERSION`** | Hardcoded integer `43` (`0x0000002b`) | 4 bytes uint32 LE | Disassembly at VA `0x1008a8290` (`mov w8, #0x2b`) | **100%** |
| **Asymmetric Cipher** | RSA with PKCS#1 v2.1 OAEP padding | OpenSSL padding ID 4 | Disassembly at VA `0x100927cc8` (`mov w4, #4`) | **100%** |
| **OAEP Hash Function** | SHA-1 ($2 \times 20 + 2 = 42$ bytes overhead) | Modulus - 42 bytes | Disassembly at VA `0x100927c70` (`sub w27, w23, #0x2a`) | **100%** |
| **`LogOnParams` Serialization Order** | 1. `LogOnType` (1B uint8 = `0x01`)<br>2. `Username` (BW string)<br>3. `Password` (BW string)<br>4. `SessionKey` (BW string: `0x38` + 56B)<br>5. `ClientNonce` (16B SIMD block)<br>6. `ClientFlags` (4B uint32 LE) | Sequential in memory stream | Disassembly of `LogOnParams::addToStream` at VA `0x1008992fc`–`0x100899590` | **100%** |
| **BigWorld String Encoding** | If $L < 255$: 1B length.<br>If $L \ge 255$: `0xFF` + 3B uint24 LE length. | BigWorld compact encoding | Disassembly at VA `0x1008993e4`–`0x100899404` | **100%** |
| **Password Preprocessing** | Hardcoded salt `aec05336` prefix + byte-by-byte decrement: $c_i - 1$. | ASCII string transformation | Disassembly at VA `0x1008776bc`–`0x100877878` | **100%** |
| **Session Key Length** | Exactly 56 bytes (448-bit Blowfish key) | 56 raw bytes | Disassembly at VA `0x1008994e8` & `0x1008aa064` | **100%** |
| **Login Reply Status: Success** | `0x01` (`LOGON_STATUS_SUCCESS`) | 1 byte uint8 | Disassembly at VA `0x1008a844c` (`cmp w8, #1`) | **100%** |
| **Login Reply Status: Failure** | Status $\neq 1$ followed by BigWorld error message string | 1 byte uint8 + BW string | Disassembly at VA `0x1008a84e8`–`0x1008a8540` | **100%** |
| **BaseApp Address Block** | 20-byte `Mercury::Address` (4B IPv4, 2B port, 14B padding) padded to 24B (8B block multiple) | Decrypted with 56B Blowfish key | Disassembly at VA `0x1008a85f0` & `0x10091caf4` | **100%** |
| **Session Key Replacement Cookie** | Magic cookie `0x32ef9816` | 4 bytes uint32 LE | Disassembly at VA `0x1008a8654` | **100%** |

---

### 3. Static Inferences & Architectural Decisions

1. **Reply Message ID Framing:**
   - In BigWorld Mercury bundle protocol, RPC responses are dispatched to the callback handler bound to the matching 4-byte `Request ID`.
   - On the wire, Mercury bundle headers represent reply messages with message ID `0xFF` (standard BigWorld `REPLY_MESSAGE_IDENTIFIER`), followed by the 4-byte `Request ID`.
   - *Implementation:* The prototype supports standard `0xFF` reply framing with correlation to the client's `Request ID`.

2. **Blowfish Address Decryption Mode:**
   - The native client decrypts the reply address block using `EncryptionFilter::decrypt` (VA `0x10091ca8c`).
   - The function strictly asserts that the payload length is a multiple of the 8-byte Blowfish block size (`tst w19, #7` at `0x10091caf4`).
   - The 20-byte `Mercury::Address` is zero-padded to 24 bytes (3 Blowfish blocks).
   - *Implementation:* Blowfish encryption is implemented in standard Electronic Codebook (ECB) or Cipher Block Chaining (CBC) with zero IV for the single 3-block address payload.

3. **Session Handoff Lifetime:**
   - Because `LoginApp` only authenticates and hands off to `BaseApp`, login session records in memory are short-lived.
   - *Implementation:* Sessions are given a 60-second TTL in the in-memory session store.

---

### 4. Explicitly Isolated / Unverified Boundaries

1. **In-Match Simulation:**
   - This phase covers ONLY the `LoginApp` authentication pipeline.
   - The prototype does **not** simulate CellApp physics, player movement, hit registration, weapons, or matches.
2. **Production Secrets:**
   - Production NetEase keys are nonexistent.
   - All tests run against locally generated synthetic RSA-2048 keys.
