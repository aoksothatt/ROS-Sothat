# Native Mercury Gateway Remediation Plan
## Detailed File-by-File Correction Specification
**Project:** ROS Sothat — Legacy iOS Client Private Server  
**Phase:** 6.2B.8.4 (Planning Only — Strict Read-Only)  
**Target Architecture:** ARM64 NetEase BigWorld Mercury UDP Protocol Engine  
**Target Codebase:** `phase6B_8_local_gateway/`  
**Reference Evidence:** `ros_phase6B_8_2_native_evidence_closure_report.md`, `ros_phase6B_8_3_native_flag_compatibility_audit_report.md`  

---

## 1. Executive Summary & Purpose

The purpose of this document is to specify the exact, file-by-file engineering modifications required to align the local synthetic Mercury UDP gateway (`phase6B_8_local_gateway/`) with the native ARM64 Mercury wire specification discovered during Phase 6.2B.8.2 and Phase 6.2B.8.3.

### What Stays Unchanged (100% Cryptographic Match):
- **Blowfish Plaintext Block Chaining (PBC):** The mathematical formulation $C_0 = E(P_0 \oplus 0)$ and $C_i = E(P_i \oplus P_{i-1})$ matches native ARM64 instructions at `0x10091c7f4` and `0x10091c82c`.
- **Single-Byte Trailer Padding:** The wastage count trailer $1 \le L \le 8$ at `buf[-1]` matches native instructions at `0x10091c7c4` and `0x10091c9e0`.
- **32-Bit SIMD XOR Checksum:** The 32-bit bitwise XOR reduction over 4-byte dwords with in-place zeroing at tail matches native NEON instructions at `0x100922a54`, `0x100922bfc`, and `0x100922c38`.
- **Localhost 127.0.0.1 Binding Controls:** Strict assertions in `config.py` preventing external or multi-homed exposure.

### What Must Be Remediated (Wire Protocol Incompatibilities):
1. **Flag Bit Allocations:** 5 header flag masks in `MercuryPacketFlags` are misallocated or inverted relative to native ARM64 checks, and 2 native flags (`FLAG_IS_RELIABLE` and `FLAG_HAS_FRAGMENTS`) are missing entirely.
2. **Footer Reverse Packing/Unpacking Order:** Inclusion of the 8-byte Fragment Spec footer (`FLAG_HAS_FRAGMENTS = 0x0020`) between Sequence Number and Request Offset.
3. **Channel Activation Handshake:** Updating incoming channel initiation logic to expect Bit 9 (`0x0200`) instead of Bit 0 (`0x0001`), simulating the native `isWantingCreateChannel` flag clearing (`strb wzr, [x22, #0x105]`).
4. **28-Bit Sequence Arithmetic:** Incorporating native 28-bit sequence difference masking (`(seq - expected) & 0x0FFFFFFF`) with half-window threshold (`0x08000000`).
5. **Piggybacked ACK Queueing:** Aligning the channel ACK queue lifecycle with native `Channel::queueAckForPacket`.

---

## 2. File-by-File Remediation Plan

---

### File 1: `phase6B_8_local_gateway/packet_parser.py`

#### 1. Current Code Analysis (Lines 24–38)
```python
class MercuryPacketFlags:
    FLAG_CREATE_CHANNEL      = 0x0001  # INCORRECT: Native is 0x0200 (Bit 9)
    FLAG_HAS_PIGGYBACKS      = 0x0002  # CORRECT: Native is 0x0002 (Bit 1)
    FLAG_HAS_SEQUENCE_NUMBER = 0x0004  # INCORRECT: Native is 0x0040 (Bit 6)
    FLAG_HAS_ACKS            = 0x0008  # INCORRECT: Native is 0x0004 (Bit 2)
    FLAG_ON_CHANNEL          = 0x0020  # INCORRECT: Native is 0x0008 (Bit 3)
    FLAG_HAS_REQUESTS        = 0x0040  # INCORRECT: Native is 0x0001 (Bit 0)
    FLAG_INDEXED_CHANNEL     = 0x0080  # CORRECT: Native is 0x0080 (Bit 7)
    FLAG_HAS_CHECKSUM        = 0x0100  # CORRECT: Native is 0x0100 (Bit 8)
```

