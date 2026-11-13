# Gate 1 Verification Report: Mercury Parser and Flag Corrections
**Project:** ROS Sothat — Original ROS Legacy iOS Private Server Research  
**Phase:** 6.2B.8.5 — Controlled Implementation  
**Gate:** GATE 1 — Mercury Parser & Flag Corrections  
**Date:** November 13, 2026  
**Status:** PASS  

---

## 1. Executive Summary

Gate 1 aligned the local synthetic gateway's header flag definitions and reverse packet footer parsing logic with the native BigWorld Mercury implementation verified in Phase 6.2B.8.3 from the original iOS client Mach-O binary (`extracted/Payload/client.app/client`).

All 10 native Mercury flags and their corresponding footers were implemented with 100% adherence to native ARM64 control-flow disassembly. The implementation preserves Blowfish PBC encryption, single-byte wastage trailer padding, and the 32-bit SIMD XOR checksum reduction.

Unit testing was executed offline with 13 comprehensive test suites spanning 10 individual flag isolation tests, valid combination tests, reserved-bit rejection tests, bundle fragment range/truncation checks, and independent golden vector validation. **All 13 unit tests passed with 0 failures and 0 errors.**

---

## 2. Modified Files and Changes

### 1. `phase6B_8_local_gateway/packet_parser.py`
- **Native Evidence Classification:** `VERIFIED BY NATIVE EVIDENCE`
- **Updated `MercuryPacketFlags` enumeration:**
  ```python
  class MercuryPacketFlags:
      FLAG_HAS_REQUESTS        = 0x0001  # Bit 0 (was 0x0040)
      FLAG_HAS_PIGGYBACKS      = 0x0002  # Bit 1 (unchanged)
      FLAG_HAS_ACKS            = 0x0004  # Bit 2 (was 0x0008)
      FLAG_ON_CHANNEL          = 0x0008  # Bit 3 (was 0x0020)
      FLAG_IS_RELIABLE         = 0x0010  # Bit 4 (NEW)
      FLAG_HAS_FRAGMENTS       = 0x0020  # Bit 5 (was On-Channel)
      FLAG_HAS_SEQUENCE_NUMBER = 0x0040  # Bit 6 (was 0x0004)
      FLAG_INDEXED_CHANNEL     = 0x0080  # Bit 7 (unchanged)
      FLAG_HAS_CHECKSUM        = 0x0100  # Bit 8 (unchanged)
      FLAG_CREATE_CHANNEL      = 0x0200  # Bit 9 (was 0x0001)

      ALL_SUPPORTED_MASKS = (
          FLAG_HAS_REQUESTS | FLAG_HAS_PIGGYBACKS | FLAG_HAS_ACKS |
          FLAG_ON_CHANNEL | FLAG_IS_RELIABLE | FLAG_HAS_FRAGMENTS |
          FLAG_HAS_SEQUENCE_NUMBER | FLAG_INDEXED_CHANNEL |
          FLAG_HAS_CHECKSUM | FLAG_CREATE_CHANNEL
      )
  ```
- **Forward Assembly in `pack()`:**
  - Added support for `fragments: Optional[Tuple[int, int]] = None` (`fragBegin`, `fragEnd`).
  - Added `is_reliable`, `is_create_channel`, and `is_on_channel` flags.
  - Assembled footers in forward order matching reverse tail unwinding:
    `[ReqOffset: 2B]` $\to$ `[Fragments: 8B]` $\to$ `[SeqNum: 4B]` $\to$ `[ACKs: N*4B+1B]` $\to$ `[ChannelID: 4B]` $\to$ `[Piggyback: M+2B]` $\to$ `[Checksum: 4B]`.
- **Reverse Unpacking in `unpack_footers()`:**
  - Added unpacking for 8-byte Fragment footer (Bit 5).
  - Added native reliability check: If `FLAG_IS_RELIABLE` (`0x0010`) is set without `seq_num`, raises `PacketFramingError` (matching native instruction `0x100923098`).
  - Rejection of reserved flags $\ge 0x0400$ and unsupported bits retained.

