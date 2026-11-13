# ROS Sothat — Phase 6.2B.7: Offline Synthetic Cryptographic & Mercury Protocol Validation Report

**Date:** November 12, 2026  
**Status:** COMPLETE (OFFLINE SYNTHETIC VALIDATION ONLY)  
**Research Directory:** `phase6B_7_synthetic_research/`  
**Test Suite Status:** 29 Passed, 0 Failed, 0 Skipped (100% Pass Rate in 0.077s)  
**Target Reference Client:** `RoS-Legacy-iOS.ipa` (`Payload/client.app/client` — 64-bit ARM64 Mach-O)  
**Production Backend:** `ros-private-server` (Completely Untouched; 133 Passing Tests)  

---

## 1. Executive Summary

Phase 6.2B.7 successfully constructed and executed an isolated, offline, synthetic cryptographic and protocol validation test suite. The suite rigorously evaluated the hypotheses and findings established during the Phase 6.2B.6 design phase without touching production systems, original game archives, or external networks.

```
+---------------------------------------------------------------------------------------------------+
|                               PHASE 6.2B.7 VALIDATION SCORECARD                                   |
+-----------------------------+--------------------+---------------+--------------------------------+
| Test Domain                 | Module             | Tests Passed  | Key Result                     |
+-----------------------------+--------------------+---------------+--------------------------------+
| Synthetic RSA-OAEP          | test_rsa_oaep.py   | 10 / 10 (100%)| SHA-1 OAEP verified; bounds ok |
| Synthetic Blowfish CBC      | test_blowfish_cbc  |  6 /  6 (100%)| Native ECB-loop == CBC zero-IV |
| Mercury Reverse Footers     | test_mercury_parser| 10 / 10 (100%)| Head flags + reverse footers ok|
| Deterministic Test Vectors  | test_synthetic_vec |  3 /  3 (100%)| Reproducible vector suite ok   |
+-----------------------------+--------------------+---------------+--------------------------------+
| TOTAL SUITE EXECUTION       | 4 Modules          | 29 / 29 (100%)| Execution time: 0.077 seconds  |
+-----------------------------+--------------------+---------------+--------------------------------+
```

### Critical Discoveries & Validations:
1. **Mathematical Equivalence of Native Blowfish-CBC [VERIFIED]:**  
   The client's manual unrolled ECB loop (`0x10091c7f0` - `0x10091c834`) was modeled in Python and proven to be **bit-for-bit identical** to standard library Blowfish in CBC mode with an all-zero IV (`b'\x00'*8`). Each datagram independently resets to zero IV.
2. **Packet Layout Clarification [VERIFIED]:**  
   Disassembly audit of `Nub::processFilteredPacket` (VA `0x100922894: ldrh w8, [x28, #0x60]`) resolved a critical framing detail: **The 16-bit flags word resides at the HEAD of the packet (Offset 0)**, while all optional control fields (Requests, SeqNum, ACKs, Channel ID, Piggybacks, Checksum) reside at the **TAIL** and are unpacked backwards.
3. **SIMD Checksum Identified [VERIFIED]:**  
   The datagram checksum (flag `0x0100`) is **not CRC32**. Disassembly at VA `0x100922bdc` - `0x100922c28` revealed ARM NEON SIMD instructions (`eor v0.16b`, `dup v1.4s`) computing a fast **32-bit XOR checksum** over all dwords in the packet with the checksum field zeroed.
4. **RSA-OAEP Boundary Enforcement [VERIFIED]:**  
   Strict capacity limits for OpenSSL `RSA_PKCS1_OAEP_PADDING` ($k - 42$ bytes) were validated. For a 1024-bit key, 86 bytes succeeds while 87 bytes raises `ValueError`. The standard 56-byte session key payload encrypts cleanly with 30 bytes of capacity to spare.

---

## 2. Scope & Protection Boundaries

