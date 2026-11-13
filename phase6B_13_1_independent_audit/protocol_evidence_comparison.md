# ROS Sothat — Phase 6.2B.13.1 Independent Protocol Evidence Comparison

## 1. Executive Protocol Verification Summary

This document presents a rigorous comparative analysis between the Phase 6.2B.13 Synthetic LoginApp Prototype (`phase6B_13_loginapp_prototype/`) and the ground-truth native disassembly of the original Rules of Survival Legacy iOS client binary (`extracted/Payload/client.app/client`, SHA-256: `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6`), augmented by BigWorld Technology 2.0.1 engine source references.

### Overall Protocol Accuracy
The Phase 13 prototype achieved high conceptual fidelity with BigWorld Mercury login conventions (RSA-OAEP 2048, 56-byte Blowfish key negotiation, 20-byte native `Mercury::Address`, and salt prefix reversal). However, the audit identified **one critical cryptographic mode defect** in the Blowfish filter, **one critical architecture limitation** (lack of a network transport daemon), and confirmed several **synthetic application conventions** that must be explicitly understood before Phase 14 native client integration.

---

## 2. Comprehensive Protocol Comparison Matrix

| Protocol Element | Native Client Evidence (Mach-O Disassembly & BigWorld Engine) | Phase 6.2B.13 Prototype Implementation | Classification | Audit Evaluation & Impact |
| :--- | :--- | :--- | :--- | :--- |
| **Mercury Magic / Flags** | 1 byte at packet offset 0. `0x80` = `FLAG_HAS_REQUESTS`, `0x01` = `FLAG_HAS_SEQUENCE_NUMBER`, `0x02` = `FLAG_HAS_ACKS`. Confirmed in Phase 6B.8.3 native disassembly. | `src/mercury_parser.py`: Exact bitmask definitions matching native flags. Correctly sets `FLAG_HAS_REQUESTS` on client bundles. | `[VERIFIED NATIVE]` | Fully compliant with native Mercury packet header format. |
| **Sequence Number** | 28-bit sequence number packed in 4 bytes (lower 28 bits sequence, top 4 bits reserved/flags). | `src/mercury_parser.py`: Packs and unpacks 28-bit sequence numbers using `seq & 0x0FFFFFFF`. | `[VERIFIED NATIVE]` | Fully compliant with Phase 6B.8.5 corrected sequence packing. |
| **Request ID Tracking** | 4-byte (`uint32_t`) request ID included when `FLAG_HAS_REQUESTS` is set. Native client tracks in `Mercury::Bundle`. | `src/bundle_parser.py`: Parses 32-bit little-endian `request_id`, preserves it, and correlates with reply bundle. | `[VERIFIED NATIVE]` | Fully compliant. Enables client `LoginHandler` to dispatch reply callback. |
| **Version Field** | 4-byte integer `0x0000002B` (decimal 43). Verified at VA `0x1008772a0` and BigWorld 2.0.1 protocol specification. | `src/logon_params.py`: Enforces `version == 43` (`0x2B`). Rejects mismatched versions with `INVALID_VERSION`. | `[VERIFIED NATIVE]` | Exact match with native client BigWorld protocol version. |
| **RSA Public Key Encryption** | RSA-2048 with OAEP padding and SHA-1 digest (`RSA_PKCS1_OAEP_PADDING`). Verified at VA `0x1008773c0` (`RSA_public_encrypt`). | `src/crypto.py`: Uses `cryptography.hazmat.primitives.asymmetric.padding.OAEP` with `MGF1(SHA1)` and `SHA1()`. | `[VERIFIED NATIVE]` | Exact cryptographic match with OpenSSL 0.9.8 / 1.0.0 client routine. |
| **Blowfish Key Length** | Exactly 56 bytes (`KEY_SIZE = 56`). Initialized via `EncryptionFilter::initKey` (`0x1030a211c`). | `src/crypto.py`, `src/blowfish_filter.py`: Generates and expects 56-byte session keys. | `[VERIFIED NATIVE]` | Maximum key length supported by standard OpenSSL Blowfish. |
| **Client Nonce (Replay)** | 8-byte (`uint64_t`) random integer embedded in encrypted LogOnParams payload. | `src/logon_params.py`, `src/session_manager.py`: Extracts 8-byte uint64 nonce, tracks against sliding window cache. | `[VERIFIED NATIVE]` | Fully compliant with BigWorld replay prevention mechanism. |
| **Password Salt & Prefix** | Client prepends hardcoded salt `"aec05336"` and decrements each byte by 1 (`sub w23, w8, #1` at VA `0x100877718`). | `src/auth.py`: `reverse_salt_password` checks prefix `"aec05336"` and increments each char (`ord(c) + 1`). | `[VERIFIED NATIVE]` | 100% byte-accurate reverse operation of native client disassembly. |
| **Status Byte Evaluation** | Native `LoginHandler::handleMessage` at VA `0x1008a844c` checks `cmp w8, #1; b.ne ...`. Only `0x01` is success; all others read error string. | `src/auth.py`: Defines `STATUS_SUCCESS = 0x01`, `STATUS_INVALID_PASSWORD = 0x02`, `STATUS_USER_NOT_FOUND = 0x03`, etc. | `[SYNTHETIC ONLY]` | Native client treats any non-1 status as failure. Codes 2–6 are server conventions. |
| **Error String Formatting** | BigWorld length-prefixed string (1 byte length $N \le 255$, followed by $N$ ASCII/UTF-8 bytes). Fallback at `0x10309c1dc`. | `src/login_reply.py`: Formats error messages as `struct.pack('B', len(msg)) + msg.encode()`. | `[VERIFIED NATIVE]` | Matches native client BinaryIStream string unpacker. |
| **Address Block Size & Pad** | Native `Mercury::Address` is 20 bytes (4B IP + 2B port + 14B pad). Blowfish requires 24 bytes (multiple of 8). `cmp w8, #5` at `0x1008a862c`. | `src/address.py`: Packs 20-byte native address, adds 4 bytes zero padding $\to$ 24 bytes total. | `[VERIFIED NATIVE]` | Verified native behavior; client reads 20 bytes and ignores 4 bytes trailing padding. |
| **Blowfish Cipher Mode** | Native client uses **BigWorld Plaintext-Chained Blowfish** (`EncryptionFilter::encrypt` at `0x10091c7f0`, `decrypt` at `0x10091ca8c`). | `src/blowfish_filter.py`: Uses standard **Blowfish ECB** (`modes.ECB()`). | `[INCORRECT / DEFECT]` | **CRITICAL DEFECT**: Native client XORs each block after the first with the previous plaintext block before encryption. |
| **Network Transport Daemon** | BigWorld LoginApp operates as an active UDP socket daemon listening on port 20013. | `src/loginapp_core.py`: Exposes `handle_datagram()` as an in-memory function. No socket or port bound. | `[MISSING]` | Prototype is an in-memory simulator, not an operational network daemon. |