### 2. `phase6B_8_local_gateway/protocol_engine.py`
- **Native Evidence Classification:** `VERIFIED BY SOURCE INSPECTION`
- Updated `send_packet()` signature to accept `fragments`, `is_reliable`, `is_create_channel`, and `is_on_channel`, passing them through to `MercuryPacketParser.pack()`.

### 3. `phase6B_8_local_gateway/tests/test_unit.py`
- **Native Evidence Classification:** `VERIFIED BY INDEPENDENT SYNTHETIC CALCULATION`
- Updated Test 3 golden datagram flags from `0x0184` to corrected native flag `0x01C0` (`FLAG_HAS_CHECKSUM | FLAG_INDEXED_CHANNEL | FLAG_HAS_SEQUENCE_NUMBER`).
- Updated golden checksum to `0x7b76bada` (proving XOR linearity: `0x7b76ba9e ^ 0x0044 = 0x7b76bada`).
- Updated expected ciphertext to `b7036a2c2f2da845...57d9371d16c659e8`.
- Added Test 9: All 10 individual flags isolation verification.
- Added Test 10: `FLAG_IS_RELIABLE` without sequence number rejection.
- Added Test 11: Fragment range validation (`fragEnd < fragBegin` check).
- Added Test 12: Valid flag combination matrix (`0x0100`, `0x0102`, `0x0180`, `0x03C0`, `0x0158`, `0x01D0`, `0x01C4`, `0x01CC`, `0x01E0`).
- Added Test 13: Truncated footer bounds testing across all 8 footer types.

---

## 3. Test Execution and Results

Command run:
```powershell
python phase6B_8_local_gateway/tests/test_unit.py
```

Output:
```
.............
----------------------------------------------------------------------
Ran 13 tests in 0.010s

OK
```

### Detailed Test Results Table:
| Test ID | Test Name | Status | Evidence Classification |
|---|---|---|---|
| `test_01` | Independent Golden PBC Single Block | **PASS** | VERIFIED BY INDEPENDENT SYNTHETIC CALCULATION |
| `test_02` | Independent Golden PBC Multi-Block (2, 3, 4 blocks) | **PASS** | VERIFIED BY INDEPENDENT SYNTHETIC CALCULATION |
| `test_03` | Independent Golden Login Datagram & Checksum (0x01C0) | **PASS** | VERIFIED BY INDEPENDENT SYNTHETIC CALCULATION |
| `test_04` | Single-Byte Trailer Padding Boundaries (0..32 bytes) | **PASS** | VERIFIED BY NATIVE EVIDENCE |
| `test_05` | Single-Byte Trailer Slack Independence | **PASS** | VERIFIED BY NATIVE EVIDENCE |
| `test_06` | Bad Flags Rejection (>= 0x0400: 0x0400..0xFFFF) | **PASS** | VERIFIED BY NATIVE EVIDENCE |
| `test_07` | Tampered Ciphertext Rejection | **PASS** | VERIFIED BY SOURCE INSPECTION |
| `test_08` | Mismatched Session Key Rejection | **PASS** | VERIFIED BY SOURCE INSPECTION |
| `test_09` | All 10 Individual Flags Isolation Verification | **PASS** | VERIFIED BY NATIVE EVIDENCE |
| `test_10` | Reliable Flag Without Sequence Rejection | **PASS** | VERIFIED BY NATIVE EVIDENCE |
| `test_11` | Bundle Fragment Range Validation | **PASS** | VERIFIED BY NATIVE EVIDENCE |
| `test_12` | Valid Flag Combinations Matrix | **PASS** | VERIFIED BY NATIVE EVIDENCE |
| `test_13` | Truncated Footer Bounds Rejection (all 8 types) | **PASS** | VERIFIED BY NATIVE EVIDENCE |

---

## 4. Gate 1 Acceptance Criteria Checklist

- [x] Every known flag has the correct native mask (`0x0001` through `0x0200`).
- [x] No two flags accidentally share a mask.
- [x] Reserved flags ($\ge 0x0400$) are strictly rejected.
- [x] Footer parsing follows the documented native reverse layout.
- [x] Tests cover individual flags and supported combinations.
- [x] All existing regression tests pass with updated golden vectors.

**GATE 1 STATUS: PASSED.** Proceeding to Gate 2.