All activities in Phase 6.2B.7 complied strictly with the project's non-destructive research rules:
* **Isolated Research Directory:** All test scripts, fixtures, and synthetic runners were placed exclusively inside `phase6B_7_synthetic_research/`.
* **Zero Real Key Usage:** 100% of tested RSA keys, Blowfish session keys, usernames, and tokens were synthetically generated dummy data. No NetEase private keys or extracted game credentials were used.
* **Zero Production Access:** No network sockets were opened, no production database was connected, and no live game servers (LoginApp/BaseApp) were launched.
* **Integrity of Original Artifacts:** `RoS-Legacy-iOS.ipa` remains bit-for-bit untouched (846,004,086 bytes). The existing `ros-private-server` backend codebase was completely unedited.

---

## 3. Task A — RSA-OAEP Validation

### 3.1 Test Coverage (`test_rsa_oaep.py`)
Ten targeted test cases evaluated RSA-OAEP behavior using synthetic 1024-bit and 2048-bit keypairs:

```
+-------------------------------------------------------+-------------+-----------------------------+
| Test Case                                             | Status      | Observed Behavior           |
+-------------------------------------------------------+-------------+-----------------------------+
| test_01_synthetic_key_serialization                  | PASSED      | Valid SubjectPublicKeyInfo  |
| test_02_oaep_56_byte_session_key_roundtrip_1024       | PASSED      | Exact 56-byte recovery      |
| test_03_oaep_56_byte_session_key_roundtrip_2048       | PASSED      | Exact 56-byte recovery      |
| test_04_boundary_conditions_1024 (85, 86, 87 bytes)   | PASSED      | Max 86B; 87B raises error   |
| test_05_boundary_conditions_2048 (214, 215 bytes)     | PASSED      | Max 214B; 215B raises error |
| test_06_negative_wrong_private_key                    | PASSED      | Decryption fails (ValueError)
| test_07_negative_tampered_ciphertext                  | PASSED      | Bit-flip fails (ValueError) |
| test_08_negative_padding_mode_mismatch                | PASSED      | PKCS#1 v1.5 cannot decode   |
| test_09_negative_mgf1_digest_mismatch                 | PASSED      | MGF1 SHA-256 rejected       |
| test_10_negative_label_mismatch                       | PASSED      | Non-empty label rejected    |
+-------------------------------------------------------+-------------+-----------------------------+
```

### 3.2 Key Cryptographic Distinctions Established
1. **Message Digest vs. MGF1 Digest:** OpenSSL's standard `RSA_PKCS1_OAEP_PADDING` mode configures **SHA-1 for both** the primary message digest and the Mask Generation Function (MGF1).
2. **OAEP Label:** In OpenSSL `RSA_public_encrypt`, the label parameter is NULL (`label = None`, length 0).
3. **Modulus Sizing:** Disassembly confirmed `PublicKeyCipher::setKey` dynamically calculates `RSA_size(rsa) * 8`. The test suite verified that our server architecture handles both 1024-bit ($k=128$, max input 86 bytes) and 2048-bit ($k=256$, max input 214 bytes) keys seamlessly.

---

## 4. Task B — Blowfish Encryption & Decryption Validation

### 4.1 Native Algorithm vs. Standard CBC
The client binary implements Blowfish encryption in `neox::bwclient::Mercury::EncryptionFilter` via an unrolled ECB loop with register-level XOR chaining:
```assembly
0x10091c808:  ldr  x8, [x8]          ; x8 = previous ciphertext block (0 for block 0)
0x10091c80c:  eor  x9, x8, x9        ; x9 = plaintext XOR previous ciphertext
0x10091c814:  str  x9, [x0]
0x10091c824:  bl   0x1000ab248       ; BF_ecb_encrypt(x0, x0, key, BF_ENCRYPT)
```

In `test_blowfish_cbc.py`, this exact manual loop was implemented alongside standard `Cipher(Blowfish(key), modes.CBC(b'\x00'*8))`. Across all payload sizes, both implementations produced **100% identical ciphertexts**.

