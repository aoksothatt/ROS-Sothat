# Native Mercury Flag Specification
## NetEase BigWorld Engine (Rules of Survival Legacy iOS Client)

**Document Classification:** NATIVE ARM64 INSTRUCTION RECONSTRUCTION  
**Target Executable:** `extracted/Payload/client.app/client` (Mach-O ARM64, SHA-256: `51e63bfea67e62f8adf32b0664148576725832761c897216cc526f8814123dd6`)  
**Audit Phase:** Phase 6.2B.8.3  
**Status:** COMPLETE & VERIFIED BY NATIVE EVIDENCE  

---

## 1. Overview and Header Flags Architecture

In the native NetEase BigWorld Mercury UDP transport protocol, every datagram begins with a **16-bit Header Flags word** (little-endian uint16, `<H`) located at **Offset 0** of the decrypted packet buffer (`packet_data + 0x00`).

```
+===================================================================================================+
|                              16-BIT NATIVE MERCURY HEADER FLAGS WORD                              |
+---------------------------------------------------------------------------------------------------+
| Bit 15 | Bit 14 | Bit 13 | Bit 12 | Bit 11 | Bit 10 |  Bit 9  |  Bit 8  |  Bit 7  |  Bit 6      |
|                                                     | CREATE  | CHECKSUM| INDEXED | SEQUENCE    |
|             RESERVED / ILLEGAL (>= 0x0400)          | CHANNEL |         | CHANNEL | NUMBER      |
|                     Must be 0                       | (0x0200)| (0x0100)| (0x0080)| (0x0040)    |
+-----------------------------------------------------+---------+---------+---------+-------------+
|  Bit 5      |  Bit 4       |  Bit 3       |  Bit 2       |  Bit 1        |  Bit 0             |
|  FRAGMENTS  |  IS_RELIABLE |  ON_CHANNEL  |  ACKS        |  PIGGYBACKS   |  REQUESTS          |
|  (0x0020)   |  (0x0010)    |  (0x0008)    |  (0x0004)    |  (0x0002)     |  (0x0001)          |
+=============+==============+==============+==============+===============+====================+
```

### Architectural Properties:
1. **Upper-Bound Check:** Instruction `0x100922898: cmp w8, #0x400` followed by `b.hs #0x1009228dc` strictly enforces that bits 10–15 must be zero ($0 \le \text{flags} < \text{0x0400}$). Any packet with $\text{flags} \ge \text{0x0400}$ is discarded immediately as corrupted.
2. **Reverse Footer Unwinding:** Optional footers signaled by these flag bits are unpacked backwards from the datagram tail towards the payload start (Offset 2).
3. **Decryption Ordering:** All flag parsing and footer unwinding occurs strictly **after** Blowfish PBC decryption and single-byte wastage count unpadding.

---

## 2. Complete Native Flag Enumeration