---

## 3. Deep Dive: The Blowfish Plaintext-Chaining Defect

### 3.1 Ground-Truth Disassembly vs BigWorld Engine Source
Reverse engineering of the native iOS client binary (`extracted/Payload/client.app/client`) at VA `0x10091c7f0`–`0x10091c834` (`EncryptionFilter::send` / `encrypt`) and VA `0x10091ca8c`–`0x10091cb80` (`EncryptionFilter::decrypt`), correlated with BigWorld Technology 2.0.1 `encryption_filter.cpp`, reveals the exact block cipher logic:

```cpp
// BigWorld Technology 2.0.1 - encryption_filter.cpp
int EncryptionFilter::encrypt( const unsigned char * src, unsigned char * dest, int length )
{
    uint64 * pPrevBlock = NULL;
    for (int i=0; i < length; i += BLOCK_SIZE)
    {
        if (pPrevBlock)
            *(uint64*)(dest + i) = *(uint64*)(src + i) ^ *pPrevBlock;
        else
            *(uint64*)(dest + i) = *(uint64*)(src + i);

        BF_ecb_encrypt( dest + i, dest + i, this->pBFKey(), BF_ENCRYPT );

        pPrevBlock = (uint64*)(src + i); // Points to previous PLAINTEXT block!
    }
    return length;
}
```

And corresponding decryption routine called by `LoginHandler` at VA `0x1008a85f0`:
```cpp
// BigWorld Technology 2.0.1 - encryption_filter.cpp
int EncryptionFilter::decrypt( const unsigned char * src, unsigned char * dest, int length )
{
    uint64 * pPrevBlock = NULL;
    for (int i=0; i < length; i += BLOCK_SIZE)
    {
        BF_ecb_encrypt( src + i, dest + i, this->pBFKey(), BF_DECRYPT );

        if (pPrevBlock)
            *(uint64*)(dest + i) ^= *pPrevBlock;

        pPrevBlock = (uint64*)(dest + i); // Points to previous PLAINTEXT block!
    }
    return length;
}
```