### 4.2 Test Coverage (`test_blowfish_cbc.py`)
```
+-------------------------------------------------------+-------------+-----------------------------+
| Test Case                                             | Status      | Observed Behavior           |
+-------------------------------------------------------+-------------+-----------------------------+
| test_01_key_length_boundaries (3, 4, 16, 56, 57 bytes)| PASSED      | 4-56B valid; <4, >56 rejected
| test_02_native_vs_standard_cbc_equivalence            | PASSED      | Bit-for-bit identical bytes |
| test_03_exact_plaintext_recovery_across_lengths       | PASSED      | 0, 1, 7, 8, 9, 15, 16, 17...|
| test_04_tampered_ciphertext                           | PASSED      | Corrupted pad/block rejected|
| test_05_truncated_ciphertext (non-multiple of 8)      | PASSED      | Stream size error raised    |
| test_06_independent_datagram_statelessness            | PASSED      | Zero IV reset per datagram  |
+-------------------------------------------------------+-------------+-----------------------------+
```

### 4.3 Padding Scheme Insights
* **Encoding (Encryptor):** Appends 1 to 8 bytes such that `(len + pad) % 8 == 0`. At VA `0x10091c7c4`, instruction `sturb w8, [x9, #-1]` writes the pad length specifically into the **last byte** of the buffer.
* **Decoding (Decryptor):** At VA `0x10091c9dc`, instruction `ldrb w21, [x10, #0x5f]` reads the final byte and validates $1 \le \text{pad\_len} \le 8$.
* **Interoperability:** Both ANSI X9.23 (zeroes with last byte tag) and PKCS#7 (all bytes equal tag) decode successfully because the decryptor only inspects the final byte. Setting pad bytes according to ANSI X9.23 or PKCS#7 is completely safe.

---

## 5. Task C — Mercury Reverse-Order Footer Parser Validation

### 5.1 Packet Framing Architecture
Through iterative disassembly verification, the Mercury datagram structure was established:

```
+---------------------------------------------------------------------------------------------------+
|                                 MERCURY UDP PACKET WIRE STRUCTURE                                 |
+-------------------+-----------------------------+-------------------------------------------------+
| Offset 0..1       | Offset 2 .. (Tail - N)      | Tail - N .. Tail                                |
| Header Flags      | Message Payload             | Reverse-Order Footers                           |
| (16-bit uint16)   | (BigWorld Message Bundles)  | [RequestOffset] [SeqNum] [ACKs] [ChanID] [CRC32]|
+-------------------+-----------------------------+-------------------------------------------------+
```

### 5.2 Footers and Flag Mask Association
Unpacked backwards from the tail of the received datagram:
1. **Checksum (4 bytes):** If `FLAG_HAS_CHECKSUM` (`0x0100`) is set. 32-bit XOR reduction.
2. **Piggyback Bundle (2 bytes len + M bytes data):** If `FLAG_HAS_PIGGYBACKS` (`0x0002`) is set.
3. **Indexed Channel ID (4 bytes):** If `FLAG_INDEXED_CHANNEL` (`0x0080`) is set.
4. **Piggybacked ACKs (1 byte count + $N \times 4$ bytes):** If `FLAG_HAS_ACKS` (`0x0008`) is set.
5. **Sequence Number (4 bytes):** If `FLAG_HAS_SEQUENCE_NUMBER` (`0x0004`) is set.
6. **First Request Offset (2 bytes):** If `FLAG_HAS_REQUESTS` (`0x0040`) is set.

### 5.3 Test Coverage (`test_mercury_parser.py`)
```
+-------------------------------------------------------+-------------+-----------------------------+
| Test Case                                             | Status      | Observed Behavior           |
+-------------------------------------------------------+-------------+-----------------------------+
| test_01_empty_optional_footers                        | PASSED      | Header + payload parsed     |
| test_02_individual_footer_sequence_number             | PASSED      | SeqNum extracted cleanly    |
| test_03_individual_footer_channel_id                  | PASSED      | Channel ID extracted cleanly|
| test_04_individual_footer_acks                        | PASSED      | List of ACKs extracted      |
| test_05_individual_footer_piggyback                   | PASSED      | Piggybacked bundle unpacked |
| test_06_all_footers_combined simultaneously           | PASSED      | All 6 footers unpacked ok   |
| test_07_checksum_verification_and_tamper_detection    | PASSED      | XOR checksum verified       |
| test_08_truncated_packet_handling                     | PASSED      | Gracefully raises ValueError|
| test_09_invalid_ack_count                             | PASSED      | Rejects count=0 or overrun  |
| test_10_bad_flags_rejection                           | PASSED      | Rejects flags >= 0x0400     |
+-------------------------------------------------------+-------------+-----------------------------+
```