#### 2. Native Evidence & Instruction References
- **Bit 0 (`0x0001`):** `0x100923908: tbz w8, #0, #0x100923948` -> First Request Offset (`packet->firstRequestOffset_`).
- **Bit 1 (`0x0002`):** `0x10092297c: tbnz w8, #1, #0x100922db0` -> Piggybacked Bundle.
- **Bit 2 (`0x0004`):** `0x100922994: tbnz w8, #2, #0x100922e4c` -> Piggybacked ACKs (`channel->ackQueue_`).
- **Bit 3 (`0x0008`):** `0x100922984: tbnz w8, #3, #0x100922c88` -> On Channel (Lookup in `nub->channelsByAddress_`).
- **Bit 4 (`0x0010`):** `0x100922f70: tbnz w8, #4, #0x100923090` -> Reliable Request (`FLAG_IS_RELIABLE`, requires `FLAG_HAS_SEQUENCE_NUMBER`).
- **Bit 5 (`0x0020`):** `0x100923948: tbnz w8, #5, #0x100923974` -> Bundle Fragments (8-byte footer: `fragBegin` 4B + `fragEnd` 4B).
- **Bit 6 (`0x0040`):** `0x10092299c: tbz w8, #6, #0x100922f70` -> Sequence Number (`packet->seq_num_`).
- **Bit 7 (`0x0080`):** `0x100922980: tbnz w8, #7, #0x100922dc0` -> Indexed Channel ID (`nub->channelsById_`).
- **Bit 8 (`0x0100`):** `0x100922970: tbnz w8, #8, #0x1009229d0` -> Checksum (32-bit XOR).
- **Bit 9 (`0x0200`):** `0x1009228b8: tbz w8, #9, #0x100922904` and `0x100923208: tbnz w8, #9, #0x100923360` -> Channel Creation.
- **Bits 10–15 (`>= 0x0400`):** `0x100922898: cmp w8, #0x400; b.hs #0x1009228dc` -> Bad Flags Rejection.

#### 3. Required Modifications
1. Re-declare `MercuryPacketFlags` constants with exact native values.
2. In `MercuryPacketParser.pack()`:
   - Accept optional `fragments: Optional[Tuple[int, int]] = None` (`frag_begin`, `frag_end`).
   - Accept `is_reliable: bool = False` to toggle `FLAG_IS_RELIABLE` (`0x0010`).
   - Pack footers in physical forward order such that unpacking in reverse unwinds correctly:
     - Physical Layout:
       `[Header: 2B Flags]`
       `[Payload]`
       `[ReqOffset: 2B (<H)]` (Bit 0)
       `[Fragments: 8B (2x <I)]` (Bit 5)
       `[SeqNum: 4B (<I)]` (Bit 6)
       `[ACKs: N*4B + 1B (<I... + <B)]` (Bit 2)
       `[ChannelID: 4B (<I)]` (Bit 7)
       `[Piggybacks: MB + 2B (<h)]` (Bit 1)
       `[Checksum: 4B (<I)]` (Bit 8)
3. In `MercuryPacketParser.unpack_footers()`:
   - Check `flags >= 0x0400` (already present, retain).
   - Unpack tail Checksum (Bit 8).
   - Unpack Piggybacks (Bit 1).
   - Unpack Channel ID (Bit 7).
   - Unpack ACKs (Bit 2).
   - Unpack Sequence Number (Bit 6).
   - Unpack Fragments (Bit 5): 8 bytes (`<II` -> `frag_begin`, `frag_end`).
   - Unpack Request Offset (Bit 0): 2 bytes (`<H`).
   - Validate that if `flags & FLAG_IS_RELIABLE` (`0x0010`), `seq_num is not None`. If sequence number is missing, raise `PacketFramingError("Illegal request for reliability without sequence number")`.

#### 4. Proposed Code Replacement for `packet_parser.py`
```python
class MercuryPacketFlags:
    FLAG_HAS_REQUESTS        = 0x0001  # Bit 0: First request offset (2 bytes <H)
    FLAG_HAS_PIGGYBACKS      = 0x0002  # Bit 1: Piggybacked bundle (2 bytes len <h + M bytes)
    FLAG_HAS_ACKS            = 0x0004  # Bit 2: Piggybacked ACKs (1 byte count + N*4B <I)
    FLAG_ON_CHANNEL          = 0x0008  # Bit 3: Addressed on channel (no footer, lookup by IP:Port)
    FLAG_IS_RELIABLE         = 0x0010  # Bit 4: Reliable message packet (requires seq_num)
    FLAG_HAS_FRAGMENTS       = 0x0020  # Bit 5: Bundle fragments (8 bytes: fragBegin 4B + fragEnd 4B)
    FLAG_HAS_SEQUENCE_NUMBER = 0x0040  # Bit 6: Packet sequence number (4 bytes <I)
    FLAG_INDEXED_CHANNEL     = 0x0080  # Bit 7: Indexed channel ID (4 bytes <I)
    FLAG_HAS_CHECKSUM        = 0x0100  # Bit 8: 32-bit XOR checksum (4 bytes <I)
    FLAG_CREATE_CHANNEL      = 0x0200  # Bit 9: Channel creation handshake

    ALL_SUPPORTED_MASKS = (
        FLAG_HAS_REQUESTS | FLAG_HAS_PIGGYBACKS | FLAG_HAS_ACKS |
        FLAG_ON_CHANNEL | FLAG_IS_RELIABLE | FLAG_HAS_FRAGMENTS |
        FLAG_HAS_SEQUENCE_NUMBER | FLAG_INDEXED_CHANNEL |
        FLAG_HAS_CHECKSUM | FLAG_CREATE_CHANNEL
    )
```

