# Private LoginApp Architectural Requirements
## Service Specifications for ROS Sothat Private Server Emulation

---

### 1. Purpose and Role

In the Rules of Survival Legacy server architecture, `LoginApp` serves as the initial authentication gateway and traffic director. Its core responsibilities are:
1. Terminating the initial client Mercury UDP connection.
2. Ingesting, decrypting, and authenticating user credentials transmitted via `LogOnParams`.
3. Selecting an active, appropriate `BaseApp` game server node.
4. Returning a securely encrypted session referral (`LoginReply`) containing the `BaseApp` address to the client.

This document specifies the exact technical requirements for implementing a private `LoginApp` service compatible with the original ROS Legacy iOS client.

---

### 2. Service Architecture & Component Boundaries

```mermaid
graph TD
    Client["Original ROS Legacy iOS Client"] <-->|Mercury UDP (Port 20013)| LoginGateway["Private LoginApp Gateway"]
    LoginGateway <-->|Internal REST / gRPC| Backend["FastAPI Backend (ros-private-server)"]
    Backend <-->|SQLAlchemy| DB[("PostgreSQL Database")]
    LoginGateway -->|Directs Client To| BaseApp["Private BaseApp (Game Server)"]
```

---

### 3. Functional Requirements

#### 3.1 Network Transport Ingestion
- **Protocol:** UDP over IPv4 (optional dual-stack IPv6).
- **Default Port:** Configurable (standard BigWorld default: `20013` or `20014`).
- **Mercury Framing Compliance:** Must fully parse and generate packets conforming to the native Mercury protocol verified in Phase 6.2B.8.5:
  - 2-byte header flags (`HAS_REQUESTS = 0x0001`, `IS_RELIABLE = 0x0010`, `HAS_SEQUENCE_NUMBER = 0x0040`, `CREATE_CHANNEL = 0x0200`).
  - 28-bit sequence number wrapping (`seq & 0x0FFFFFFF`).
  - Packet footer layout: `requestID`, `seq`, `ack`, piggybacks.

#### 3.2 Inbound `login` Request Processing
Upon receiving a datagram on the listening socket:
1. **Header Validation:** Confirm header flags and extract the packet payload.
2. **RPC Header Unpacking:**
   - Verify Message ID equals `0x00` (`LoginInterface::login`).
   - Read 2-byte little-endian message length.
   - Read 4-byte little-endian `requestID` (required to correlate the reply).
3. **Protocol Version Verification:**
   - Read 4-byte `uint32_t` integer immediately following `requestID`.
   - Must equal `0x0000002b` (decimal 43, `LOGIN_VERSION`).
   - If mismatch, discard packet and log version error.
4. **`LogOnParams` Ingestion & Decryption:**
   - Check whether payload is encrypted (RSA-OAEP) or plaintext.
   - If RSA-OAEP: Decrypt using server private key (OAEP padding, SHA-1 digest).
   - If plaintext (unencrypted mode): Proceed directly to stream parsing.
5. **Field Deserialization:**
   - **`LogOnType` (1 byte):** Must be `0x01`.
   - **`Username` (BigWorld String):** Parse 1B or 4B length prefix, extract ASCII account identifier.
   - **`Password` / Token (BigWorld String):** Parse length prefix, extract session token.
   - **`SessionKey` (BigWorld String):** Verify length byte equals `0x38` (56 decimal); extract 56-byte Blowfish session key.
   - **`ClientNonce` (16 bytes):** Extract 128-bit random nonce for replay defense.
   - **`ClientFlags` (4 bytes `uint32_t`):** Extract client build/features bitmask.

#### 3.3 Backend Authentication Integration
- The private `LoginApp` transmits the extracted username and password/token to the existing ROS Sothat FastAPI backend (`ros-private-server/`):
  - Inbound route: `POST /api/v1/auth/verify-token` or internal auth service.
  - Verifies user exists, account is not banned, and credentials match database records.
