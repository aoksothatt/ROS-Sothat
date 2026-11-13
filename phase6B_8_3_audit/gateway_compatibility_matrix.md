# Gateway Compatibility Matrix
## Native ROS Legacy Mercury Transport vs. Local Synthetic Gateway (`phase6B_8_local_gateway/`)

**Target Audit:** Rules of Survival Legacy iOS Client (ARM64) vs. Phase 6.2B.8 Synthetic Prototype  
**Audit Phase:** Phase 6.2B.8.3  
**Status:** COMPLETE  

---

## 1. Executive Summary

This matrix provides a component-by-component and feature-by-feature comparison between:
1. **The Native BigWorld Mercury Transport** disassembled directly from `extracted/Payload/client.app/client`.
2. **The Local Synthetic Mercury UDP Gateway** implemented in [`phase6B_8_local_gateway/`](file:///d:/ROS-Legacy-Analysis/phase6B_8_local_gateway/).

The audit reveals that while the **low-level cryptographic pipeline** (Blowfish PBC, single-byte wastage count padding, and 32-bit SIMD XOR checksum) is bit-for-bit identical to the native client, the **protocol flag mappings** and **higher-layer bundle/reliability semantics** exhibit critical mismatches that would prevent communication with an original, unmodified physical client.

---

## 2. Comprehensive Compatibility Matrix

| Feature | Native Evidence | Gateway Implementation | Status | Required Correction |
|---|---|---|---|---|
| **Header Flags Width** | 16-bit uint16 at Offset 0 (`0x100922894: ldrh w8, [x28, #0x60]!`) | 2 bytes little-endian `<H` at Offset 0 (`packet_parser.py:131`) | **MATCH** | None |
| **Flags Upper Bound Check** | Discard if $\ge 0x0400$ (`0x100922898: cmp w8, #0x400; b.hs`) | Raises `PacketFramingError` if `flags >= 0x0400` (`packet_parser.py:133`) | **MATCH** | None |
| **Flag: Checksum** | Bit 8 (`0x0100`, VA `0x100922970`) | `FLAG_HAS_CHECKSUM = 0x0100` (`packet_parser.py:32`) | **MATCH** | None |
| **Flag: Indexed Channel** | Bit 7 (`0x0080`, VA `0x100922980`) | `FLAG_INDEXED_CHANNEL = 0x0080` (`packet_parser.py:31`) | **MATCH** | None |
| **Flag: Piggybacks** | Bit 1 (`0x0002`, VA `0x10092297c`) | `FLAG_HAS_PIGGYBACKS = 0x0002` (`packet_parser.py:26`) | **MATCH** | None |
| **Flag: Sequence Number** | Bit 6 (`0x0040`, VA `0x10092299c`) | `FLAG_HAS_SEQUENCE_NUMBER = 0x0004` (Bit 2) (`packet_parser.py:27`) | **MISMATCH** | Change `FLAG_HAS_SEQUENCE_NUMBER` from `0x0004` to `0x0040` |
| **Flag: Piggybacked ACKs** | Bit 2 (`0x0004`, VA `0x100922994`) | `FLAG_HAS_ACKS = 0x0008` (Bit 3) (`packet_parser.py:28`) | **MISMATCH** | Change `FLAG_HAS_ACKS` from `0x0008` to `0x0004` |
| **Flag: On Channel (Address)** | Bit 3 (`0x0008`, VA `0x100922984`) | `FLAG_ON_CHANNEL = 0x0020` (Bit 5) (`packet_parser.py:29`) | **MISMATCH** | Change `FLAG_ON_CHANNEL` from `0x0020` to `0x0008` |
| **Flag: First Request Offset** | Bit 0 (`0x0001`, VA `0x100923908`) | `FLAG_HAS_REQUESTS = 0x0040` (Bit 6) (`packet_parser.py:30`) | **MISMATCH** | Change `FLAG_HAS_REQUESTS` from `0x0040` to `0x0001` |
| **Flag: Create Channel** | Bit 9 (`0x0200`, VA `0x1009228b8`, `0x100923208`)| `FLAG_CREATE_CHANNEL = 0x0001` (Bit 0) (`packet_parser.py:25`) | **MISMATCH** | Change `FLAG_CREATE_CHANNEL` from `0x0001` to `0x0200` |
| **Flag: Reliability Required** | Bit 4 (`0x0010`, VA `0x100922f70`) | Not defined in gateway flags enum | **NOT IMPLEMENTED** | Add `FLAG_IS_RELIABLE = 0x0010` to `MercuryPacketFlags` |
| **Flag: Bundle Fragments** | Bit 5 (`0x0020`, VA `0x100923948`) | Misallocated to `FLAG_ON_CHANNEL` | **MISMATCH** | Add `FLAG_HAS_FRAGMENTS = 0x0020` and support 8B footer |
| **Checksum Algorithm** | 32-bit bitwise XOR sum (`0x100922c00`, `0x100922c38`) | 32-bit bitwise XOR sum over `<I` dwords (`checksum.py:17`) | **MATCH** | None |
| **Checksum In-Place Zeroing** | Tail 4B zeroed during compute (`0x100922a54: str wzr`) | Field packed with 0 in-place during compute (`checksum.py:20`) | **MATCH** | None |
| **Checksum Execution Timing** | Executed in `processFilteredPacket` after decrypt | Verified strictly after `BlowfishPBC.decrypt` and unpad | **MATCH** | None |
| **Cipher Primitive** | OpenSSL `BF_ecb_encrypt` calls (`0x1000ab248`) | OpenSSL ECB block primitive via `cryptography` | **MATCH** | None |
| **Cipher Chaining Mode** | PBC: `mov x8, x27` (`0x10091c82c`) | $C_i = E(P_i \oplus P_{i-1})$ (`pbc_cipher.py:34`) | **MATCH** | None |
| **IV Lifecycle** | Implicit zero IV per packet (`0x10091c7f4: mov x8, #0`) | Implicit zero IV per datagram; stateless between packets | **MATCH** | None |
| **Padding Format** | Single-byte wastage count at `buf[-1]` (`0x10091c7c4`)| Single-byte trailer $1 \le L \le 8$ at `buf[-1]` | **MATCH** | None |
| **Padding Validation Policy** | Receiver checks only `buf[-1] <= 8` (`0x10091c9e0`)| Receiver validates only `buf[-1] <= 8` | **MATCH** | None |
| **Padding Slack Policy** | Uninitialized buffer memory pool | Zero-filled slack bytes (`0x00`) | **SYNTHETIC ONLY** | Retain zero-slack policy for memory hygiene |
| **Footer Unpacking Order** | Reverse from tail: Checksum $\to$ Piggybacks $\to$ CID $\to$ ACKs $\to$ SeqNum $\to$ Frag $\to$ Req | Reverse from tail: Checksum $\to$ Piggybacks $\to$ CID $\to$ ACKs $\to$ SeqNum $\to$ Req | **PARTIALLY IMPLEMENTED**| Add fragment footer unpacking step (Bit 5: 8 bytes) |
| **Sequence Number Width** | 4-byte uint32 little-endian (`<I`, VA `0x100922f68`)| 4-byte uint32 little-endian (`<I`) | **MATCH** | None |
| **Channel ID Width** | 4-byte uint32 little-endian (`<I`, VA `0x100922dec`)| 4-byte uint32 little-endian (`<I`) | **MATCH** | None |
| **ACK Footer Format** | 1B count + $N \times 4$B seqs (`0x100922efc`, `0x100922f08`)| 1B count + $N \times 4$B seqs (`packet_parser.py:186`) | **MATCH** | None |
| **First Request Offset Width** | 2-byte uint16 little-endian (`<H`, VA `0x100923940`)| 2-byte uint16 little-endian (`<H`, `packet_parser.py:204`) | **MATCH** | None |
| **Fragment Footer Format** | 8 bytes: `fragBegin` (4B) + `fragEnd` (4B) (`<I`, `0x1009239bc`)| Not implemented | **NOT IMPLEMENTED** | Implement 8-byte fragment unpacking when Bit 5 set |
| **Channel Creation Handshake**| Requires `FLAG_CREATE_CHANNEL` (`0x0200`) on initial packet; clears `isWantingCreateChannel` (`0x100923368`) | Checks `FLAG_CREATE_CHANNEL` (`0x0001`) in `INIT_CHANNEL` action; transitions channel state | **MISMATCH** | Update flag check to `0x0200` |
| **Reliability Window Mechanism**| BigWorld `Nub` cumulative ACK window tree with 28-bit modular difference (`0x10091b6b8: and w9, w9, #0xfffffff`) | Monotonic integer sequence progression (`channel_manager.py:90`) | **EXPERIMENTAL DESIGN CHOICE** | Retain discrete sequence for prototype; adopt window for full native interoperability |
| **Session Key Provisioning** | Dynamic RSA-OAEP public-key login handshake (`LoginConnection::sendLogin`)| Static pre-shared master keys in `config.py` | **EXPERIMENTAL DESIGN CHOICE** | Reconcile with RSA handshake in Phase 6.2B.9 |
| **Application Payload Body** | BigWorld Engine binary RPC bundles (Entity IDs, method numbers, BigWorld stream) | UTF-8 JSON commands (`{"action": "INIT_CHANNEL"}`) | **SYNTHETIC ONLY** | Requires BigWorld bundle serializer/deserializer |

---

## 3. Affected Source Files in `phase6B_8_local_gateway/`

The following gateway files require updates when transitioning from the synthetic prototype to native Mercury compatibility:

1. **`phase6B_8_local_gateway/packet_parser.py`:**
   - Update `MercuryPacketFlags`:
     - `FLAG_HAS_REQUESTS = 0x0001` (was `0x0040`)
     - `FLAG_HAS_PIGGYBACKS = 0x0002` (unchanged)
     - `FLAG_HAS_ACKS = 0x0004` (was `0x0008`)
     - `FLAG_ON_CHANNEL = 0x0008` (was `0x0020`)
     - `FLAG_IS_RELIABLE = 0x0010` (new)
     - `FLAG_HAS_FRAGMENTS = 0x0020` (new)
     - `FLAG_HAS_SEQUENCE_NUMBER = 0x0040` (was `0x0004`)
     - `FLAG_INDEXED_CHANNEL = 0x0080` (unchanged)
     - `FLAG_HAS_CHECKSUM = 0x0100` (unchanged)
     - `FLAG_CREATE_CHANNEL = 0x0200` (was `0x0001`)
   - Update `MercuryPacketParser.pack()`:
     - Reorder footer assembly to match native reverse sequence.
     - Add `fragments: Optional[Tuple[int, int]]` argument to support `fragBegin` and `fragEnd`.
   - Update `MercuryPacketParser.unpack_footers()`:
     - Unpack `FLAG_HAS_FRAGMENTS` (8 bytes) between SeqNum and Request Offset.

2. **`phase6B_8_local_gateway/synthetic_client.py`:**
   - Update `send_init()`: Change `FLAG_CREATE_CHANNEL` to `0x0200` and `FLAG_HAS_SEQUENCE_NUMBER` to `0x0040`.
   - Update `send_message()`: Change `FLAG_ON_CHANNEL` to `0x0008` and `FLAG_HAS_SEQUENCE_NUMBER` to `0x0040`.

3. **`phase6B_8_local_gateway/gateway.py`:**
   - Update incoming packet routing: Recognize `0x0200` as channel initialization.
   - Update response packet framing to use corrected flag bits.

4. **`phase6B_8_local_gateway/channel_manager.py`:**
   - Incorporate 28-bit modular sequence difference (`seq & 0x0FFFFFFF`) to match native `0x10091b6b8`.

5. **`phase6B_8_local_gateway/tests/`:**
   - `test_unit.py`: Update literal flag values in test datagrams (e.g. Test 3 Login datagram flags).
   - `test_channel_state.py`: Update flag assertions for ACKs and sequence numbers.
   - `test_udp_integration.py`: Update integration test assertions for client-gateway exchange.
   - `phase6B_8_1_audit/independent_reconstruction.py`: Update golden test vectors to reflect native flag masks.

---

## 4. Immediate Safety and Non-Regression Guarantee

Under Phase 6.2B.8.3 rules:
- **No changes have been made to any gateway source files or test scripts.**
- The existing gateway remains fully functional and self-consistent for isolated localhost testing.
- All modifications will be executed only after formal user review and explicit phase authorization.
