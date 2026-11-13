# ROS Sothat — Phase 6.2B.13.4 Audit Deliverable 3
## Protocol Independence & Verification Integrity Audit Report

**Phase:** Phase 6.2B.13.4 (Independent Audit)  
**Audit Target:** `D:\ROS-Legacy-Analysis\phase6B_13_3_udp_daemon\`  
**Target Focus:** Architecture decoupling, test independence, oracle separation, and circular validation risks  
**Audit Date:** 2026-11-13  
**Status:** AUDIT COMPLETE — RISKS IDENTIFIED AND MITIGATED  

---

### 1. Executive Summary

Audit 3 evaluated the methodological separation between the synthetic server prototype (`src/`), the network client (`UdpSyntheticClient`), the independent verification decoders (`independent_reference/`), and the cryptographic oracle. The primary objective is to verify whether the test suite's 100% pass rate represents genuine protocol compatibility or whether circular validation risks allow erroneous assumptions to pass silently.

The audit confirmed that **cryptographic verification is strictly independent and genuinely decoupled**, utilizing an external C library (`libcrypto-3-x64.dll`). However, **protocol-layer bundle construction exhibits partial coupling**, as the synthetic UDP client reuses server-side packet builders and parsers. These risks are counterbalanced by direct ARM64 disassembly verification of the original iOS Mach-O client.

---

### 2. Decoder Separation & Import Dependency Audit

#### A. Cryptographic Reference Module (`independent_reference/independent_blowfish.py`)
- **Import Analysis:**
  ```python
  from typing import Optional
  import ctypes
  import os
  from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
  from cryptography.hazmat.backends import default_backend
  ```
- **Finding:** The file contains **zero imports** from `src/`. It does not reference `src/blowfish_filter.py`, `src/loginapp_core.py`, `src/address.py`, or any prototype component.
- **Independence Status:** **100% INDEPENDENT.**

#### B. Interoperability Decoder (`tests/test_login_reply_interoperability.py`)
- **Import Analysis:**
  ```python
  from src.mercury_parser import MercuryParser
  from src.address import MercuryAddress
  from src.auth import LoginStatus
  from src.login_reply import LoginReplyBuilder, decode_bw_string
  from independent_reference.independent_blowfish import (
      IndependentBigWorldBlowfish, OpenSSLCryptoOracle
  )
  ```
- **Finding:** `IndependentClientDecoder` imports `MercuryParser` (for unpacking Mercury transport framing) and `decode_bw_string` (for error string decoding) from `src/`. However, it **does not import** the production cipher filter (`BlowfishAddressFilter`). It decrypts and verifies the payload strictly through `IndependentBigWorldBlowfish` or `OpenSSLCryptoOracle`.
- **Independence Status:** **CRYPTOGRAPHICALLY INDEPENDENT; FRAMING COUPLED.**

#### C. Network Client (`src/udp_synthetic_client.py`)
- **Import Analysis:**
  ```python
  from .mercury_parser import MercuryParser
  from .crypto import RsaOaepEngine
  from .synthetic_client import SyntheticLoginClient
  from .login_reply import decode_bw_string
  from independent_reference.independent_blowfish import IndependentBigWorldBlowfish
  ```
- **Finding:** `UdpSyntheticClient` delegates login datagram construction to `SyntheticLoginClient` (`src/synthetic_client.py`), which in turn depends on `LogonParamsEncoder` (`src/logon_params.py`) and `BundleParser` (`src/bundle_parser.py`).
- **Independence Status:** **COUPLED TO SERVER PACKET BUILDER.**

---

### 3. OpenSSL Oracle Independence

`OpenSSLCryptoOracle` in `independent_reference/independent_blowfish.py` was inspected:
1. **Dynamic Linkage:** It uses Python's `ctypes` to locate and load `libcrypto-3-x64.dll` directly from the OS environment (`C:\msys64\ucrt64\bin`, `C:\Program Files\Git\usr\bin`).
2. **C Function Signatures:**
   ```python
   lib.BF_set_key.argtypes = [ctypes.POINTER(BF_KEY), ctypes.c_int, ctypes.c_char_p]
   lib.BF_ecb_encrypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.POINTER(BF_KEY), ctypes.c_int]
   ```
3. **Execution Path:** Single-block Blowfish operations execute natively in C inside compiled OpenSSL assembly routines (`BF_set_key` and `BF_ecb_encrypt`).
4. **Chaining Implementation:** The BigWorld Plaintext-Chaining loop ($C_i = E_K(P_i \oplus P_{i-1})$) is implemented in Python, passing blocks one by one to the OpenSSL C function.

**Oracle Verdict:** The single-block cipher oracle is completely independent of the Python `cryptography` hazardous materials backend and custom server code.

---

### 4. Golden Vector Fixtures Assessment

The test fixtures in `fixtures/golden_vectors.json` contain 10 test cases:
- `GV01`–`GV03`: 1-block, 2-block, and 3-block chaining vectors.
- `GV04`–`GV05`: 24-byte Mercury address vectors for `127.0.0.1:20014` and `192.168.1.100:20013`.
- `GV06`: Mathematical proof of zero-padded address property ($C_1 = C_0$ when $P_1 = 0$).
- `GV07`–`GV09`: Unaligned length and invalid key length negative detectors.
- `GV10`: Bidirectional cross-oracle interoperability assertion.

**Verification Check:**
- In `tests/test_blowfish_golden_vectors.py`, every vector is tested against both `BlowfishAddressFilter` (production) and `IndependentBigWorldBlowfish` (reference), as well as `OpenSSLCryptoOracle` (native C).
- In addition, four negative detector tests prove that standard ECB mode and standard CBC mode **fail** on these vectors, demonstrating that BigWorld's plaintext-chaining cannot be falsely validated by standard cipher modes.

---

### 5. Identification of Circular Validation Risks

The audit identified three specific areas of circular validation risk:

```
+---------------------------------------------------------------------------------------+
|                               CIRCULAR VALIDATION MATRIX                              |
+---------------------------+-----------------------------------+-----------------------+
| Area                      | Mechanism of Circularity          | Severity & Mitigation |
+---------------------------+-----------------------------------+-----------------------+
| 1. Request Datagram       | UdpSyntheticClient builds packets | MEDIUM RISK           |
|    Serialization          | using server-side LogonParams-    | Mitigated by ARM64    |
|                           | Encoder and BundleParser.         | Disassembly checks.   |
+---------------------------+-----------------------------------+-----------------------+
| 2. Reply Payload          | Both server and test client       | HIGH RISK             |
|    Structure Assumption   | expect 24B address with 18 zeros. | Mitigated by ARM64    |
|                           | Slicing [6:24] ignores pad split. | Disassembly checks.   |
+---------------------------+-----------------------------------+-----------------------+
| 3. Transport Header       | Both client and server share      | LOW RISK              |
|    Flag Handling          | MercuryParser constants and logic | Verified against      |
|                           | (FLAG_HAS_REQUESTS, etc.).        | BigWorld 2.0.1 spec.  |
+---------------------------+-----------------------------------+-----------------------+
```

#### Detailed Risk Explanations:

#### Risk 1: Shared Request Encoder
If `LogonParamsEncoder` in `src/logon_params.py` serialized field 3 (Password) or field 4 (Session Key) with an incorrect wire offset, `SyntheticLoginApp`'s `BundleParser` would unpack it using the reciprocal assumption. Both the client test and the server would report success, while a native client would fail.
- **Mitigation:** In Audit 4, we verified that the ARM64 instructions at `0x1008992fc`–`0x100899580` match `LogonParamsEncoder` byte-for-byte (1B auth type, BW string username, BW string password, BW string 56B session key, 16B nonce, 4B flags).

#### Risk 2: Shared Reply Structure Assumption
As uncovered in Audit 2, both the server and the test client assume the decrypted address payload is 24 bytes and assert `padding == b'\x00' * 18`. If both sides are written by the same engineer with the same mental model, any divergence from native behavior would remain invisible to the test suite.
- **Mitigation:** In Audit 2, we disassembled `LoginHandler::onLoginReply` at `0x1008a8604` (`mov w1, #0x14`), proving that the native client unpacks 20 bytes and evaluates `cmp w8, #5`, which naturally accommodates the 24-byte payload.

#### Risk 3: Lack of Live Packet Capture (PCAP) Baseline
Because the original NetEase game servers have been decommissioned, the test suite cannot compare synthetic traffic against real-world packet captures.
- **Mitigation:** Architectural honesty dictates acknowledging Level 2 progress (localhost UDP) while deferring Level 3 claims (native physical iPhone compatibility) until live binary hook testing or network bridge testing is conducted.

---

### 6. Recommendations for Phase 14

1. **Implement Independent Wire Decoders for BaseApp:**  
   In Phase 14, avoid sharing `BundleParser` between the BaseApp daemon and synthetic BaseApp clients. Write a standalone, clean-room client parser that does not import server packet schemas.
2. **Explicit Address Struct Validation:**  
   Update synthetic client tests to assert:
   - `addr_bytes = decrypted[:20]` (Native `Mercury::Address` struct).
   - `cipher_pad = decrypted[20:24]` (Blowfish block alignment padding).
   This avoids conflating structural padding with cipher block padding.
3. **Retain OpenSSL C API Oracle:**  
   Continue using `OpenSSLCryptoOracle` as the gold standard for all subsequent multi-block cipher verifications in BaseApp and CellApp.