---

### File 2: `phase6B_8_local_gateway/channel_manager.py`

#### 1. Current Code Analysis (Lines 81–103)
```python
# 2. Process Sequence Number if present
if seq_num is not None:
    if seq_num in self.seen_seqs:
        return "DUPLICATE", f"Packet with seq {seq_num} already processed"

    if seq_num < self.expected_seq:
        return "DUPLICATE", f"Packet seq {seq_num} is behind expected {self.expected_seq}"

    if seq_num > self.expected_seq:
        self.seen_seqs.add(seq_num)
        self.pending_acks.append(seq_num)
        return "OUT_OF_ORDER", f"Received seq {seq_num}, expected {self.expected_seq}"

    self.seen_seqs.add(seq_num)
    self.last_received_seq = seq_num
    self.expected_seq += 1
    self.pending_acks.append(seq_num)
    return "SUCCESS", f"Sequence advanced to {self.expected_seq}"
```

#### 2. Native Evidence & Instruction References
- In `Channel::handlePacket` (`0x10091b6b8`):
  ```assembly
  0x10091b6b8:  sub      w9, w8, w20               ; w9 = incoming_seq - inSeqAt
  0x10091b6bc:  and      w9, w9, #0xfffffff        ; 28-bit modular difference!
  0x10091b6c0:  movk     w10, #0x800, lsl #16      ; w10 = 0x08000000 (Half-Window Threshold)
  0x10091b6c4:  cmp      w9, w10
  0x10091b6c8:  b.hi     #0x10091b704              ; If diff > 0x08000000, packet is old/duplicate
  ```
- Maximum sequence number is $2^{28} - 1 = 0x0FFFFFFF$. Sequence wraps cleanly to $0$ after $0x0FFFFFFF$.
- Sequence `SEQ_NULL = 0x10000000` is reserved to indicate an unsequenced packet.
- Channel creation activation at `0x100923368: strb wzr, [x22, #0x105]` clears `isWantingCreateChannel`.

#### 3. Required Modifications
1. Add constant `SEQ_MASK = 0x0FFFFFFF` (28 bits) and `HALF_WINDOW = 0x08000000` ($2^{27}$).
2. Update `process_incoming_packet()`:
   - Compute modular difference: `diff = (seq_num - self.expected_seq) & SEQ_MASK`.
   - If `diff == 0`: Exact match! Advance `expected_seq = (self.expected_seq + 1) & SEQ_MASK`.
   - If `diff > HALF_WINDOW`: Packet sequence is behind (older than `expected_seq` within circular window) or in `seen_seqs` -> return `"DUPLICATE"`.
   - If `0 < diff <= HALF_WINDOW`: Packet is ahead (gap detected / out-of-order) -> queue ACK, record in `seen_seqs`, return `"OUT_OF_ORDER"`.
3. Add `is_wanting_create_channel: bool` flag to `ChannelState`:
   - Set to `True` when channel record is initially allocated.
   - Cleared to `False` when packet bearing `FLAG_CREATE_CHANNEL` (`0x0200`) arrives.
   - Drop packets on channel if `is_wanting_create_channel == True` but incoming packet lacks `FLAG_CREATE_CHANNEL` (`0x0200`).

---

### File 3: `phase6B_8_local_gateway/synthetic_client.py`

#### 1. Current Code Analysis (Lines 54–67, 87–102)
```python
# In send_init:
flags = (
    MercuryPacketFlags.FLAG_CREATE_CHANNEL |     # 0x0001 (Old)
    MercuryPacketFlags.FLAG_INDEXED_CHANNEL |    # 0x0080
    MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER |# 0x0004 (Old)
    MercuryPacketFlags.FLAG_HAS_CHECKSUM         # 0x0100
) # Resulted in flags = 0x0185

# In send_message:
flags = (
    MercuryPacketFlags.FLAG_ON_CHANNEL |         # 0x0020 (Old)
    MercuryPacketFlags.FLAG_INDEXED_CHANNEL |    # 0x0080
    MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER  # 0x0004 (Old)
) # Resulted in flags = 0x01A4 (or 0x01A5)
```