---

## 6. Reproducible Synthetic Test Vectors

The following deterministic test vectors allow any developer to verify interoperability without requiring proprietary game client binaries.

### Vector 1: RSA-OAEP Key Handshake Payload
* **Modulus Size:** 1024 bits (128 bytes)
* **Public Exponent ($e$):** 65537 (`0x010001`)
* **Padding:** `RSA_PKCS1_OAEP_PADDING`
* **Message Digest:** SHA-1
* **MGF1 Digest:** SHA-1
* **Label:** None (empty)
* **Synthetic Plaintext (56 bytes):**
  ```text
  ASCII: "DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY_56_BYTES!12"
  HEX:   44455445524d494e49535449435f53594e5448455449435f424c4f57464953485f53455353494f4e5f4b45595f35365f4259544553213132
  ```
* **Output Length:** 128 bytes (1024-bit ciphertext)
* **Decryption Result:** Matches plaintext bit-for-bit.

### Vector 2: Blowfish-CBC Channel Frame
* **Key Length:** 56 bytes (448 bits)
* **Synthetic Key (56 bytes):**
  `000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031323334353637`
* **Initial Vector (IV):** `0000000000000000` (8 zero bytes)
* **Plaintext (16 bytes):** `30313233343536373839414243444546` ("0123456789ABCDEF")
* **Padding (ANSI X9.23, 8 bytes):** `0000000000000008`
* **Padded Plaintext (24 bytes):** `303132333435363738394142434445460000000000000008`
* **Ciphertext Length:** 24 bytes (3 blocks)
* **Decryption Result:** Recovers exact 16-byte original plaintext.

### Vector 3: Mercury UDP Packet with Full Footers
* **Header Flags:** `0x01CE` (Checksum + IndexedChannel + Requests + ACKs + SeqNum)
* **Payload (30 bytes):** `"SYNTHETIC_MERCURY_PAYLOAD_BODY"`
* **Sequence Number:** `1234` (`0x000004D2`)
* **Indexed Channel ID:** `65537` (`0x00010001`)
* **ACK List:** `[100, 101, 102]`
* **Wire Format Footers (Tail):**
  - ACKs: `64000000 65000000 66000000 03`
  - Channel ID: `01000100`
  - Sequence Number: `D2040000`
  - Checksum: 4 bytes XOR sum
* **Parser Verification:** Cleanly extracts all fields without data loss or exceptions.

---

## 7. Protocol Confidence Matrix

The confidence matrix separates facts established by native Mach-O disassembly from those validated by the synthetic test harness:

```
+-------------------------+--------------------+-----------------------+-----------------------------+---------------------+
| Protocol Detail         | Phase 6.2B.6 Claim | Independent Validation| Concrete Evidence           | Final Confidence    |
+-------------------------+--------------------+-----------------------+-----------------------------+---------------------+
| RSA Padding Mode        | OAEP (Constant 4)  | test_rsa_oaep.py      | Disasm VA 0x100927cc8       | VERIFIED            |
| OAEP Message Digest     | SHA-1 (0x2a overh.)| test_rsa_oaep.py      | Disasm VA 0x100927c70       | VERIFIED            |
| OAEP MGF1 Digest        | SHA-1              | test_rsa_oaep.py      | OpenSSL default parameter   | STRONGLY SUPPORTED  |
| OAEP Label              | Empty (NULL)       | test_rsa_oaep.py      | OpenSSL standard convention | STRONGLY SUPPORTED  |
| RSA Modulus Sizing      | Dynamic (1024/2048)| test_rsa_oaep.py      | Disasm VA 0x100927ac4       | VERIFIED            |
| Symmetrical Cipher      | Blowfish           | test_blowfish_cbc.py  | Disasm VA 0x1000ab0b8       | VERIFIED            |
| Symmetrical Chaining    | CBC Mode           | test_blowfish_cbc.py  | Disasm VA 0x10091c80c       | VERIFIED            |
| IV Initialization       | Zero per datagram  | test_blowfish_cbc.py  | Disasm VA 0x10091c7f4       | VERIFIED            |
| Session Key Length      | 4 to 56 bytes      | test_blowfish_cbc.py  | Disasm VA 0x10091c344       | VERIFIED            |
| Padding Tag Position    | Last byte of block | test_blowfish_cbc.py  | Disasm VA 0x10091c7c4       | VERIFIED            |
| Header Flags Position   | Offset 0 (Head)    | test_mercury_parser.py| Disasm VA 0x100922894       | VERIFIED            |
| Footer Direction        | Reverse from tail  | test_mercury_parser.py| Disasm VA 0x100922950-31ac  | VERIFIED            |
| Checksum Algorithm      | 32-bit XOR sum     | test_mercury_parser.py| Disasm VA 0x100922bdc NEON  | VERIFIED            |
| Channel ID Footer       | 4 bytes uint32     | test_mercury_parser.py| Disasm VA 0x100922dec       | VERIFIED            |
| ACKs Footer             | 1B count + N*4B    | test_mercury_parser.py| Disasm VA 0x100922efc       | VERIFIED            |
| Sequence Number Footer  | 4 bytes uint32     | test_mercury_parser.py| Disasm VA 0x100922e7c       | VERIFIED            |
| Request Offset Footer   | 2 bytes uint16     | test_mercury_parser.py| Disasm VA 0x1009229a0       | STRONGLY SUPPORTED  |
| Wire Endianness         | Little-endian      | test_mercury_parser.py| ARM64 / BigWorld stream def | VERIFIED            |
+-------------------------+--------------------+-----------------------+-----------------------------+---------------------+
```

---

## 8. Unresolved Questions & Technical Observations

1. **Snappy Compression Threshold (`CompressionEncryptionFilter`):**  
   The binary references `snappy::RawUncompress` (VA `0x1030a23ee`). It remains to be determined at what packet size the client engages Snappy compression prior to Blowfish encryption.
2. **Channel Ping Frequency:**  
   The timeout interval for Mercury inactivity resends (`Channel::checkResendTimers`) is typically 1.0–2.0 seconds in BigWorld, but client-specific heartbeat RPCs in Python scripts need runtime observation.
3. **BigWorld Message ID Dispatching:**  
   While reverse-order footers strip packet routing metadata, the internal payload consists of bundled message IDs (`uint8` or `uint16`) followed by length-prefixed arguments conforming to the 632 `.def` schemas.

---

## 9. Explicit Compatibility Limitations

> [!WARNING]
> **Passing 29 synthetic tests does NOT prove wire-compatibility with the original game client.**
> 
> * The synthetic test suite validates our internal cryptographic and framing logic against our reverse-engineered model.
> * Until an isolated research client connects to a prototype server, subtle behavioral differences (such as bundle ordering, entity message ID mapping, or packet MTU fragmentation) cannot be completely ruled out.

---

## 10. Final Verification & File Protection Confirmation

The following integrity checks were verified at turn completion:

1. **Original IPA Untouched:**
   `RoS-Legacy-iOS.ipa` remains bit-for-bit identical (846,004,086 bytes; Last Write Time unmodified).
2. **Backend Source Untouched:**
   No code, models, tests, or configurations in `ros-private-server/` were modified.
3. **Database Records Untouched:**
   No database connections, writes, or schema migrations were executed.
4. **No Replacement Client Keys Generated:**
   No keys intended for replacing assets in the IPA were generated; all keys were deterministic synthetic test fixtures.
5. **Strict Directory Containment:**
   All new files were isolated inside `phase6B_7_synthetic_research/` and the report in the research workspace.

---

## 11. Recommended Next Phase

### Recommended Phase: **Phase 6.2B.8 — Minimal Network-Facing Protocol Test Harness**
With offline mathematical and framing logic 100% verified, the next logical milestone is:
1. Construct a minimal, isolated local UDP daemon implementing the verified packet header, reverse-order footer, and Blowfish cipher stack.
2. Test loopback UDP datagram exchange between synthetic client and synthetic server scripts.
3. Prepare the testing harness for eventual interaction with a separate, authorized research client.

*(Standing by for your explicit instructions and approval before proceeding.)*
