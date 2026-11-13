# ROS Sothat — Phase 6.2B.13.2 Protocol Assumptions & Cryptographic Evidence

## 1. Executive Summary

This document formally records all protocol assumptions, native binary evidence citations, and cryptographic properties validated in Phase 6.2B.13.2 (`phase6B_13_2_blowfish_remediation/`).

The primary objective of this phase was the complete remediation of the Blowfish block cipher mode defect identified during Phase 6.2B.13.1, replacing standard Electronic Codebook (ECB) mode with the native BigWorld Plaintext-Chained Blowfish algorithm verified in the original iOS client Mach-O binary (`extracted/Payload/client.app/client`).

---

## 2. Cryptographic Protocol Specification

### 2.1 Native Cipher Mode: BigWorld Plaintext-Chained Blowfish
The native client binary does **not** use standard ECB or standard CBC. Instead, it implements a proprietary form of Plaintext Block Chaining (PBC) on top of low-level OpenSSL `BF_ecb_encrypt` calls.

#### Disassembly Evidence:
1. **Packet Encryption Routine (`EncryptionFilter::send` at VA `0x10091c7f0`–`0x10091c834`):**
   ```arm64
   0x10091c7f0: mov  x25, #0              ; Block byte offset = 0
   0x10091c7f4: mov  x8, #0               ; pPrevBlock pointer = NULL
   ; Loop body:
   0x10091c7fc: add  x27, x23, x25       ; src + offset (current plaintext block)
   0x10091c800: ldr  x9, [x27]           ; Load 8-byte plaintext block
   0x10091c804: cbz  x8, #0x10091c810    ; If pPrevBlock == NULL, skip XOR (First block!)
   0x10091c808: ldr  x8, [x8]            ; Load previous plaintext block
   0x10091c80c: eor  x9, x8, x9          ; XOR: curr_plaintext ^ prev_plaintext
   0x10091c810: add  x0, x26, x25        ; dest + offset
   0x10091c814: str  x9, [x0]            ; Store XORed block
   0x10091c818: ldr  x2, [x22, #0x30]    ; BF_KEY pointer
   0x10091c81c: mov  x1, x0              ; out pointer
   0x10091c820: mov  w3, #1              ; BF_ENCRYPT = 1
   0x10091c824: bl   #0x1000ab248        ; BF_ecb_encrypt(out, out, key, BF_ENCRYPT)
   0x10091c828: add  x25, x25, #8        ; offset += 8
   0x10091c82c: mov  x8, x27             ; pPrevBlock = (uint64*)(src + offset) (Previous Plaintext!)
   0x10091c830: cmp  w25, w24            ; offset < length
   0x10091c834: b.lt #0x10091c7fc
   ```

2. **Packet Decryption Routine (`EncryptionFilter::decrypt` at VA `0x10091ca8c`–`0x10091cb80`):**
   ```arm64
   0x10091cb38: mov  x24, #0             ; Block byte offset = 0
   0x10091cb3c: mov  x25, #0             ; pPrevBlock pointer = NULL
   ; Loop body:
   0x10091cb54: add  x0, x21, x24        ; src + offset (ciphertext block)
   0x10091cb58: add  x23, x22, x24       ; dest + offset (plaintext block)
   0x10091cb5c: ldr  x2, [x20, #0x30]    ; BF_KEY pointer
   0x10091cb60: mov  x1, x23             ; out pointer
   0x10091cb64: mov  w3, #0              ; BF_DECRYPT = 0
   0x10091cb68: bl   #0x1000ab248        ; BF_ecb_encrypt(src, dest, key, BF_DECRYPT)
   0x10091cb6c: cbz  x25, #0x10091cb44   ; If pPrevBlock == NULL, skip XOR (First block!)
   0x10091cb70: ldr  x8, [x25]           ; Load previous decrypted plaintext
   0x10091cb74: ldr  x9, [x22, x24]      ; Load current decrypted block
   0x10091cb78: eor  x8, x9, x8          ; XOR: decrypted ^ prev_plaintext
   0x10091cb7c: str  x8, [x22, x24]      ; Store unchained plaintext
   0x10091cb80: b    #0x10091cb44
   0x10091cb44: mov  x25, x23            ; pPrevBlock = (uint64*)(dest + offset) (Previous Plaintext!)
   0x10091cb48: add  x24, x24, #8        ; offset += 8
   0x10091cb4c: cmp  w19, w24            ; offset <= length
   0x10091cb50: b.le #0x10091cb10
   ```

