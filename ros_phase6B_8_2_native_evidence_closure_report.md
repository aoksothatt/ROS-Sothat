# ROS Sothat — Phase 6.2B.8.2
# Native Evidence Closure Audit: Strict Read-Only Technical Investigation

**Auditor:** Google DeepMind Agentic AI Assistant (Antigravity)  
**Target:** Rules of Survival (iOS Legacy Client, ARM64 Mach-O Executable) & Phase 6.2B.8 Gateway  
**Date:** November 12, 2026  
**Audit Classification:** READ-ONLY TECHNICAL INVESTIGATION & CONTROL-FLOW CLOSURE  
**Final Audit Verdict:** **PASS WITH ISSUES**  

---

## 1. Executive Summary

This investigation was conducted under strict read-only constraints to independently determine whether the architectural and cryptographic claims established in Phase 6.2B.8 are supported by native ARM64 instructions in the original Rules of Survival Mach-O executable (`extracted/Payload/client.app/client`).

Every relevant function, register lifecycle, memory access pattern, and control-flow branch was disassembled directly from the pristine binary and traced without reliance on earlier narrative assertions.

### Core Findings Summary:
1. **Plaintext Block Chaining (PBC) [VERIFIED BY NATIVE EVIDENCE]:**
   Instruction-level tracing of `EncryptionFilter::send` (`0x10091c7f0`–`0x10091c834`) and `EncryptionFilter::recv` (`0x10091c95c`–`0x10091c9c0`) conclusively proves that the symmetric cipher operates in **Plaintext Block Chaining (PBC)** mode ($C_i = E(P_i \oplus P_{i-1})$) with an implicit all-zero IV ($C_0 = E(P_0)$). Register `x8` in `send` is loaded from `x27` (`mov x8, x27` at `0x10091c82c`), which points strictly to the **input plaintext buffer**, not the output ciphertext buffer. In `recv`, in-place decryption executes ECB decryption followed by XOR with the previously recovered plaintext block ($P_{i-1}$).
2. **Padding Semantics [VERIFIED BY NATIVE EVIDENCE]:**
   The padding formula is strictly `pad_len = 8 - (raw_len & 7)` ($1 \le \text{pad\_len} \le 8$). The sender writes the padding count **strictly to the final byte** (`sturb w8, [x9, #-1]` at `0x10091c7c4`). Preceding padding slack bytes are uninitialized and never checked. The receiver validates only that `pad_len <= 8` and `total_len >= pad_len` (`0x10091c9e0`–`0x10091c9e4`). Padding is removed **before** checksum verification and packet dispatch.
3. **Checksum Algorithm & Coverage [VERIFIED BY NATIVE EVIDENCE]:**
   Disassembly of `Nub::processFilteredPacket` (`0x100922860`–`0x100922c4c`) confirms that Mercury packet integrity uses a **32-bit bitwise XOR accumulation** over all little-endian 32-bit dwords from Offset 0 (Flags word) up to the datagram tail. The 4-byte checksum field is zeroed in-place during computation (`str wzr, [x10]` at `0x100922a54`) and restored afterward (`str w11, [x10]` at `0x100922c44`). Checksum verification executes strictly **after** Blowfish decryption and unpadding.
4. **Flags Upper Bound Rejection [VERIFIED BY NATIVE EVIDENCE]:**
   The instruction `0x100922898: cmp w8, #0x400` followed by `b.hs #0x1009228dc` enforces an unsigned upper-bound check on the 16-bit flags word. If `flags >= 0x0400`, the packet is immediately logged as `"received packet with bad flags %x"` (`0x1030a2d6c`), the discard counter is incremented, and the function returns `-4` (`REASON_CORRUPTED_PACKET`).
5. **Critical Discovery — Flag Bit Mask Discrepancy [CONTRADICTED / SYNTHETIC CHOICE]:**
   While the gateway correctly implements the `flags < 0x0400` constraint, direct disassembly of branch instructions (`tbnz`/`tbz`) in `Nub::processFilteredPacket` reveals that the native engine assigns flag bits differently from the synthetic gateway's enumeration:
   - Native Bit 2 (`0x0004`): `FLAG_HAS_ACKS` (Gateway assigned `0x0008`)
   - Native Bit 6 (`0x0040`): `FLAG_HAS_SEQUENCE_NUMBER` (Gateway assigned `0x0004`)
   - Native Bit 9 (`0x0200`): `FLAG_CREATE_CHANNEL` (Gateway assigned `0x0001`)
   - Native Bit 3 (`0x0008`): `FLAG_ON_CHANNEL` (Gateway assigned `0x0020`)
   - Agreement exists on Bit 1 (`0x0002`: Piggybacks), Bit 7 (`0x0080`: Indexed Channel), and Bit 8 (`0x0100`: Checksum).
6. **Golden Vectors [VERIFIED BY INDEPENDENT SYNTHETIC CALCULATION]:**
   Both multi-block datagram vectors reported in Phase 6.2B.8.1 were reproduced independently from pure mathematical formulas and fixed literal expected outputs without invoking gateway helper functions.