### 3.2 Mathematical Formulation
Let $P = [P_0, P_1, P_2]$ represent the three 8-byte blocks of the 24-byte BaseApp address payload ($P_0$ = IP + Port + 2B zeroes, $P_1$ = 8B zeroes, $P_2$ = 8B zeroes).
Let $C = [C_0, C_1, C_2]$ represent the ciphertext blocks sent by the server.

#### Native BigWorld Plaintext-Chaining:
$$\begin{aligned}
C_0 &= E_K(P_0) \\
C_1 &= E_K(P_1 \oplus P_0) \\
C_2 &= E_K(P_2 \oplus P_1)
\end{aligned}$$

#### Phase 13 Prototype (ECB Mode):
$$\begin{aligned}
C_0^{\text{proto}} &= E_K(P_0) \\
C_1^{\text{proto}} &= E_K(P_1) \\
C_2^{\text{proto}} &= E_K(P_2)
\end{aligned}$$

### 3.3 Impact on Native Client Decryption
When the native iOS client receives the Phase 13 prototype's ECB-encrypted address:
1. **Block 0 ($C_0$):** Decrypted as $D_K(C_0) = P_0$. Native client correctly extracts the 4-byte IP address and 2-byte port.
2. **Block 1 ($C_1$):** Native client computes $P_1' = D_K(C_1^{\text{proto}}) \oplus P_0 = P_1 \oplus P_0 = 0 \oplus P_0 = P_0$. Bytes 8–15 of the address struct receive a duplicate of the IP/port block instead of zero padding.
3. **Block 2 ($C_2$):** Native client computes $P_2' = D_K(C_2^{\text{proto}}) \oplus P_1' = P_2 \oplus P_0 = 0 \oplus P_0 = P_0$.
4. **Mercury Channel Packets:** Once the client connects to BaseApp, multi-block packets encrypted with standard ECB will fail decryption completely, corrupting all application bundles after block 0.

---

## 4. Ground Truth on Login Status Codes

In `phase6B_13_loginapp_prototype/src/auth.py`, status codes are defined as:
- `0x01`: `LOGON_STATUS_SUCCESS`
- `0x02`: `LOGON_STATUS_INVALID_PASSWORD`
- `0x03`: `LOGON_STATUS_USER_NOT_FOUND`
- `0x04`: `LOGON_STATUS_ACCOUNT_BANNED`
- `0x05`: `LOGON_STATUS_SERVER_FULL`
- `0x06`: `LOGON_STATUS_VERSION_MISMATCH`

### Native Client Code Inspection (`LoginHandler::handleMessage` at VA `0x1008a844c`):
```arm64
0x1008a8448: ldrb w8, [x21]          ; Load status byte from bundle
0x1008a844c: cmp  w8, #1              ; Compare with 1 (LOGON_STATUS_SUCCESS)
0x1008a8450: b.ne #0x1008a84e0        ; If not 1, branch directly to error handler!
```
At `0x1008a84e0`, the native client does not evaluate secondary switch/case branches for status codes 2, 3, 4, etc. Instead, it immediately reads the BigWorld error string from the stream and forwards the error string to the UI callback (`LoginHandler::onLoginFailed`).

**Conclusion:** Status code `0x01` is the only structurally significant status byte in the client binary. Status codes `0x02`–`0x06` are synthetic application-level conventions. They are fully safe to use because the client treats all non-1 statuses identically, displaying the accompanying error string.

---

## 5. Formal Evidence Classification Summary

- **Total Protocol Elements Evaluated:** 13
- **`[VERIFIED NATIVE]`:** 9 (Mercury flags, 28-bit sequence, request correlation, version 43, RSA-OAEP SHA-1, 56B Blowfish key, 64-bit nonce, password salt reversal, 24-byte zero-padded address layout).
- **`[SYNTHETIC ONLY]`:** 2 (Status codes 2–6 as specific enums, in-memory account store).
- **`[UNVERIFIED / PLAUSIBLE]`:** 0.
- **`[INCORRECT / DEFECT]`:** 1 (Blowfish ECB mode vs BigWorld Plaintext-Chained Blowfish).
- **`[MISSING]`:** 1 (Active UDP socket daemon on port 20013).
