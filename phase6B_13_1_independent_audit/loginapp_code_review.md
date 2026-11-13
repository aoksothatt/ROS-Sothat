# Phase 6.2B.13.1 — Code Review Report
## Independent Inspection of Synthetic LoginApp Prototype Implementation

---

### 1. Executive Summary

This code review evaluates the 12 Python source files implemented in `phase6B_13_loginapp_prototype/src/`.

The implementation is evaluated on:
- Code structure, modularity, and adherence to Python best practices.
- Error handling resilience against corrupted, truncated, or malicious inputs.
- Cryptographic correctness against native client ARM64 disassembly.
- Identification of discrepancies between implementation and native evidence.

**Key Finding:** The codebase is well-structured, clean, thoroughly type-annotated, and resilient against malformed inputs. However, an important cryptographic discrepancy was detected: `blowfish_filter.py` implements **Blowfish ECB**, whereas native ARM64 disassembly proves that the client uses **Blowfish CBC mode with IV = 0**.

---

### 2. Module-by-Module Code Review

#### 2.1 `mercury_parser.py` (Mercury Transport Framing)
- **Role:** Handles 2-byte header flags, footer unpacking, and reverse footer calculations.
- **Code Quality:** Excellent. Clean dataclass `MercuryFrame`, typed constants for all native flags.
- **Header Parsing:** Correctly parses 2-byte uint16 LE flags.
- **Footer Parsing:** Unpacks footers from datagram tail forward:
  - Sequence number: Correctly shifts right by 4 bits to extract 28-bit sequence integer and lower 4 bits for sub-packet index.
  - Request count: Extracts 1 byte when `FLAG_HAS_REQUESTS` is set.
  - ACKs: Correctly extracts count and 4-byte sequence integers when `FLAG_HAS_ACKS` is set.
- **Resilience:** Throws `MercuryFramingError` on truncated footers or header overlap.

#### 2.2 `bundle_parser.py` (BigWorld Bundle Demuxer & String Codec)
- **Role:** Demuxes BigWorld RPC bundles, extracts message ID `0x00`, length, and 4-byte Request ID.
- **String Encoding (`encode_bw_string` / `decode_bw_string`):**
  - Fully compliant with native disassembly: $< 255$ encoded as 1-byte length; $\ge 255$ encoded as `0xFF` + 3-byte uint24 LE length.
- **Bundle Parsing:** Correctly verifies declared length against physical byte buffer size. Enforces message ID `0x00`.
- **Resilience:** Gracefully catches truncated streams and length mismatches via `BundleParsingError`.

#### 2.3 `crypto.py` (RSA-OAEP Asymmetric Decryption)
- **Role:** Asymmetric decryption of `LogOnParams` envelope.
- **Implementation:** Wraps `cryptography.hazmat.primitives.asymmetric.padding.OAEP` with `MGF1(hashes.SHA1())` and `hashes.SHA1()`.
- **Native Alignment:** Exactly matches native OpenSSL configuration (`RSA_PKCS1_OAEP_PADDING = 4`, 42-byte overhead at VA `0x100927c70`).
- **Resilience:** Catches all cryptography exceptions and wraps them in `RsaDecryptionError`, preventing server crashes on invalid ciphertexts.

#### 2.4 `logon_params.py` (LogOnParams Codec & Salt Reversal)
- **Role:** Serializes and deserializes the 6 plaintext fields of `LogOnParams`.
- **Field Order:** Exactly matches native `addToStream` (LogOnType, Username, Password, SessionKey, ClientNonce, ClientFlags).
- **Password Salt:**
  - Client transformation: Prefixes `aec05336` and decrements each character by 1 (`c_i - 1`).
  - Server reversal: Verifies `aec05336` prefix and increments each character by 1 (`c_i + 1`).
  - Matches native disassembly at VA `0x1008776bc`–`0x100877878`.
- **Validation Constraints:** Strictly enforces `len(session_key) == 56` and `len(client_nonce) == 16`.

#### 2.5 `auth.py` (Synthetic Account Repository)
- **Role:** In-memory user store for offline test execution.
- **Status Codes:** Defines `LoginStatus` enum (`0x01`–`0x07`).
- **Native Alignment Nuance:** Native disassembly confirms that `0x01` is `LOGON_STATUS_SUCCESS`. Non-1 statuses (`0x02`–`0x07`) are synthetic application conventions; native client treats ANY status $\neq 1$ as failure and displays the server's BigWorld error string.
- **Security:** Passwords are hashed using salted SHA-256 in memory; no real credentials stored.

#### 2.6 `session_manager.py` (Session Store & Replay Defense)
- **Role:** Manages active session tickets, rate limits, and nonce deduplication.
- **Replay Protection:** Maintains `_seen_nonces` dictionary with automatic timestamp pruning.
- **Rate Limiting:** Sliding 60-second window tracking requests per client IP.
- **Memory Safety:** Automatically prunes expired sessions based on configured TTL (default 60s).