7. **Historical Integrity [VERIFIED BY SOURCE INSPECTION]:**
   Cryptographic SHA-256 hashes of the original IPA (`d1f638ad...`) and extracted Mach-O (`51e63bfe...`) match historical records bit-for-bit. Zero files in `ros-private-server/` or `phase6B_8_local_gateway/` were modified.

---

## 2. Final Verdict

### Audit Verdict: **PASS WITH ISSUES**

**Justification:**
- **Passing Criteria:** The foundational protocol claims—Blowfish Plaintext Block Chaining (PBC), single-byte wastage count padding, 32-bit SIMD XOR checksum, post-decryption validation, and `flags >= 0x0400` rejection—are conclusively proven by native ARM64 instructions.
- **Issues Warranting Caution:**
  1. **Flag Bit Allocations:** The synthetic gateway's flag constants (`packet_parser.py`) for sequence numbers (`0x0004`), ACKs (`0x0008`), and channel creation (`0x0001`) deviate from the native client's bit assignments (Bit 6 = sequence number, Bit 2 = ACKs, Bit 9 = channel creation). While self-consistent between the synthetic client and synthetic gateway, an original physical client will misinterpret these flags.
  2. **Synthetic Payload Layer:** Datagram payloads remain UTF-8 JSON commands rather than native BigWorld binary RPC bundles.
  3. **Pre-Shared Static Keys:** Session keys are pre-shared rather than negotiated via dynamic RSA-OAEP exchange.

---

## 3. Investigation A — PBC Pointer and Buffer Lifecycle

### 3.1 Disassembly Evidence: `EncryptionFilter::send`

The encryption routine is implemented at `0x10091c6e4`–`0x10091c890`:

```assembly
; --- Initialization & Packet Setup ---
0x10091c710:  mov      x24, x4                    ; x24 = raw_len
0x10091c714:  mov      x23, x3                    ; x23 = plaintext buffer pointer (input Packet data)
0x10091c71c:  mov      x22, x0                    ; x22 = EncryptionFilter* this
...
0x10091c730:  ldr      x19, [x25]                 ; x19 = newly allocated out_packet from pool
...
0x10091c7b8:  add      x24, x8, x24               ; x24 = padded_len = raw_len + pad_len
0x10091c7bc:  strh     w24, [x19, #0x1a]          ; out_packet->len_ = padded_len
0x10091c7c0:  add      x9, x24, x23               ; x9 = plaintext buffer + padded_len
0x10091c7c4:  sturb    w8, [x9, #-1]              ; Write pad_len to final byte of plaintext buffer!

; --- Encryption Loop ---
0x10091c7f0:  mov      x25, #0                    ; x25 = offset = 0
0x10091c7f4:  mov      x8, #0                     ; x8 = prev_block_ptr = NULL (IV = 0)
0x10091c7f8:  add      x26, x19, #0x60            ; x26 = out_packet->data()
0x10091c7fc:  add      x27, x23, x25              ; x27 = plaintext_buffer + offset (block i)
0x10091c800:  ldr      x9, [x27]                  ; Load 64-bit plaintext block P_i
0x10091c804:  cbz      x8, #0x10091c810           ; If x8 == NULL (block 0), skip XOR
0x10091c808:  ldr      x8, [x8]                   ; Load 64-bit previous block from [x8]
0x10091c80c:  eor      x9, x8, x9                 ; x9 = P_i ^ (*x8)
0x10091c810:  add      x0, x26, x25               ; x0 = out_packet->data() + offset
0x10091c814:  str      x9, [x0]                   ; Store XORed block into out_packet
0x10091c818:  ldr      x2, [x22, #0x30]           ; Blowfish key schedule pointer
0x10091c81c:  mov      x1, x0                     ; out = x0
0x10091c820:  mov      w3, #1                     ; 1 = BF_ENCRYPT
0x10091c824:  bl       #0x1000ab248               ; BF_ecb_encrypt(x0, x0, &keySchedule, 1)
0x10091c828:  add      x25, x25, #8               ; offset += 8
0x10091c82c:  mov      x8, x27                    ; *** CRITICAL: x8 = x27 (PREVIOUS PLAINTEXT POINTER!) ***
0x10091c830:  cmp      w25, w24                   ; offset < padded_len?
0x10091c834:  b.lt     #0x10091c7fc               ; Next block
```

### 3.2 Disassembly Evidence: `EncryptionFilter::recv`

The decryption routine is implemented at `0x10091c8e8`–`0x10091ca30` (in-place decryption):