3. **LoginHandler Decryption Invocation (`0x1008a85f0`):**
   ```arm64
   0x1008a85e8: mov x0, x21              ; EncryptionFilter pointer
   0x1008a85ec: mov x1, x20              ; Input ciphertext stream
   0x1008a85f0: bl  #0x10091ca8c         ; Calls EncryptionFilter::decrypt directly!
   ```

### 2.2 Mathematical Definition
Given $N$ blocks of 8-byte plaintext $P_0, P_1, \dots, P_{N-1}$:
- **Encryption:**
  $$C_0 = E_K(P_0)$$
  $$C_i = E_K(P_i \oplus P_{i-1}) \quad \text{for } 1 \le i < N$$
- **Decryption:**
  $$P_0 = D_K(C_0)$$
  $$P_i = D_K(C_i) \oplus P_{i-1} \quad \text{for } 1 \le i < N$$

---

## 3. The 24-Byte Mercury Address Structure

### 3.1 Binary Memory Layout
The native client unpacks `Mercury::Address` at VA `0x1008a8604` into `LoginHandler.baseAppAddr_` using exactly 20 bytes (`0x14`):
- `[0..3]`: IPv4 Address (network byte order, big-endian)
- `[4..5]`: Port Number (network byte order, big-endian)
- `[6..19]`: Zero padding / unused `sockaddr_in` fields (14 bytes)

Because Blowfish requires inputs to be multiples of 8 bytes (`tst w19, #7` assertion), the 20-byte address is padded with 4 additional zero bytes to produce a **24-byte payload** (3 blocks).

### 3.2 Plaintext Representation:
$$P_0 = [\text{IP (4B)}, \text{Port (2B)}, 0x00, 0x00]$$
$$P_1 = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]$$
$$P_2 = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]$$

### 3.3 Ciphertext Identity Property
Because $P_1 = \mathbf{0}_8$:
$$C_1 = E_K(P_1 \oplus P_0) = E_K(\mathbf{0}_8 \oplus P_0) = E_K(P_0) = C_0$$
Because $P_2 = \mathbf{0}_8$:
$$C_2 = E_K(P_2 \oplus P_1) = E_K(\mathbf{0}_8 \oplus \mathbf{0}_8) = E_K(\mathbf{0}_8)$$

**Mathematical Identity:** For any 24-byte zero-padded Mercury address, **Ciphertext Block 1 identically equals Ciphertext Block 0**. This property was formally verified in Golden Vector 6 (`GV06_ZERO_PADDED_ADDRESS_PROPERTY`).

---

## 4. Summary of Assumptions & Classifications

| Protocol Element | Evidence Status | Native VA Citation | Phase 13.2 Handling |
| :--- | :--- | :--- | :--- |
| **Blowfish Plaintext Chaining** | `[VERIFIED NATIVE]` | `0x10091c7f0`, `0x10091ca8c` | Fully implemented in `src/blowfish_filter.py` |
| **56-Byte Key Length** | `[VERIFIED NATIVE]` | `0x1030a211c` | Strictly enforced (56 bytes / 448 bits) |
| **24-Byte Address Layout** | `[VERIFIED NATIVE]` | `0x1008a8604`, `0x1008a862c` | 20B address + 4B transport pad |
| **Status Byte Evaluation** | `[VERIFIED NATIVE]` | `0x1008a844c` | Only status 1 is success; others error |
| **Status Codes 2–6** | `[SYNTHETIC ONLY]` | None (Client reads string) | Synthetic server error conventions |
| **Transport Daemon** | `[MISSING / DEFERRED]`| `0.0.0.0:20013` UDP | Deferred to Phase 14 |
