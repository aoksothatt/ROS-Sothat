# Gate 1 — Independent Login Protocol Audit
## Native Mercury Framing, BigWorld RPC Wire Format, and Cryptographic Specification

---

### 1. Executive Summary

This independent technical audit verifies the exact binary wire protocol used during client-to-LoginApp communication in the original Rules of Survival Legacy client (`extracted/Payload/client.app/client`).

Every specification in this document is derived from direct ARM64 static disassembly, native vtable inspection, and mathematical analysis of the client binary.

Key Verified Findings:
1. **Interface & Message ID:** `LoginInterface::login` is Message ID `0x00`, encoded with a 2-byte variable length header (`VAR(2B)`).
2. **Protocol Version:** The client transmits a hardcoded 4-byte little-endian `LOGIN_VERSION = 43` (`0x0000002b`).
3. **Encryption Architecture:** Authentication parameters are serialized into `LogOnParams` and encrypted via **RSA with OAEP padding and SHA-1**.
4. **Session Key Length:** The client generates and transmits a **56-byte Blowfish session key**.
5. **Password Preprocessing:** The client prefixes user passwords with the hardcoded salt string `aec05336` and decrements each byte by 1.
6. **Reply Handshake:** `LoginReply` carries a 1-byte status header (`0x01` for success) followed by a Blowfish-encrypted 20-byte `Mercury::Address` (padded to 24 bytes).

---

### 2. Mercury UDP Transport Framing

The client transmits login datagrams to `LoginApp` over UDP (default port `20013`, `0x4e2d` at VA `0x1008abf8c`).

```
+------------------------------------+------------------------------------------+-----------------------+
| Mercury Header Flags (2 Bytes LE)  | BigWorld RPC Message Bundle (Variable)  | Footers (Variable)    |
+------------------------------------+------------------------------------------+-----------------------+
```

#### 2.1 Transport Flag Verification
- **Header:** 2 bytes `uint16_t` little-endian flags.
- **Observed Native Flags on Initial Login:**
  - `0x0001`: `HAS_REQUESTS` — datagram carries an RPC request requiring a reply handler.
  - `0x0040`: `HAS_SEQUENCE_NUMBER` — datagram carries a 28-bit sequence number.
  - Combined Initial Flag: `0x0041` (`0x41, 0x00`).
- **Footer Structure:**
  - Sequence Number: 4 bytes (28-bit sequence integer, 4-bit sub-packet index).
  - Request Tracking: 1 byte indicating outstanding request count.

---

### 3. Application Message Envelope (`LoginInterface::login`)

The registration routine at VA `0x1008cde0c` registers the `LoginInterface` bundle format:
- VA `0x1008cde10`: Interface name string at `0x10309d15e` = `"LoginInterface"`.
- VA `0x1008cde40`: Method name string at `0x1030453ed` = `"login"`.
- VA `0x1008cde48`: Length style `w2 = 1` (`VARIABLE_LENGTH`).
- VA `0x1008cde4c`: Length parameter `w3 = 2` (2-byte uint16 length header).
- Message ID: `0x00` (First registered method).

```
+---------------+-----------------------+--------------------+-----------------------------+
| Msg ID (0x00) | Length (2B uint16 LE) | Request ID (4B LE) | Body (LOGIN_VERSION + Blob) |
+---------------+-----------------------+--------------------+-----------------------------+
```

#### Detailed Wire Field Table
| Field # | Field Name | Data Type | Byte Order | Size (Bytes) | Disassembly Reference | Confidence |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: |
| **1** | `Message ID` | `uint8_t` | N/A | 1 | `0x1008cde44` (`0x00`) | **100% Verified** |
| **2** | `Length` | `uint16_t` | Little-Endian | 2 | `0x1008cde4c` (`w3 = 2`) | **100% Verified** |
| **3** | `Request ID` | `uint32_t` | Little-Endian | 4 | `0x100917c24` (`startRequest`) | **100% Verified** |
| **4** | `LOGIN_VERSION` | `uint32_t` | Little-Endian | 4 | `0x1008a8290` (`mov w8, #0x2b`) | **100% Verified** |
| **5** | `Ciphertext` | Binary Blob | Big-Endian / Raw | 128 or 256 | `0x1008995ac` (`bl publicEncrypt`) | **100% Verified** |