```assembly
0x10091c910:  mov      x20, x3                    ; x20 = input packet
0x10091c914:  ldrh     w8, [x3, #0x1a]            ; packet->len_
0x10091c918:  ldrh     w9, [x3, #0x1c]            ; packet->footers_len_
0x10091c91c:  add      x23, x9, x8                ; x23 = total ciphertext length
0x10091c920:  tst      w23, #7                    ; Check length % 8 == 0
0x10091c924:  b.eq     #0x10091c95c               ; Valid block alignment

; --- Decryption Loop Setup ---
0x10091c964:  mov      x24, #0                    ; x24 = offset = 0
0x10091c968:  mov      x26, #0                    ; x26 = prev_plaintext_ptr = NULL (IV = 0)
0x10091c96c:  add      x25, x20, #0x60            ; x25 = packet->data()
0x10091c970:  b        #0x10091c998               ; Decrypt Block 0 first

; --- In-Place ECB Decryption Step ---
0x10091c998:  add      x22, x25, x24              ; x22 = packet->data() + offset (block i)
0x10091c99c:  ldr      x2, [x21, #0x30]           ; Blowfish key schedule
0x10091c9a0:  mov      x0, x22                    ; in = x22
0x10091c9a4:  mov      x1, x22                    ; out = x22 (in-place)
0x10091c9a8:  mov      w3, #0                     ; 0 = BF_DECRYPT
0x10091c9ac:  bl       #0x1000ab248               ; BF_ecb_encrypt(x22, x22, &keySchedule, 0)
0x10091c9b0:  cbnz     x26, #0x10091c974          ; If x26 != NULL (i >= 1), jump to XOR!
0x10091c9b4:  mov      x26, x22                   ; Block 0: x26 = decrypted P_0 pointer!
0x10091c9b8:  add      x24, x24, #8               ; offset += 8
0x10091c9bc:  cmp      x24, x23                   ; offset < total_len?
0x10091c9c0:  b.lo     #0x10091c998

; --- Plaintext XOR Step (Block i >= 1) ---
0x10091c974:  add      x8, x20, x24               ; x8 = packet + offset
0x10091c978:  ldr      x9, [x26]                  ; Load previous decrypted plaintext P_(i-1)!
0x10091c97c:  add      x26, x8, #0x60             ; Advance x26 to current block pointer
0x10091c980:  ldr      x8, [x25, x24]             ; Load ECB-decrypted current block D(C_i)
0x10091c984:  eor      x8, x8, x9                 ; Recover P_i = D(C_i) ^ P_(i-1)
0x10091c988:  str      x8, [x25, x24]             ; Store P_i back into packet buffer
0x10091c98c:  add      x24, x24, #8               ; offset += 8
0x10091c990:  cmp      x24, x23
0x10091c994:  b.hs     #0x10091c9c4               ; All blocks complete -> go to unpadding
```

### 3.3 Register Lifecycle and Investigation Answers

| Question | Answer & Instruction Proof | Classification |
|---|---|---|
| **1. Current plaintext pointer register** | In `send`: `x27 = x23 + offset` (`0x10091c7fc`). In `recv`: `x22 = x25 + offset` (`0x10091c998`). | VERIFIED BY NATIVE EVIDENCE |
| **2. Previous-block pointer register** | In `send`: `x8` (set at `0x10091c82c: mov x8, x27`). In `recv`: `x26` (set at `0x10091c9b4: mov x26, x22` and `0x10091c97c`). | VERIFIED BY NATIVE EVIDENCE |
| **3. Memory pointed to by previous-block pointer** | In `send`: References the **original input plaintext buffer** (`x23`). In `recv`: References the **previously recovered plaintext block** ($P_{i-1}$) in the packet buffer. | VERIFIED BY NATIVE EVIDENCE |
| **4. Are pointed-to bytes overwritten during encryption?** | **NO.** In `send`, ciphertext is written to `x0` in a distinct destination packet `x19`. Input buffer `x23` remains untouched. | VERIFIED BY NATIVE EVIDENCE |
| **5. Advance rate per block** | Exactly **8 bytes** per block (`0x10091c828: add x25, x25, #8`; `0x10091c98c: add x24, x24, #8`). | VERIFIED BY NATIVE EVIDENCE |
| **6. Handling of first block (Block 0)** | `x8` is initialized to 0 (`mov x8, #0` at `0x10091c7f4`). `cbz x8, #0x10091c810` branches over the XOR operation. Effective IV = 0. In `recv`, `cbz x26` branches over XOR on Block 0. | VERIFIED BY NATIVE EVIDENCE |
| **7. Does receive mirror chaining?** | **YES.** `recv` decrypts $D(C_i)$ and XORs with `[x26]` containing $P_{i-1}$, since $D(C_i) = P_i \oplus P_{i-1}$. | VERIFIED BY NATIVE EVIDENCE |
| **8. Identical block boundaries?** | **YES.** Both strictly enforce 8-byte alignment (`tst w23, #7`). | VERIFIED BY NATIVE EVIDENCE |
| **9. Are partial final blocks padded before encryption?** | **YES.** `padded_len = raw_len + (8 - (raw_len & 7))` is computed and stored before the loop begins. | VERIFIED BY NATIVE EVIDENCE |
| **10. Is trailer included in PBC input?** | **YES.** Trailer byte is written to `buf[padded_len - 1]` at `0x10091c7c4` before encryption; the final block contains the trailer byte. | VERIFIED BY NATIVE EVIDENCE |

### 3.4 Mathematical Proof: PBC vs. CBC

$$\begin{aligned}
\text{Standard CBC Mode:} \quad & C_i = E_K(P_i \oplus C_{i-1}) \\
\text{Native ROS Mode (PBC):} \quad & C_i = E_K(P_i \oplus P_{i-1})
\end{aligned}$$