#### 2. Native Evidence & Correct Values
- In `send_init`:
  - `FLAG_CREATE_CHANNEL` = `0x0200`
  - `FLAG_INDEXED_CHANNEL` = `0x0080`
  - `FLAG_HAS_SEQUENCE_NUMBER` = `0x0040`
  - `FLAG_HAS_CHECKSUM` = `0x0100`
  - Total Flags = `0x0200 | 0x0080 | 0x0040 | 0x0100 = 0x03C0`.
- In `send_message`:
  - `FLAG_ON_CHANNEL` = `0x0008`
  - `FLAG_INDEXED_CHANNEL` = `0x0080`
  - `FLAG_HAS_SEQUENCE_NUMBER` = `0x0040`
  - `FLAG_HAS_CHECKSUM` = `0x0100`
  - Optional `FLAG_IS_RELIABLE` = `0x0010`
  - Unreliable Total Flags = `0x0008 | 0x0080 | 0x0040 | 0x0100 = 0x01C8`.
  - Reliable Total Flags = `0x0008 | 0x0080 | 0x0040 | 0x0010 | 0x0100 = 0x01D8`.

#### 3. Required Modifications
1. Update `send_init()`:
   - Combine updated flags resulting in `0x03C0`.
   - Advance `self.current_seq = (self.current_seq + 1) & 0x0FFFFFFF`.
2. Update `send_message()`:
   - Accept `is_reliable: bool = True`.
   - Combine updated flags: `0x01D8` if reliable, `0x01C8` if unreliable.
   - Advance `self.current_seq = (self.current_seq + 1) & 0x0FFFFFFF`.

---

### File 4: `phase6B_8_local_gateway/gateway.py`

#### 1. Current Code Analysis (Lines 212–215, 305–320, 350–365)
```python
# Channel Init Check:
if flags & MercuryPacketFlags.FLAG_CREATE_CHANNEL:  # Evaluated 0x0001
    self._handle_channel_init(unpacked, engine, client_addr)
    return

# Response Flags in _handle_channel_init and _handle_application_message:
resp_flags = (
    MercuryPacketFlags.FLAG_ON_CHANNEL |          # 0x0020 (Old)
    MercuryPacketFlags.FLAG_INDEXED_CHANNEL |     # 0x0080
    MercuryPacketFlags.FLAG_HAS_SEQUENCE_NUMBER | # 0x0004 (Old)
    MercuryPacketFlags.FLAG_HAS_ACKS |            # 0x0008 (Old)
    MercuryPacketFlags.FLAG_HAS_CHECKSUM          # 0x0100
) # Evaluated to 0x01AC
```

#### 2. Native Evidence & Correct Behavior
- Native dispatch evaluates `FLAG_CREATE_CHANNEL` at Bit 9 (`0x0200`).
- If a packet arrives on a channel wanting creation and does not have Bit 9 set, drop the packet with error log `"Dropping packet on channel wanting FLAG_CREATE_CHANNEL"`.
- Response flags must evaluate to:
  `FLAG_ON_CHANNEL (0x0008) | FLAG_INDEXED_CHANNEL (0x0080) | FLAG_HAS_SEQUENCE_NUMBER (0x0040) | FLAG_HAS_ACKS (0x0004) | FLAG_HAS_CHECKSUM (0x0100) = 0x01CC`.
- If response is reliable: `0x01CC | FLAG_IS_RELIABLE (0x0010) = 0x01DC`.

#### 3. Required Modifications
1. In `_handle_datagram()`:
   - Evaluate `flags & MercuryPacketFlags.FLAG_CREATE_CHANNEL` (`0x0200`).
   - If packet has `FLAG_IS_RELIABLE` (`0x0010`) but lacks `FLAG_HAS_SEQUENCE_NUMBER` (`0x0040`), reject immediately with error category `"ILLEGAL_RELIABILITY_REQUEST"`.
2. In `_handle_channel_init()`:
   - Ensure channel state is properly activated (clearing `is_wanting_create_channel`).
   - Construct response datagram with corrected flags `0x01CC` (or `0x01DC`).
3. In `_handle_application_message()`:
   - Check channel activation: if channel `is_wanting_create_channel == True`, drop packet.
   - Construct response datagram with corrected flags `0x01CC` (or `0x01DC`).