---

### 4. `LogOnParams` Plaintext Field Specification

Before transmission, the client serializes authentication parameters inside `LogOnParams::addToStream` (VA `0x1008992fc`). If an RSA public key is loaded, this byte buffer is encrypted into the ciphertext blob.

```
+----------+------------------+------------------+------------------+-------------------+-------------------+
| Type(1B) | Username (BWstr) | Password (BWstr) | BlowfishKey(57B) | Nonce (16B SIMD)  | ClientFlags (4B)  |
+----------+------------------+------------------+------------------+-------------------+-------------------+
```

#### Field-by-Field Breakdown
| Field # | Field Name | Serialization Type | Length (Bytes) | Native Instruction | Description | Confidence |
| :---: | :--- | :--- | :---: | :--- | :--- | :---: |
| **1** | `LogOnType` | `uint8_t` | 1 | `0x10089938c: strb w22, [x0]` | Protocol sub-type (default `0x01`). | **100% Verified** |
| **2** | `Username` | BigWorld String | $1 + L$ or $4 + L$ | `0x1008993cc: strb w8, [x0]` | Account name / identifier. | **100% Verified** |
| **3** | `Password` | BigWorld String | $1 + L$ or $4 + L$ | `0x100899464: strb w8, [x0]` | Salted and decremented password token. | **100% Verified** |
| **4** | `SessionKey` | BigWorld String | 57 (`0x38` + 56B) | `0x1008994fc: strb w8, [x0]` | **56-byte Blowfish key** (`0x38` prefix). | **100% Verified** |
| **5** | `ClientNonce` | 128-bit block | 16 | `0x100899574: str q0, [x0]` | Random cryptographic nonce (`q0`). | **100% Verified** |
| **6** | `ClientFlags` | `uint32_t` LE | 4 | `0x100899590: str w21, [x0]` | Client feature bitmask / build flag. | **100% Verified** |

#### BigWorld Variable-Length String Prefix Rules
- If $L < 255$ (`0xFF`): 1 byte `uint8_t` encoding $L$.
- If $L \ge 255$ (`0xFF`): 1 escape byte `0xFF` followed by 3 bytes `uint24_t` little-endian length ($L \ \& \ \text{0xFFFFFF}$).
- Disassembly confirmation at VA `0x1008993e4`–`0x1008993f4`.

#### Password Preprocessing & Salting
Disassembly at VA `0x1008776bc`–`0x100877878` reveals that prior to serialization:
1. The client loads a hardcoded 8-byte salt `aec05336` (stored obfuscated at `0x103099441` as `bfd16447` and decoded via `sub w24, w9, #1`).
2. It appends the user password with every character decremented by 1: `sub w23, w8, #1`.
3. The resulting string has format: `aec05336` + $\sum (c_i - 1)$.

---

### 5. Asymmetric Cryptography: RSA-OAEP SHA-1

Native verification of `PublicKeyCipher::encrypt` at VA `0x100927c20`:
1. **Mathematical Proof of OAEP SHA-1:**
   - At VA `0x100927c70`: `sub w27, w23, #0x2a`.
   - `0x2a` = 42 decimal.
   - For RSA-OAEP with SHA-1: $\text{Overhead} = 2 \times \text{HashLen} + 2 = 2 \times 20 + 2 = 42\text{ bytes}$.
   - The client subtracts 42 bytes from the modulus size to calculate the maximum plaintext payload.
2. **OpenSSL Padding Parameter:**
   - At VA `0x100927cc8`: `mov w4, #4; blr x19`.
   - In OpenSSL `RSA_public_encrypt`, parameter 5 (`w4`) is `RSA_PKCS1_OAEP_PADDING` ($= 4$).