- At `0x10091c82c`, the instruction is `mov x8, x27`. Register `x27` holds the address of $P_i$. If CBC were intended, the instruction would have been `mov x8, x0` (the address of $C_i$).
- In `recv`, `0x10091c978: ldr x9, [x26]` loads from `x26`, which holds the memory of block $i-1$ **after** it has already been overwritten with recovered plaintext $P_{i-1}$ by `0x10091c988: str x8, [x25, x24]`.
- **Conclusion:** The algorithm is unambiguously **Plaintext Block Chaining (PBC)**.

---

## 4. Investigation B — Padding Semantics

### 4.1 Send & Receive Native Mechanics

1. **Length Formula:**
   $$\text{pad\_len} = 8 - (\text{raw\_len} \pmod 8) \quad (1 \le \text{pad\_len} \le 8)$$
   - Disassembly at `0x10091c7ac`–`0x10091c7b4`:
     ```assembly
     and  w8, w24, #7     ; w8 = raw_len & 7
     mov  w9, #8
     sub  w8, w9, w8      ; w8 = 8 - (raw_len & 7)
     add  x24, x8, x24    ; x24 = raw_len + pad_len
     ```
2. **Trailer Byte Storage:**
   - `0x10091c7c4: sturb w8, [x9, #-1]` writes `w8` (`pad_len`) exclusively to the final byte of the padded buffer.
3. **Slack Bytes Handling:**
   - The native sender does **not** zero preceding padding bytes. Slack bytes retain whatever values were previously in the packet memory buffer.
   - The synthetic gateway's policy of zero-filling slack bytes (`0x00`) is an intentional hygiene choice that is 100% accepted by the native receiver.
4. **Receiver Validation:**
   - Disassembly at `0x10091c9dc`–`0x10091c9e8`:
     ```assembly
     ldrb  w21, [x10, #0x5f]  ; w21 = final byte of decrypted buffer
     cmp   w21, #8            ; check w21 <= 8
     ccmp  w9, w21, #0, ls     ; if w21 <= 8, check total_len >= w21
     b.hs  #0x10091ca24        ; valid -> branch to unpad
     ```
   - Preceding padding bytes are **never checked**.
5. **Padding Removal Timing:**
   - At `0x10091ca28: sub w8, w8, w21; strh w8, [x20, #0x1a]`, `packet->len_` is truncated by `pad_len`. This occurs **before** `processFilteredPacket` is called. Padding bytes are therefore **excluded** from the Mercury checksum.

### 4.2 Test Length Matrix

| Raw Length | Pad Length | Padded Length | Blowfish Blocks | Trailer Byte | Receiver Truncation |
|---|---|---|---|---|---|
| **0 bytes** | 8 bytes | 8 bytes | 1 block | `0x08` | $8 - 8 = 0$ bytes (Note: zero-length ciphertext rejected by `cbz w23` in `recv`) |
| **1 byte** | 7 bytes | 8 bytes | 1 block | `0x07` | $8 - 7 = 1$ byte |
| **7 bytes** | 1 byte | 8 bytes | 1 block | `0x01` | $8 - 1 = 7$ bytes |
| **8 bytes** | 8 bytes | 16 bytes | 2 blocks | `0x08` | $16 - 8 = 8$ bytes (appends full 8-byte block) |
| **9 bytes** | 7 bytes | 16 bytes | 2 blocks | `0x07` | $16 - 7 = 9$ bytes |
| **15 bytes**| 1 byte | 16 bytes | 2 blocks | `0x01` | $16 - 1 = 15$ bytes |
| **16 bytes**| 8 bytes | 24 bytes | 3 blocks | `0x08` | $24 - 8 = 16$ bytes (appends full 8-byte block) |
| **17 bytes**| 7 bytes | 24 bytes | 3 blocks | `0x07` | $24 - 7 = 17$ bytes |

---

## 5. Investigation C — Checksum Algorithm and Exact Coverage

### 5.1 Disassembly Evidence: `Nub::processFilteredPacket`

The checksum calculation resides at `0x100922a38`–`0x100922c4c`:

```assembly
; --- Extraction & In-Place Zeroing ---
0x100922a38:  sub      w9, w9, #4                 ; w9 = remaining length - 4
0x100922a48:  add      x10, x19, w9, uxth
0x100922a4c:  ldr      w11, [x10, #0x60]!         ; w11 = uint32 checksum from datagram tail
0x100922a50:  str      w11, [x19, #0x5c]          ; store in packet->checksum_
0x100922a54:  str      wzr, [x10]                 ; *** ZERO OUT CHECKSUM FIELD IN-PLACE ***

; --- Loop Boundary Preparation ---
0x100922a58:  add      x12, x19, #0x64            ; packet_data + 4
0x100922a5c:  cmp      x10, x12
0x100922a60:  csel     x12, x10, x12, hi
0x100922a64:  mvn      x13, x19                   ; ~x19
0x100922a68:  add      x12, x12, x13              ; x12 - x19 - 1
0x100922a6c:  sub      x12, x12, #0x60            ; x12 = checksum_offset - 1
0x100922a70:  cmp      x12, #0x1c                 ; offset >= 28 bytes?
0x100922a74:  b.hs     #0x100922bdc               ; branch to NEON SIMD loop

; --- ARM NEON SIMD Loop (>= 28 bytes) ---
0x100922bdc:  lsr      x12, x12, #2               ; dword_count - 1
0x100922be0:  add      x13, x12, #1               ; total dwords
0x100922be4:  and      x14, x13, #0x7ffffffffff8  ; round down to mult of 8 dwords (32 bytes)
0x100922be8:  add      x12, x28, x14, lsl #2      ; scalar resume pointer
0x100922bf0:  movi     v0.16b, #0
0x100922bf8:  movi     v1.16b, #0
0x100922bfc:  ldp      q2, q3, [x15, #-0x10]      ; load 32 bytes (8 dwords)
0x100922c00:  eor      v0.16b, v2.16b, v0.16b     ; 32-bit vector XOR
0x100922c04:  eor      v1.16b, v3.16b, v1.16b
0x100922c08:  add      x15, x15, #0x20
0x100922c0c:  subs     x16, x16, #8
0x100922c10:  b.ne     #0x100922bfc

; --- Horizontal Reduction to 32 bits ---
0x100922c14:  eor      v0.16b, v1.16b, v0.16b
0x100922c18:  dup      v1.2d, v0.d[1]
0x100922c1c:  eor      v0.16b, v0.16b, v1.16b
0x100922c20:  dup      v1.4s, v0.s[1]
0x100922c24:  eor      v0.16b, v0.16b, v1.16b
0x100922c28:  fmov     w22, s0                    ; w22 = 32-bit XOR sum
0x100922c2c:  cmp      x13, x14
0x100922c30:  b.eq     #0x100922c44               ; If all dwords processed, skip scalar loop

; --- Scalar Fallback Loop ---
0x100922c34:  ldr      w13, [x12], #4             ; load 32-bit dword
0x100922c38:  eor      w22, w13, w22              ; w22 ^= w13
0x100922c3c:  cmp      x12, x10                   ; reached checksum offset?
0x100922c40:  b.lo     #0x100922c34

; --- Restoration & Comparison ---
0x100922c44:  str      w11, [x10]                 ; *** RESTORE SAVED CHECKSUM ***
0x100922c48:  cmp      w22, w11                   ; Compare computed vs stored checksum
0x100922c4c:  b.eq     #0x100922974               ; If matching, unpack footers!
```

### 5.2 Byte Coverage Diagram

```
+===================================================================================================+
|                                    WIRE DATAGRAM (ENCRYPTED)                                      |
+---------------------------------------------------------------------------------------------------+
| [100% Blowfish PBC Ciphertext: Blocks 0 .. N] (Block size = 8 bytes, includes trailer padding)   |
+===================================================================================================+
                                                │
                                    (1) Blowfish PBC Decrypt
                                    (2) Strip Padding Trailer
                                                ▼
+===================================================================================================+
|                                 DECRYPTED & UNPADDED DATAGRAM                                     |
+--------------------+-----------------------------+-------------------------------+----------------+
| Offset 0x0000      | Offset 0x0002               | Offset (Tail - Footers_Len)   | Offset Tail - 4|
| Header Flags Word  | Payload Body                | Optional Reverse Footers      | Checksum Field |
| 2 Bytes (uint16)   | Message Bundle Data         | (ReqOffset, SeqNum, ACKs, CID)| 4 Bytes (uint32|
+--------------------+-----------------------------+-------------------------------+----------------+
|   [Flags 16-bit]   |   [Payload Bytes ...]       | [Footers Bytes ...]           | 00  00  00  00 |
+--------------------+-----------------------------+-------------------------------+----------------+
|<────────────────────────────────── INCLUDED IN 32-BIT XOR SUM ───────────────────────────────────>|
                                                                                | (Zeroed In-    |
                                                                                |  Place during  |
                                                                                |  computation)  |
```

### 5.3 Resolution of Checksum Criteria

1. **Algorithm:** 32-bit bitwise XOR summation.
2. **Operation:** XOR only (`eor`). No additions, subtractions, carries, or CRC polynomial.
3. **Word Format:** Little-endian 32-bit dwords (`<I`).
4. **Non-4-byte Alignment Handling:** Zeroing the 4-byte checksum field ensures that trailing partial words are padded with zero bytes, which contribute $0 \oplus 0 = 0$ to the XOR accumulation.
5. **Start Offset:** Byte 0 (`packet_data + 0`).
6. **End Offset:** Checksum field tail (`x10`).
7. **Flags Field Included:** YES (Offset 0–1 occupies the low 16 bits of the first 32-bit dword).
8. **Checksum Field Zeroed:** YES, in-place via `str wzr, [x10]` at `0x100922a54`, restored via `str w11, [x10]` at `0x100922c44`.
9. **Footers Included:** YES, all footers preceding the checksum field are included.
10. **Padding Included:** NO, padding is stripped prior to entering `processFilteredPacket`.
11. **Verification Timing:** Verified strictly **AFTER** decryption.
12. **Unpadding Timing:** Verified strictly **AFTER** unpadding.

---

## 6. Investigation D — The 0x0400 Flags Condition

### 6.1 Control-Flow Analysis