| Bit Index | Mask (Hex) | Canonical Native Identifier | Presence | Footer Width | Wire Format | Parsing Location | Primary Function |
|---|---|---|---|---|---|---|---|
| **Bit 0** | `0x0001` | `FLAG_HAS_REQUESTS` | Optional | 2 Bytes | `<H` (uint16) | `Nub::processPacket` | First request offset in bundle |
| **Bit 1** | `0x0002` | `FLAG_HAS_PIGGYBACKS` | Optional | 2B len + M data | `<h` (int16) + raw | `Nub::processFilteredPacket` | Piggybacked sub-packet bundle |
| **Bit 2** | `0x0004` | `FLAG_HAS_ACKS` | Optional | 1B cnt + N*4B | `<B` + array of `<I` | `Nub::processFilteredPacket` | Cumulative/selective sequence ACKs |
| **Bit 3** | `0x0008` | `FLAG_ON_CHANNEL` | Optional | 0 Bytes | (Address lookup) | `Nub::processFilteredPacket` | Regular address-based channel |
| **Bit 4** | `0x0010` | `FLAG_IS_RELIABLE` | Optional | 0 Bytes | (Flag only) | `Nub::processFilteredPacket` | Requires reliable delivery & sequence |
| **Bit 5** | `0x0020` | `FLAG_HAS_FRAGMENTS` | Optional | 8 Bytes | 2x `<I` (uint32) | `Nub::processPacket` | Bundle fragment spec (`fragBegin`, `fragEnd`) |
| **Bit 6** | `0x0040` | `FLAG_HAS_SEQUENCE_NUMBER` | Optional | 4 Bytes | `<I` (uint32) | `Nub::processFilteredPacket` | Packet transmission sequence number |
| **Bit 7** | `0x0080` | `FLAG_INDEXED_CHANNEL` | Optional | 4 Bytes | `<I` (uint32) | `Nub::processFilteredPacket` | Indexed Channel ID |
| **Bit 8** | `0x0100` | `FLAG_HAS_CHECKSUM` | Optional | 4 Bytes | `<I` (uint32) | `Nub::processFilteredPacket` | 32-bit XOR datagram checksum |
| **Bit 9** | `0x0200` | `FLAG_CREATE_CHANNEL` | Optional | 0 Bytes | (State transition) | `Nub::processFilteredPacket` | Channel creation & activation handshake |
| **Bits 10–15**| `0x0400`–`0x8000`| `RESERVED_ILLEGAL_FLAGS` | **FORBIDDEN**| N/A | N/A | `Nub::processFilteredPacket` | Rejected with `bad flags %x` error |

---

## 3. Detailed Flag Specifications and Native ARM64 Disassembly

### Bit 0 (`0x0001`): `FLAG_HAS_REQUESTS`
- **Definition:** Indicates that the message bundle contains one or more request messages requiring reply tracking. A 2-byte little-endian uint16 (`<H`) First Request Offset footer is appended to the packet.
- **Receive Instruction Evidence (`Nub::processPacket`):**
  ```assembly
  0x100923904:  ldrh     w8, [x2, #0x60]            ; Load packet Flags word
  0x100923908:  tbz      w8, #0, #0x100923948       ; If bit 0 is 0, skip request offset
  0x10092390c:  ldrh     w9, [x22, #0x1a]           ; Remaining length
  0x100923910:  cmp      w9, #4                     ; Must have >= 4 bytes (header + offset)
  0x100923914:  b.hs     #0x100923928
  0x100923928:  sub      w9, w9, #2                 ; remaining -= 2
  0x10092392c:  strh     w9, [x22, #0x1a]
  0x100923930:  ldrh     w10, [x22, #0x1c]          ; footers length
  0x100923934:  add      w10, w10, #2               ; footers += 2
  0x100923938:  strh     w10, [x22, #0x1c]
  0x10092393c:  add      x9, x22, w9, uxth
  0x100923940:  ldrh     w9, [x9, #0x60]            ; Load 2-byte First Request Offset
  0x100923944:  strh     w9, [x22, #0x20]           ; packet->firstRequestOffset_ = w9
  ```
- **Send Instruction Evidence:**
  ```assembly
  0x100917258:  ldrh     w9, [x8, #0x60]
  0x10091725c:  orr      w9, w9, #1                 ; Set Bit 0
  0x100917260:  strh     w9, [x8, #0x60]
  ```
- **Error String Reference:** `0x1030a34d8`: `"Nub::processPacket( %s ): Not enough data for first request offset (%d bytes left)\n"`

---