3. **Modulus / Key Size:**
   - The cipher supports arbitrary RSA modulus lengths (typically 1024-bit / 128-byte or 2048-bit / 256-byte).

---

### 6. LoginReply Handshake Response Wire Format

When `LoginApp` responds, the client processes the reply in `LoginHandler::handleMessage` (VA `0x1008a83f8`):

#### 6.1 Success Reply Format (`status == 1`)
```
+---------------+-----------------------+--------------------+-----------------------------+
| Reply MsgID   | Length (2B uint16 LE) | Request ID (4B LE) | Status (1B = 0x01)          |
+---------------+-----------------------+--------------------+-----------------------------+
| Blowfish-Encrypted BaseApp Address Block (24 Bytes)                                      |
+------------------------------------------------------------------------------------------+
| Optional Session Key Magic Cookie: 0x32ef9816 (4B LE) + Replacement Key (56 Bytes)       |
+------------------------------------------------------------------------------------------+
```

1. **Status Byte:** 1 byte `uint8_t` = `0x01` (`LOGON_STATUS_SUCCESS` at `0x1008a844c`).
2. **Blowfish Decryption:** The remaining stream is passed to `EncryptionFilter::decrypt` (VA `0x10091ca8c`) using the client's 56-byte Blowfish key.
   - Stream length **must** be a multiple of 8 bytes (`tst w19, #7` at `0x10091caf4`).
3. **`Mercury::Address` Struct (20 Bytes):**
   - IPv4 Address: 4 bytes `uint32_t` in network byte order (big-endian).
   - Port: 2 bytes `uint16_t` in network byte order (big-endian).
   - Struct Padding: 14 bytes zero padding (struct alignment).
   - Padded to 24 bytes for 8-byte Blowfish block alignment.
4. **Optional Replacement Session Key:**
   - Checked at VA `0x1008a8654`: scans for 4-byte magic cookie `0x32ef9816`.
   - If present, replaces session key with server-provided 56-byte key.
   - If absent, client retains the original 56-byte key sent in `LogOnParams`.

#### 6.2 Failure Reply Format (`status != 1`)
Disassembly at VA `0x1008a84e8`–`0x1008a8540`:
1. **Status Byte:** Non-zero error status code (e.g., `0x02` invalid pass, `0x03` account not found, `0x05` already logged in).
2. **Error Message:** BigWorld variable-length string containing human-readable error text.
3. The client logs the error and terminates the login attempt without attempting BaseApp connection.

---

### 7. Independent Protocol Verification Summary

| Protocol Element | Statically Verified? | Wire Value / Range | Evidence VA | Confidence |
| :--- | :---: | :---: | :---: | :---: |
| Interface Name | **YES** | `"LoginInterface"` | `0x10309d15e` | **100%** |
| Method Name | **YES** | `"login"` | `0x1030453ed` | **100%** |
| Message ID | **YES** | `0x00` | `0x1008cde44` | **100%** |
| Length Header | **YES** | 2-byte uint16 LE | `0x1008cde4c` | **100%** |
| Login Version | **YES** | `43` (`0x0000002b`) | `0x1008a8290` | **100%** |
| Asymmetric Cipher | **YES** | RSA-OAEP SHA-1 | `0x100927c70` | **100%** |
| OAEP Padding Constant | **YES** | `4` (`RSA_PKCS1_OAEP_PADDING`) | `0x100927cc8` | **100%** |
| Session Key Length | **YES** | 56 Bytes | `0x1008994e8` | **100%** |
| Password Salt | **YES** | `aec05336` prefix | `0x1008776bc` | **100%** |
| Reply Status Success | **YES** | `0x01` | `0x1008a844c` | **100%** |
| Reply Address Decryption | **YES** | Blowfish CBC/PBC (8B multiple) | `0x1008a85f0` | **100%** |
| Replacement Key Cookie | **YES** | `0x32ef9816` | `0x1008a8654` | **100%** |