```assembly
0x100922890:  mov      x28, x2                    ; x28 = Packet*
0x100922894:  ldrh     w8, [x28, #0x60]!          ; w8 = uint16 Flags at Offset 0
0x100922898:  cmp      w8, #0x400                 ; Compare flags against 0x0400
0x10092289c:  b.hs     #0x1009228dc               ; If unsigned w8 >= 0x0400, branch to error!
...
; --- Normal Path (flags < 0x0400) ---
0x1009228a8:  tbnz     w8, #3, #0x1009228b8
...
0x100922904:  ldrh     w9, [x19, #0x1a]           ; Check total packet size >= 2
0x100922910:  cmp      w11, #2
0x100922914:  b.hi     #0x100922970               ; Proceed to footer checks

; --- Error Discard Path (flags >= 0x0400) ---
0x1009228dc:  ldrb     w8, [x27, #0x22c]
0x1009228e0:  cbnz     w8, #0x10092293c           ; If logging disabled, jump to discard counter
0x1009228e4:  mov      x0, x20                    ; endpoint
0x1009228e8:  bl       #0x100916db0               ; Endpoint::asString
0x1009228ec:  ldrh     w8, [x28]                  ; w8 = bad flags value
0x1009228f0:  stp      x0, x8, [sp, #8]
0x1009228f4:  str      x21, [sp]                  ; Nub* this
0x1009228f8:  adrp     x0, #0x1030a2000
0x1009228fc:  add      x0, x0, #0xd6c             ; String: "Nub(%p)::processFilteredPacket( %s ): received packet with bad flags %x\n"
0x100922900:  b        #0x100922938
0x100922938:  bl       #0x101b634c0               ; Log message
0x10092293c:  ldr      w8, [x27, #0x28]           ; nub->dropped_packets_counter
0x100922940:  add      w8, w8, #1
0x100922944:  str      w8, [x27, #0x28]
0x100922948:  mov      w23, #-4                   ; return code = -4 (REASON_CORRUPTED_PACKET)
0x10092294c:  mov      x0, x23
0x10092296c:  ret                                 ; Return immediately, packet discarded!
```

### 6.2 Investigation Answers

1. **Does `flags >= 0x0400` cause rejection?**  
   **YES.** The instruction `b.hs #0x1009228dc` unconditionally branches to the discard path, increments the dropped packet counter, and returns `-4`.
2. **Field Masking:**  
   The comparison applies to the **entire 16-bit flags word**. No bitwise masking is applied prior to `cmp w8, #0x400`.
3. **Comparison Sign:**  
   Strictly **unsigned** (`b.hs` = branch if higher or same).
4. **Valid Combinations:**  
   Any combination of lower 10 bits ($0 \le \text{flags} \le \text{0x03FF}$) passes this check. Subsequent code performs semantic checks on specific bits (e.g., rejecting `FLAG_CREATE_CHANNEL` on external nubs).
5. **Purpose:**  
   The check rejects datagrams containing unknown or unsupported high flag bits ($\ge \text{bit } 10$), reserving them for future protocol extensions.

---

## 7. Investigation E — Footer Parsing and Packet Processing Order

### 7.1 Native Footer Parsing Order

`Nub::processFilteredPacket` evaluates footers in strict reverse order from datagram tail backwards:

| Step | Native Address | Flag Bit Tested | Footer Field | Width | Handling / Error String |
|---|---|---|---|---|---|
| **1** | `0x100922970` | Bit 8 (`0x0100`) | **Checksum** | 4B (`<I`) | Tail 4 bytes zeroed, XOR verified (`0x1030a2e48`) |
| **2** | `0x10092297c` | Bit 1 (`0x0002`) | **Piggybacks** | 2B len + M | Decrements remaining by length (`0x1030a2efc`) |
| **3** | `0x100922980` | Bit 7 (`0x0080`) | **Indexed Channel**| 4B (`<I`) | Stores in `packet->channel_id_` (`0x1030a307f`) |
| **4** | `0x100922984` | Bit 3 (`0x0008`) | **On Channel** | 0B (Addr) | Address-based channel resolution |
| **5** | `0x100922994` | Bit 2 (`0x0004`) | **Piggybacked ACKs**| 1B + N*4B | Reads count byte + N sequence dwords (`0x1030a3231`) |
| **6** | `0x10092299c` | Bit 6 (`0x0040`) | **Sequence Number**| 4B (`<I`) | Stores in `packet->seq_num_` (`0x1030a33b3`) |
| **7** | `0x100922f70` | Bit 4 (`0x0010`) | **Reliability Req**| 0B | Verifies sequence number presence (`0x1030a3411`) |

### 7.2 Critical Discovery: Native vs. Gateway Flag Bit Discrepancy

A direct comparison between native disassembly and `phase6B_8_local_gateway/packet_parser.py` exposes a discrepancy in bit positions:

```python
# Discrepancy Comparison:
Feature                     Native Bit (Disassembly)        Gateway Enum (packet_parser.py)
-------------------------------------------------------------------------------------------
FLAG_CREATE_CHANNEL         Bit 9 (0x0200, VA 0x100923208)   Bit 0 (0x0001)
FLAG_HAS_PIGGYBACKS         Bit 1 (0x0002, VA 0x10092297c)   Bit 1 (0x0002) [MATCH]
FLAG_HAS_ACKS               Bit 2 (0x0004, VA 0x100922994)   Bit 3 (0x0008)
FLAG_ON_CHANNEL             Bit 3 (0x0008, VA 0x100922984)   Bit 5 (0x0020)
FLAG_IS_RELIABLE            Bit 4 (0x0010, VA 0x100922f70)   (Not mapped as discrete footer)
FLAG_HAS_SEQUENCE_NUMBER    Bit 6 (0x0040, VA 0x10092299c)   Bit 2 (0x0004)
FLAG_INDEXED_CHANNEL        Bit 7 (0x0080, VA 0x100922980)   Bit 7 (0x0080) [MATCH]
FLAG_HAS_CHECKSUM           Bit 8 (0x0100, VA 0x100922970)   Bit 8 (0x0100) [MATCH]
```

**Impact Assessment:**  
The synthetic gateway and synthetic client are internally self-consistent because both use `MercuryPacketFlags`. However, datagrams generated by the synthetic gateway will **not** be understood correctly by a physical native client, because the native client will interpret `0x0004` as ACKs (instead of Sequence Number) and `0x0001` as an unhandled flag.

---

## 8. Investigation F — Independent Golden Vector Verification

Both test vectors from Phase 6.2B.8.1 were re-evaluated in `phase6B_8_2_audit/audit_golden_vectors.py` using fixed literal golden constants and independent mathematical functions.

### 8.1 Vector 1 Audit: Channel 1 Initialization Request
- **Raw Input:** 65 bytes (`flags = 0x0185`, `seq = 1`, `chan = 1`, JSON payload 51 bytes).
- **Independent 32-bit XOR Checksum:** `0x034616a1` (Recalculated independently: 100% MATCH).
- **Independent Padding:** `pad_len = 8 - (65 % 8) = 7` bytes (Trailer: `0x07`, Padded length: 72 bytes).
- **Blowfish PBC Ciphertext (9 Blocks):**
  - Expected: `8aff37d58113b1a118aac47447b3722eb6a458cd99c422edbc26534e6dde6eeb2993ef333f5a7096f9287dca9ed23679b5829c275d42143e0f246c5997465409e0f6923d63f0cdbf`
  - Reconstructed: `8aff37d58113b1a118aac47447b3722eb6a458cd99c422edbc26534e6dde6eeb2993ef333f5a7096f9287dca9ed23679b5829c275d42143e0f246c5997465409e0f6923d63f0cdbf`
  - **Verdict:** **BIT-FOR-BIT IDENTICAL MATCH**.

### 8.2 Vector 2 Audit: Application Message on Channel 1
- **Raw Input:** 39 bytes (`flags = 0x01A4`, `seq = 2`, `chan = 1`, payload 25 bytes).
- **Independent 32-bit XOR Checksum:** `0x043f1eab` (Recalculated independently: 100% MATCH).
- **Independent Padding:** `pad_len = 8 - (39 % 8) = 1` byte (Trailer: `0x01`, Padded length: 40 bytes).
- **Blowfish PBC Ciphertext (5 Blocks):**
  - Expected: `74f26a69d5ba69f6953bf0853339d0e9c8a2ad12404d3c2fe833d666c0acb182f7488878f17fa456`
  - Reconstructed: `74f26a69d5ba69f6953bf0853339d0e9c8a2ad12404d3c2fe833d666c0acb182f7488878f17fa456`
  - **Verdict:** **BIT-FOR-BIT IDENTICAL MATCH**.

### 8.3 Vector Independence Confirmation
- Neither test vector was generated dynamically from gateway code.
- Verification relied strictly on pure Python standard libraries and raw `Blowfish.ECB` primitives from `cryptography.hazmat`.

---

## 9. Investigation G — Historical Integrity Results

All historical artifacts and project directories were audited without modification:

| Artifact | Historical SHA-256 Record | Current Computed SHA-256 | Status |
|---|---|---|---|
| **Original IPA** (`RoS-Legacy-iOS.ipa`) | `d1f638ad49387a0bca3b5e391799e07faa12f3dca7db32f9fd22f07db14e8c55` | `d1f638ad49387a0bca3b5e391799e07faa12f3dca7db32f9fd22f07db14e8c55` | **PRISTINE MATCH** |
| **Mach-O Binary** (`client`) | `51e63bfea67e62f8adf32b0664148576725832761c897216cc526f8814123dd6` | `51e63bfea67e62f8adf32b0664148576725832761c897216cc526f8814123dd6` | **PRISTINE MATCH** |
| **Phase 6.2B.7.1 Report** | (Historical hash unindexed) | `f08d11a345f877f32a5e04c97393c6da9743a1d170d6aa2cafd48ef740bacde3` | Unmodified |
| **Phase 6.2B.8 Gateway Code** | (Historical hash unindexed) | Multi-file hash verified | Unmodified |
| **Phase 6.2B.8.1 Audit Code** | (Historical hash unindexed) | `e94f6ed68f2149045aa8f8d22e6459a49bf61c703e49cd95baf09da7e89d8474` | Unmodified |
| **Backend Source** (`ros-private-server/`) | Timestamps: 11/9/2026–11/11/2026 | Timestamps: Unchanged | Unmodified |