#### 2.7 `address.py` (Mercury Address Struct)
- **Role:** Encodes 20-byte and 24-byte `Mercury::Address` binary structs.
- **Byte Order:** Correctly utilizes network byte order (Big-Endian) for IPv4 address (`inet_aton`) and port (`!H`).
- **Padding:** Provides 14 bytes internal struct padding and 4 bytes zero-padding to reach 24 bytes (multiple of 8 for Blowfish).

#### 2.8 `blowfish_filter.py` (Address Block Cipher) — **DEFECT IDENTIFIED**
- **Role:** Encrypts and decrypts the 24-byte BaseApp address block for `LoginReply`.
- **Code Inspection:**
  ```python
  cipher = Cipher(algorithms.Blowfish(session_key), modes.ECB())
  ```
- **Discrepancy:** Uses `modes.ECB()`.
- **Native Disassembly Reality:** Static disassembly of `EncryptionFilter::decrypt` at VA `0x10091cb54`–`0x10091cb80` explicitly proves that the native client uses **Blowfish CBC mode with zero IV**:
  ```arm64
  0x10091cb68: bl  #0x1000ab248         ; BF_ecb_encrypt(in, out, key, BF_DECRYPT)
  0x10091cb6c: cbz x25, #0x10091cb44   ; If block 0, skip XOR (IV = 0)
  0x10091cb70: ldr x8, [x25]           ; Previous ciphertext block
  0x10091cb74: ldr x9, [x22, x24]      ; Decrypted block
  0x10091cb78: eor x8, x9, x8          ; XOR with previous ciphertext (CBC un-chaining!)
  ```
- **Impact:** For Block 0 (bytes 0–7), ECB and CBC(IV=0) are identical. However, for Blocks 1 and 2 (bytes 8–23), ECB does not XOR with the previous ciphertext block. The real client will decrypt garbage for bytes 8–23 if the server uses ECB.
- **Classification:** **INCORRECT** — Must be updated to Blowfish CBC mode with zero IV in Phase 6.2B.14.

#### 2.9 `login_reply.py` (LoginReply Datagram Builder)
- **Role:** Packs success and failure response packets.
- **Structure:** BigWorld MsgID `0xFF`, 2-byte length, 4-byte Request ID, 1-byte status, and payload.
- **Success Payload:** Encrypted 24-byte address block + optional `0x32ef9816` cookie and 56-byte key.
- **Failure Payload:** Status byte + BigWorld error string.
- **Mercury Framing:** Attaches sequence number footer and ACK sequence if provided.

#### 2.10 `audit_logger.py` (Security Logger)
- **Role:** Structured JSON operational event logging.
- **Sanitization:** Programmatically filters out `password`, `plain_password`, `private_key`, and `session_key`. Verified zero leak in `TC-16`.

#### 2.11 `loginapp_core.py` (Central Service Orchestrator)
- **Role:** Ties all components together into `handle_datagram(data, client_ip)`.
- **Pipeline:** Rate check $\rightarrow$ Mercury unpack $\rightarrow$ Bundle unpack $\rightarrow$ Version check (43) $\rightarrow$ RSA decrypt $\rightarrow$ LogOnParams unpack $\rightarrow$ Replay check $\rightarrow$ Auth check $\rightarrow$ Session creation $\rightarrow$ Address encrypt $\rightarrow$ Reply build.
- **Execution Scope:** Purely in-memory method. Zero network sockets opened.

#### 2.12 `synthetic_client.py` (Test Harness Helper)
- **Role:** Generates synthetic client requests and verifies replies.
- **Circularity Note:** Directly imports and reuses `MercuryParser`, `BundleParser`, and `BlowfishAddressFilter` from `src/`, introducing self-consistent testing circularity.

---

### 3. Summary of Code Review Findings

| Module | Architectural Compliance | Security & Error Handling | Native Evidence Match | Notes |
| :--- | :---: | :---: | :---: | :--- |
| `mercury_parser.py` | High | High | **VERIFIED** | Correct 28-bit sequence and footer logic. |
| `bundle_parser.py` | High | High | **VERIFIED** | Correct MsgID 0x00 and string encoding. |
| `crypto.py` | High | High | **VERIFIED** | Correct OAEP SHA-1 parameters. |
| `logon_params.py` | High | High | **VERIFIED** | Correct field order and `aec05336` salt reversal. |
| `auth.py` | High | High | **SYNTHETIC ONLY** | Status codes 0x02–0x07 are synthetic conventions. |
| `session_manager.py` | High | High | **SYNTHETIC ONLY** | Nonce replay defense works well; synthetic TTL. |
| `address.py` | High | High | **VERIFIED** | Correct 20B/24B struct and Big-Endian packing. |
| `blowfish_filter.py` | Moderate | High | **INCORRECT** | Uses ECB mode; native client uses CBC (IV=0). |
| `login_reply.py` | High | High | **VERIFIED** | Correct reply framing and cookie support. |
| `audit_logger.py` | High | High | **VERIFIED** | Zero credential exposure verified. |
| `loginapp_core.py` | High | High | **SYNTHETIC ONLY** | In-memory protocol simulator (no UDP socket). |
| `synthetic_client.py`| High | High | **CIRCULAR** | Reuses server modules; masks cipher mode defect. |