- If authentication fails:
  - Return `LogOnStatus` error code (e.g., `LOGON_STATUS_INVALID_PASSWORD = 2` or `LOGON_STATUS_ACCOUNT_BLOCKED = 3`).
  - Attach descriptive error string to reply.
- If authentication succeeds:
  - Return `LogOnStatus = 1` (`LOGON_STATUS_SUCCESS`).
  - Allocate an active `BaseApp` worker instance.

#### 3.4 Outbound `LoginReply` Construction
When authentication succeeds, the private `LoginApp` must format the reply as follows:
1. **Reply Datagram Header:**
   - Set Mercury header flags (`IS_RELIABLE = 0x0010`, `HAS_ACKS = 0x0004`, `HAS_SEQUENCE_NUMBER = 0x0040`).
   - Set reply correlation referencing incoming `requestID`.
2. **Reply Payload:**
   - **Byte 0:** `LogOnStatus = 0x01` (`uint8_t`).
   - **Encrypted Payload (Blowfish PBC):**
     - Symmetrically encrypted using the client's 56-byte Blowfish key.
     - Must be padded to a multiple of 8 bytes (Blowfish block size).
     - Payload content:
       - **Bytes 0–19 (20 bytes):** `Mercury::Address` of `BaseApp`:
         - `ip`: 4 bytes `uint32_t` network byte order (or native integer).
         - `port`: 2 bytes `uint16_t` network byte order.
         - Remaining 14 bytes: zero-padded `sockaddr_in` / `sockaddr_in6` buffer.
       - **Optional Extension (Key Rotation):**
         - If server desires to re-key: append `0x32ef9816` magic followed by BigWorld string containing new 56-byte Blowfish key.
         - If keeping client's key: omit extension (leave total length at 20 bytes $\to$ padded to 24 bytes).

---

### 4. Resolving the NetEase RSA Key Barrier

Under the strict project constraint that the original iOS IPA cannot be modified:

#### 4.1 Root Analysis
The original Mach-O binary contains hardcoded logic at `0x1008abfb4` seeking the public key at `"entities\\loginapp.pubkey"`. NetEase's private key is unknown.

#### 4.2 Solution Architectures for ROS Sothat
1. **Launcher Virtual File System (VFS) Redirection:**
   - The ROS Sothat launcher (PC/iOS wrapper) intercepts client file system access.
   - When the client requests `"entities\\loginapp.pubkey"`, the launcher presents the private server's RSA public key.
   - The client then encrypts `LogOnParams` with the private server's key, allowing the private `LoginApp` to cleanly decrypt the payload.
   - **IPA Status:** Completely unmodified on disk.

2. **Launcher In-Memory Hook:**
   - When launching the original game, the launcher hooks `PublicKeyCipher::setKey` (VA `0x100927a20`) in RAM and injects the private server's public key.
   - **IPA Status:** Completely unmodified on disk.

3. **Fallback Unencrypted Mode:**
   - Disassembly at `0x10089936c` proves that when `pCipher == NULL`, the client transmits `LogOnParams` in plaintext.
   - If the launcher causes `ServerConnection::setKeyFromResource` to return NULL gracefully without triggering `PUBLIC_KEY_LOOKUP_FAILED`, the client sends cleartext credentials.

---

### 5. Architectural Checklist for Implementation

| Subsystem | Requirement | Priority | Target Phase |
| :--- | :--- | :---: | :---: |
| **Mercury Transport** | Complete 28-bit sequence and footer processing | High | Completed (Phase 6B.8.5) |
| **Bundle Demuxer** | Extract Message ID, 2-byte variable length, request ID | High | Phase 6.2B.10 |
| **RSA Ingestion** | Support RSA-OAEP SHA-1 decryption with server private key | High | Phase 6.2B.10 |
| **Blowfish PBC** | Support 56-byte Blowfish encryption of `LoginReply` payload | High | Phase 6.2B.10 |
| **DB Integration** | Authenticate credentials against `ros-private-server` PostgreSQL | Medium | Phase 6.2B.10 |
| **BaseApp Dispatch** | Generate 20-byte `Mercury::Address` for BaseApp referral | High | Phase 6.2B.10 |