4. In `_server_seq` progression:
   - Advance using `self._server_seq = (self._server_seq + 1) & 0x0FFFFFFF`.

---

### File 5: `phase6B_8_local_gateway/protocol_engine.py`

#### 1. Current Code Analysis (Lines 61–72)
```python
def send_packet(
    self,
    payload: bytes,
    flags: int = 0,
    seq_num: Optional[int] = None,
    channel_id: Optional[int] = None,
    acks: Optional[List[int]] = None,
    piggyback: Optional[bytes] = None,
    first_request_offset: Optional[int] = None,
    enable_checksum: bool = True,
    slack_mode: str = "zero"
) -> bytes:
```

#### 2. Required Modifications
1. Add `fragments: Optional[Tuple[int, int]] = None` to `send_packet()` signature and pass through to `MercuryPacketParser.pack()`.
2. Add `is_reliable: bool = False` to `send_packet()` signature.
3. In `receive_packet()`:
   - Forward unpacked `fragments` tuple and `is_reliable` boolean in return dictionary.
   - Validate that if `flags & FLAG_IS_RELIABLE`, sequence number must be present.

---

### File 6: `phase6B_8_local_gateway/tests/` Suite Updates

#### 1. `tests/test_unit.py`
- Update Test 3 (`test_03_independent_golden_login_datagram_and_checksum`):
  - Previously, flags were `0x0100 | 0x0080 | 0x0004 = 0x0184`.
  - With corrected `FLAG_HAS_SEQUENCE_NUMBER = 0x0040`, flags become `0x0100 | 0x0080 | 0x0040 = 0x01C0`.
  - Checksum changes from `0x7b76ba9e` to newly calculated golden checksum.
  - Padded ciphertext changes to newly calculated golden ciphertext.
- Add Test 9 (`test_09_fragment_footer_packing_and_unpacking`):
  - Tests Bit 5 (`0x0020`) with 8-byte `fragBegin` and `fragEnd`.
- Add Test 10 (`test_10_reliable_flag_without_sequence_rejection`):
  - Tests Bit 4 (`0x0010`) without Bit 6 (`0x0040`) triggering `PacketFramingError`.

#### 2. `tests/test_channel_state.py`
- Add Test 8 (`test_08_sequence_wraparound_28bit`):
  - Tests sequence progression from `0x0FFFFFFF` to `0x00000000`.
- Add Test 9 (`test_09_half_window_duplicate_threshold`):
  - Tests modular difference comparison across the $2^{27} = 0x08000000$ half-window boundary.
- Add Test 10 (`test_10_channel_creation_activation_gate`):
  - Tests that packets lacking `0x0200` are rejected on unactivated channels.

#### 3. `tests/test_udp_integration.py`
- Update all expected flags in assertions:
  - Init packet client flags: `0x03C0` (was `0x0185`).
  - Init response server flags: `0x01CC` (was `0x01AC`).
  - App message client flags: `0x01C8` / `0x01D8` (was `0x01A4`).
  - App response server flags: `0x01CC` (was `0x01AC`).
- Confirm all 14 integration scenarios pass with updated flags.

---

## 3. Implementation Order and Safety Gates

To ensure non-destructive execution and total traceability, the implementation must proceed in 4 strict sequential gates:

```
[ Gate 1: Parser & Flag Enums ]
  Update packet_parser.py (Flags + Fragment Footer)
  Update test_unit.py Golden Vectors
  VERIFY: All unit tests pass
         |
         v
[ Gate 2: Sequence & Channel State ]
  Update channel_manager.py (28-bit modular diff + ACK queue + activation gate)
  Update test_channel_state.py (Wraparound & half-window tests)
  VERIFY: All channel state tests pass
         |
         v
[ Gate 3: Protocol Engine & Client ]
  Update protocol_engine.py (Fragment pass-through)
  Update synthetic_client.py (0x03C0 init, 0x01C8/0x01D8 message)
  Update gateway.py (0x0200 init routing, 0x01CC responses)
  VERIFY: Full local integration passes
         |
         v
[ Gate 4: Independent Reconstruction Audit ]
  Update phase6B_8_1_audit/independent_reconstruction.py
  Verify independent bit-level match against native client wire format
```

---

## 4. Safety & Authorization Confirmation

> [!IMPORTANT]
> This plan is strictly analytical and conceptual. In compliance with Phase 6.2B.8.4 rules:
> - **NO code files in `phase6B_8_local_gateway/` have been altered.**
> - **NO sockets have been opened.**
> - **Implementation will proceed ONLY upon explicit user approval.**