---

## 10. Evidence Classification Table

| Protocol Feature / Assertion | Primary Supporting Reference | Evidence Classification |
|---|---|---|
| **Blowfish Block Cipher Primitive** | VA `0x1000ab248` (`BF_ecb_encrypt`) | **VERIFIED BY NATIVE EVIDENCE** |
| **Plaintext Block Chaining (PBC)** | VA `0x10091c82c` (`mov x8, x27`) & `0x10091c978` | **VERIFIED BY NATIVE EVIDENCE** |
| **Stateless Zero IV Lifecycle** | VA `0x10091c7f4` (`mov x8, #0`) & `0x10091c968` | **VERIFIED BY NATIVE EVIDENCE** |
| **Single-Byte Trailer Padding** | VA `0x10091c7c4` (`sturb w8, [x9, #-1]`) | **VERIFIED BY NATIVE EVIDENCE** |
| **Padding Validation Policy (L <= 8)** | VA `0x10091c9e0` (`cmp w21, #8; ccmp w9, w21, #0, ls`) | **VERIFIED BY NATIVE EVIDENCE** |
| **Zero-Slack Padding Hygiene** | `phase6B_8_local_gateway/protocol_engine.py` | **SYNTHETIC IMPLEMENTATION ONLY** |
| **32-bit SIMD XOR Checksum** | VA `0x100922bfc` (`eor v0.16b`) & `0x100922c38` | **VERIFIED BY NATIVE EVIDENCE** |
| **Checksum In-Place Zeroing** | VA `0x100922a54` (`str wzr, [x10]`) | **VERIFIED BY NATIVE EVIDENCE** |
| **Checksum Post-Decryption Timing** | VA `0x10091ca54` $\to$ `0x100927a0c` $\to$ `0x100922860` | **VERIFIED BY NATIVE EVIDENCE** |
| **Flags Upper Bound (< 0x0400)** | VA `0x100922898` (`cmp w8, #0x400; b.hs`) | **VERIFIED BY NATIVE EVIDENCE** |
| **Reverse Footer Unpacking Order** | VA `0x100922970`–`0x100922f70` | **VERIFIED BY NATIVE EVIDENCE** |
| **Native Flag Bits (Seq=0x40, ACK=0x04)** | VA `0x100922994`, `0x10092299c`, `0x100923208` | **VERIFIED BY NATIVE EVIDENCE** |
| **Gateway Flag Bits (Seq=0x04, ACK=0x08)** | `phase6B_8_local_gateway/packet_parser.py` | **CONTRADICTED (SYNTHETIC CHOICE)** |
| **Golden Datagram 1 Reproduction** | `phase6B_8_2_audit/audit_golden_vectors.py` | **VERIFIED BY INDEPENDENT SYNTHETIC CALCULATION** |
| **Golden Datagram 2 Reproduction** | `phase6B_8_2_audit/audit_golden_vectors.py` | **VERIFIED BY INDEPENDENT SYNTHETIC CALCULATION** |
| **Pre-Shared Static Key Registry** | `phase6B_8_local_gateway/config.py` | **EXPERIMENTAL DESIGN CHOICE** |
| **UTF-8 JSON Payload Framing** | `phase6B_8_local_gateway/synthetic_client.py` | **SYNTHETIC IMPLEMENTATION ONLY** |

---

## 11. Remaining Uncertainties

1. **Flag Bit Alignment Remediation:**  
   The synthetic gateway currently operates using an experimental flag mapping. Alignment with native bit positions (Bit 6 for Sequence Number, Bit 2 for ACKs, Bit 9 for Channel Creation, Bit 3 for On-Channel) must be planned for client interoperability.
2. **BigWorld Binary Bundle Format:**  
   The native payload structure contained between Header Offset 2 and the footers consists of BigWorld message bundles (message IDs, variable-length parameters, entity methods) rather than JSON text.
3. **Dynamic Handshake Protocol:**  
   The dynamic session key negotiation (via RSA-OAEP public-key exchange) remains to be reconciled with the client's login state machine.

---

## 12. Recommended Next Research Phase

**Phase 6.2B.9 — Native Protocol Harmonization & Handshake Reverse Engineering:**
1. Update synthetic gateway flag definitions to conform to native ARM64 bit positions (`0x0040` for Sequence Number, `0x0004` for ACKs, `0x0200` for Channel Creation).
2. Disassemble client handshake routines (`LoginConnection::sendLogin`, RSA public-key loading) to map the dynamic session key exchange.
3. Disassemble BigWorld bundle deserialization (`Bundle::unpack`, `MessageFilter`) to identify native entity login message structures.

---

## 13. Stop Condition & Approval

Under strict protocol guidelines:
- **No code fixes or modifications were applied.**
- **No network traffic was initiated.**
- **No database was touched.**
- **The original IPA and binary remain completely unmodified.**

All Phase 6.2B.8.2 objectives are complete. Awaiting explicit user instruction before proceeding.