### Bit 1 (`0x0002`): `FLAG_HAS_PIGGYBACKS`
- **Definition:** Signals that a piggybacked bundle from another channel or sub-stream is appended to the packet tail. Contains a 2-byte signed length ($M$) followed by $M$ bytes of bundle data.
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x10092297c:  tbnz     w8, #1, #0x1009229fc       ; If bit 1 set, branch to piggyback unpacker
  ...
  0x1009229fc:  cmp      x23, #0
  0x100922a00:  sub      x8, x29, #0x59
  0x100922a04:  csel     x8, x8, x23, eq
  0x100922a08:  stp      x23, x8, [sp, #0x28]
  0x100922a0c:  and      w8, w9, #0xffff
  0x100922a10:  cmp      w8, #4                     ; Must have at least 4 bytes
  0x100922a14:  b.hs     #0x100922a84
  ```
- **Send Instruction Evidence:**
  ```assembly
  0x10092b524:  mov      w8, #0x102                 ; FLAG_HAS_CHECKSUM | FLAG_HAS_PIGGYBACKS
  0x10092b528:  mov      w9, #0x100                 ; FLAG_HAS_CHECKSUM only
  0x10092b52c:  csel     w1, w9, w8, ne
  ```
- **Error String References:**
  - `0x1030a2efc`: `"Nub::processFilteredPacket( %s ): Not enough data for piggyback length (%d bytes left)\n"`
  - `0x1030a2f54`: `"Nub::processFilteredPacket( %s ): Packet too small to contain piggyback message of length %d (only %d bytes remaining)\n"`

---

### Bit 2 (`0x0004`): `FLAG_HAS_ACKS`
- **Definition:** Signals the presence of piggybacked ACKs. Unpacks a 1-byte count ($N$) followed by $N \times 4$ bytes of little-endian uint32 sequence numbers being acknowledged.
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x100922994:  tbnz     w8, #2, #0x100922e4c       ; If bit 2 set, unpack ACKs
  ...
  0x100922e4c:  ldrh     w9, [x19, #0x1a]           ; Remaining length
  0x100922e50:  cmp      w9, #2                     ; Must have >= 2 bytes
  0x100922e54:  b.hi     #0x100922ee4
  ...
  0x100922ee4:  sub      w9, w9, #1                 ; remaining -= 1
  0x100922ee8:  strh     w9, [x19, #0x1a]
  0x100922eec:  ldrh     w10, [x19, #0x1c]          ; footers length
  0x100922ef0:  add      w10, w10, #1               ; footers += 1
  0x100922ef4:  strh     w10, [x19, #0x1c]
  0x100922ef8:  add      x10, x19, w9, uxth
  0x100922efc:  ldrb     w10, [x10, #0x60]          ; Load 1-byte ACK count
  0x100922f00:  strb     w10, [x19, #0x30]          ; packet->ack_count_ = w10
  0x100922f04:  cbz      w10, #0x1009230f8          ; If count == 0, error!
  0x100922f08:  lsl      w23, w10, #2               ; bytes needed = count * 4
  ```
- **Send Instruction Evidence:**
  ```assembly
  0x100917cf4:  ldrb     w9, [x8, #0x30]            ; packet->ack_count_
  0x100917cf8:  add      w9, w9, #1                 ; Increment ACK count
  0x100917cfc:  strb     w9, [x8, #0x30]
  0x100917d04:  ldrh     w9, [x8, #0x60]
  0x100917d08:  orr      w9, w9, #4                 ; Set Bit 2 (FLAG_HAS_ACKS)
  0x100917d0c:  strh     w9, [x8, #0x60]
  ```
- **Error String References:**
  - `0x1030a3231`: `"Nub::processFilteredPacket( %s ): Not enough data for ack count footer (%d bytes left)\n"`
  - `0x1030a3289`: `"Nub::processFilteredPacket( %s ): Packet with FLAG_HAS_ACKS had 0 acks\n"`
  - `0x1030a32d1`: `"Nub::processFilteredPacket( %s ): Not enough footers for %d acks (have %d bytes but need %d)\n"`

---

### Bit 3 (`0x0008`): `FLAG_ON_CHANNEL`
- **Definition:** Marks the packet as transmitted over an address-based (regular, unindexed) channel. The client looks up the local channel using the remote socket endpoint IP and port.
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x1009228a8:  tbnz     w8, #3, #0x1009228b8       ; Checks bit 3 for reliable channel counter
  0x100922984:  tbnz     w8, #3, #0x100922c88       ; Resolves channel via remote address map
  ...
  0x100922c88:  ldr      x10, [x21, #0x41f8]        ; nub->channelsByAddress_ map
  0x100922ce0:  ldur     x15, [x10, #0x24]          ; compare remote IP
  0x100922ce4:  ldur     x16, [x20, #4]
  0x100922cf8:  ldur     x15, [x10, #0x2c]          ; compare remote port
  0x100922cfc:  ldur     x16, [x20, #0xc]
  0x100923120:  tbnz     w8, #3, #0x1009233c8       ; Branch if regular channel
  ```
- **Error String Reference:** `0x1030a3127`: `"Nub::processFilteredPacket( %s ): Dropping packet due to absence of local channel\n"`

---

### Bit 4 (`0x0010`): `FLAG_IS_RELIABLE`
- **Definition:** Indicates that the packet demands reliable transmission. Requires that the packet also carries a sequence number (`FLAG_HAS_SEQUENCE_NUMBER` = Bit 6).
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x100922f70:  tbnz     w8, #4, #0x100923090       ; If bit 4 set, validate reliability
  ...
  0x100923090:  ldr      w2, [x19, #0x48]           ; Load packet sequence number
  0x100923094:  mov      w8, #0x10000000            ; SEQ_NULL / unsequenced marker (0x10000000)
  0x100923098:  cmp      w2, w8                     ; Has valid sequence number?
  0x10092309c:  b.ne     #0x1009230d0               ; Valid -> continue
  0x1009230b0:  add      x0, x0, #0x411             ; Error: "Dropping packet due to illegal request for reliability..."
  0x1009230b4:  bl       #0x101b634c0
  0x1009230b8:  b        #0x10092331c               ; Discard packet!
  ```
- **Error String References:**
  - `0x1030a3411`: `"Nub::processFilteredPacket( %s ): Dropping packet due to illegal request for reliability without related sequence number\n"`
  - `0x1030a348b`: `"Nub::processFilteredPacket( %s ): Dropping illegal once-off-reliable packet\n"`

---

### Bit 5 (`0x0020`): `FLAG_HAS_FRAGMENTS`
- **Definition:** Signals that the packet carries a bundle fragment specification. Appends an 8-byte footer containing two 32-bit little-endian dwords: `fragBegin` (`<I`) and `fragEnd` (`<I`).
- **Receive Instruction Evidence (`Nub::processPacket`):**
  ```assembly
  0x100923948:  tbnz     w8, #5, #0x100923974       ; If bit 5 set, branch to fragment spec unpacker
  ...
  0x100923974:  ldrh     w9, [x22, #0x1a]           ; Remaining length
  0x100923978:  cmp      w9, #9                     ; Must have >= 10 bytes
  0x10092397c:  b.hi     #0x100923990
  ...
  0x100923990:  sub      w10, w9, #4                ; offset of fragEnd
  0x10092399c:  add      x12, x22, #0x60
  0x1009239a0:  ldr      w10, [x12, x10]            ; Load fragEnd (4 bytes uint32)
  0x1009239a4:  sub      w9, w9, #8                 ; remaining -= 8
  0x1009239a8:  strh     w9, [x22, #0x1a]
  0x1009239ac:  add      w11, w11, #8               ; footers += 8
  0x1009239b0:  strh     w11, [x22, #0x1c]
  0x1009239b8:  ldr      w9, [x12, x9]              ; Load fragBegin (4 bytes uint32)
  0x1009239bc:  stp      w9, w10, [x22, #0x54]      ; packet->fragBegin_ = w9, fragEnd_ = w10
  0x1009239c0:  sub      w21, w10, w9               ; fragment count = fragEnd - fragBegin + 1
  ```
- **Send Instruction Evidence:**
  ```assembly
  0x100918040:  ldrh     w10, [x8, #0x1c]
  0x100918044:  add      w10, w10, #8               ; Add 8 bytes to footers
  0x100918048:  strh     w10, [x8, #0x1c]
  ```
- **Error String References:**
  - `0x1030a352c`: `"Nub::processPacket( %s ): Not enough footers for fragment spec (have %d bytes but need %d)\n"`
  - `0x1030a3588`: `"Nub::processPacket( %s ): Dropping fragment due to illegal bundle fragment count (%d)\n"`
  - `0x1030a3715`: `"Nub::processPacket( %s ): Mangled fragment footers, lastFragment(%d) != p->fragEnd()(%d)\n"`

---

### Bit 6 (`0x0040`): `FLAG_HAS_SEQUENCE_NUMBER`
- **Definition:** Appends a 4-byte little-endian uint32 (`<I`) sequence number footer to the datagram tail.
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x10092299c:  tbz      w8, #6, #0x100922f70       ; If bit 6 is 0, skip sequence number
  0x1009229a0:  ldrh     w9, [x19, #0x1a]           ; Remaining length
  0x1009229a4:  cmp      w9, #6                     ; Must have >= 6 bytes (flags + seq_num)
  0x1009229a8:  b.hs     #0x100922f50
  ...
  0x100922f50:  sub      w9, w9, #4                 ; remaining -= 4
  0x100922f54:  strh     w9, [x19, #0x1a]
  0x100922f58:  ldrh     w10, [x19, #0x1c]          ; footers length
  0x100922f5c:  add      w10, w10, #4               ; footers += 4
  0x100922f60:  strh     w10, [x19, #0x1c]
  0x100922f64:  add      x9, x19, w9, uxth
  0x100922f68:  ldr      w9, [x9, #0x60]            ; Load 4-byte Sequence Number
  0x100922f6c:  str      w9, [x19, #0x48]           ; packet->seq_num_ = w9
  ```
- **Send Instruction Evidence:**
  ```assembly
  0x100917fcc:  ldrh     w9, [x8, #0x60]
  0x100917fd0:  orr      w9, w9, #0x60              ; Sets Bit 6 (SeqNum) and Bit 5 (Fragments)
  0x100917fd4:  strh     w9, [x8, #0x60]
  ...
  0x100918050:  ldrh     w10, [x8, #0x1c]
  0x100918054:  add      w10, w10, #4               ; Add 4 bytes to footers
  0x100918058:  strh     w10, [x8, #0x1c]
  ```
- **Error String Reference:** `0x1030a33b3`: `"Nub::processFilteredPacket( %s ): Not enough data for sequence number footer (%d bytes left)\n"`

---

### Bit 7 (`0x0080`): `FLAG_INDEXED_CHANNEL`
- **Definition:** Marks the packet as transmitted over an indexed channel. Appends a 4-byte little-endian uint32 (`<I`) Channel ID footer to the packet tail.
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x100922980:  tbnz     w8, #7, #0x100922dc0       ; If bit 7 set, branch to indexed channel unpacker
  ...
  0x100922dc0:  ldr      x0, [x21, #0x4208]         ; nub->channelsById_ map
  0x100922dc4:  cbz      x0, #0x100922e28           ; Error if no finder registered
  0x100922dc8:  ldrh     w8, [x19, #0x1a]           ; Remaining length
  0x100922dcc:  cmp      w8, #6                     ; Must have >= 6 bytes
  0x100922dd0:  b.lo     #0x100922dfc
  0x100922dd4:  sub      w10, w8, #4                ; remaining -= 4
  0x100922dd8:  strh     w10, [x19, #0x1a]
  0x100922ddc:  ldrh     w9, [x19, #0x1c]           ; footers length
  0x100922de0:  add      w11, w9, #4                ; footers += 4
  0x100922de4:  strh     w11, [x19, #0x1c]
  0x100922de8:  add      x11, x19, w10, uxth
  0x100922dec:  ldr      w1, [x11, #0x60]           ; Load 4-byte Channel ID
  0x100922df0:  str      w1, [x19, #0x4c]           ; packet->channel_id_ = w1
  ```
- **Error String References:**
  - `0x1030a3027`: `"Nub::processFilteredPacket( %s ): Got indexed channel packet with no finder registered\n"`
  - `0x1030a307f`: `"Nub::processFilteredPacket( %s ): Not enough data for indexed channel footer (%d bytes left)\n"`
  - `0x1030a30dd`: `"Nub::processFilteredPacket( %s ): Couldn't get indexed channel for id %d\n"`

---

### Bit 8 (`0x0100`): `FLAG_HAS_CHECKSUM`
- **Definition:** Appends a 4-byte little-endian uint32 (`<I`) checksum to the absolute tail of the datagram.
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x100922970:  tbnz     w8, #8, #0x1009229d0       ; If bit 8 set, branch to checksum validator
  ...
  0x100922a38:  sub      w9, w9, #4                 ; remaining -= 4
  0x100922a3c:  strh     w9, [x19, #0x1a]
  0x100922a40:  add      w10, w10, #4               ; footers += 4
  0x100922a44:  strh     w10, [x19, #0x1c]
  0x100922a48:  add      x10, x19, w9, uxth
  0x100922a4c:  ldr      w11, [x10, #0x60]!         ; Load uint32 checksum from packet tail
  0x100922a50:  str      w11, [x19, #0x5c]          ; packet->checksum_ = w11
  0x100922a54:  str      wzr, [x10]                 ; ZERO CHECKSUM FIELD IN-PLACE
  ...
  0x100922c00:  eor      v0.16b, v2.16b, v0.16b     ; 32-bit NEON vector XOR sum
  0x100922c44:  str      w11, [x10]                 ; RESTORE SAVED CHECKSUM
  0x100922c48:  cmp      w22, w11                   ; Compare computed vs stored checksum
  0x100922c4c:  b.eq     #0x100922974               ; If matching, proceed to unpack footers
  ```
- **Error String References:**
  - `0x1030a2e48`: `"Nub::processFilteredPacket( %s ): Packet too short (%d bytes) for checksum!\n"`
  - `0x1030a2e95`: `"Nub::processFilteredPacket( %s ): Packet (flags %hx, size %d) failed checksum (wanted %08x, got %08x)\n"`

---

### Bit 9 (`0x0200`): `FLAG_CREATE_CHANNEL`
- **Definition:** Signals that the packet establishes or activates a communication channel. No discrete footer is added; the flag controls channel state transitions.
- **Receive Instruction Evidence (`Nub::processFilteredPacket`):**
  ```assembly
  0x1009228b8:  tbz      w8, #9, #0x100922904       ; Check bit 9 on external nub
  ...
  ; Channel validation & activation check:
  0x1009231fc:  ldrb     w9, [x22, #0x105]          ; channel->isWantingCreateChannel
  0x100923204:  cbz      w9, #0x100923354           ; If not wanting creation, continue
  0x100923208:  tbnz     w8, #9, #0x100923360       ; If bit 9 set, activate channel!
  ; If bit 9 NOT set on channel wanting creation:
  0x10092321c:  adrp     x0, #0x1030a3000
  0x100923220:  add      x0, x0, #0x1cb             ; Error: "Dropping packet on channel wanting FLAG_CREATE_CHANNEL..."
  0x100923224:  bl       #0x101b634c0
  0x100923228:  b        #0x1009231cc               ; Discard packet!
  ...
  ; Channel activation branch:
  0x100923360:  mov      x26, x23
  0x100923364:  mov      w25, #0
  0x100923368:  strb     wzr, [x22, #0x105]         ; CLEARS isWantingCreateChannel -> ACTIVE!
  0x10092336c:  b        #0x100922994               ; Proceed to ACKs & Sequence Number
  ```
- **Error String References:**
  - `0x1030a2db5`: `"Nub::processFilteredPacket( %s ): Got FLAG_CREATE_CHANNEL on external nub\n"`
  - `0x1030a31cb`: `"Nub::processFilteredPacket( %s ): Dropping packet on channel wanting FLAG_CREATE_CHANNEL (flags: %x)\n"`

---

### Bits 10–15 (`0x0400`–`0x8000`): Reserved / Bad Flags
- **Definition:** Any flag value with bit 10 or higher set is illegal.
- **Instruction Evidence:**
  ```assembly
  0x100922894:  ldrh     w8, [x28, #0x60]!          ; Load uint16 Flags at Offset 0
  0x100922898:  cmp      w8, #0x400                 ; Compare unsigned flags against 0x0400
  0x10092289c:  b.hs     #0x1009228dc               ; If >= 0x0400, branch to error handler
  ...
  0x1009228dc:  ...
  0x1009228f8:  adrp     x0, #0x1030a2000
  0x1009228fc:  add      x0, x0, #0xd6c             ; "Nub(%p)::processFilteredPacket( %s ): received packet with bad flags %x\n"
  0x100922900:  b        #0x100922938
  0x10092293c:  ldr      w8, [x27, #0x28]           ; nub->dropped_packets_counter
  0x100922940:  add      w8, w8, #1                 ; Counter++
  0x100922944:  str      w8, [x27, #0x28]
  0x100922948:  mov      w23, #-4                   ; Return -4 (REASON_CORRUPTED_PACKET)
  0x10092296c:  ret
  ```

---

## 4. Reverse Footer Layout and Unwinding Order

When all footers are present, the datagram is organized from tail backwards:

```
Tail Offset:
  [Tail - 4 .. Tail - 1]     : Checksum (4 Bytes, Bit 8: 0x0100)
  [Tail - 4 - M .. Tail - 5] : Piggybacks Data (M Bytes, Bit 1: 0x0002)
  [Tail - 4 - M - 2 .. ]     : Piggybacks Length (2 Bytes int16, Bit 1: 0x0002)
  [Tail - ... - 4 .. ]       : Indexed Channel ID (4 Bytes uint32, Bit 7: 0x0080)
  [Tail - ... - N*4 .. ]     : ACKs Sequence Array (N*4 Bytes, Bit 2: 0x0004)
  [Tail - ... - 1 .. ]       : ACK Count (1 Byte uint8, Bit 2: 0x0004)
  [Tail - ... - 4 .. ]       : Sequence Number (4 Bytes uint32, Bit 6: 0x0040)
  [Tail - ... - 8 .. ]       : Fragments Spec (8 Bytes: fragBegin 4B + fragEnd 4B, Bit 5: 0x0020)
  [Tail - ... - 2 .. ]       : First Request Offset (2 Bytes uint16, Bit 0: 0x0001)
Head Offset:
  [Offset 0x0000 .. 0x0001]  : 16-bit Header Flags Word
  [Offset 0x0002 .. Tail - F]: Message Bundle Payload Body
```

---

## 5. Summary of Native vs. Synthetic Flag Enumeration

| Protocol Semantic | Native ARM64 Bit | Native Mask | Gateway Enum (`packet_parser.py`) | Status | Impact on Original Client |
|---|---|---|---|---|---|
| **First Request Offset** | **Bit 0** | `0x0001` | `0x0040` (Bit 6) | **MISMATCH** | Incompatible request handling |
| **Piggybacked Sub-packet** | **Bit 1** | `0x0002` | `0x0002` (Bit 1) | **MATCH** | Fully compatible |
| **Piggybacked ACKs** | **Bit 2** | `0x0004` | `0x0008` (Bit 3) | **MISMATCH** | Client misinterprets ACKs |
| **On Channel (Address)** | **Bit 3** | `0x0008` | `0x0020` (Bit 5) | **MISMATCH** | Client drops channel routing |
| **Reliability Required** | **Bit 4** | `0x0010` | (Not defined) | **MISSING** | Reliability verification fails |
| **Bundle Fragments** | **Bit 5** | `0x0020` | (Assigned to On-Channel)| **MISMATCH** | Fragmented bundles unparseable |
| **Sequence Number** | **Bit 6** | `0x0040` | `0x0004` (Bit 2) | **MISMATCH** | Sequence tracking breaks |
| **Indexed Channel ID** | **Bit 7** | `0x0080` | `0x0080` (Bit 7) | **MATCH** | Fully compatible |
| **32-bit XOR Checksum** | **Bit 8** | `0x0100` | `0x0100` (Bit 8) | **MATCH** | Fully compatible |
| **Create Channel** | **Bit 9** | `0x0200` | `0x0001` (Bit 0) | **MISMATCH** | Channel activation fails |
| **Bad Flags Upper Bound** | **Bits 10–15** | `>= 0x0400` | `>= 0x0400` | **MATCH** | Fully compatible |
