# ROS Sothat — Phase 6.2B.13.1 Independent Synthetic LoginApp Protocol Audit
## Final Audit Report and Synthesis

**Audit Authorization:** Phase 6.2B.13.1 Independent Read-Only Technical Audit  
**Audit Target:** `D:\ROS-Legacy-Analysis\phase6B_13_loginapp_prototype\`  
**Ground-Truth Reference:** Original iOS Mach-O Binary (`extracted/Payload/client.app/client`), BigWorld 2.0.1 Source Engine  
**Audit Date:** November 2026  
**Audit Status:** COMPLETE — READ-ONLY RESTRICTION FULLY MAINTAINED  

---

## 1. Executive Summary & Audit Verdict

This audit conducted an exhaustive, independent, and strictly read-only technical evaluation of the Phase 6.2B.13 Synthetic LoginApp Prototype developed for the ROS Sothat private-server research project.

The investigation examined all 11 prototype modules across `phase6B_13_loginapp_prototype/src/`, analyzed all 16 test cases in `tests/test_synthetic_loginapp.py`, verified security fixtures and logging safeguards, and cross-referenced every protocol field against ground-truth ARM64 disassembly in the original Rules of Survival Legacy client binary.

### Official Audit Verdict: **PASS WITH ISSUES**
*(Conditional approval to proceed to Phase 6.2B.14 planning, contingent upon mandatory remediation of the Blowfish cipher mode defect and implementation of the network transport daemon).*

```
+---------------------------------------------------------------------------------------+
|                               PHASE 6.2B.13.1 AUDIT SCORECARD                         |
+------------------------------------+------------+-------------------------------------+
| Evaluation Dimension               | Rating     | Key Audit Finding                   |
+------------------------------------+------------+-------------------------------------+
| Code Quality & Architecture        | EXCELLENT  | Clean modularity, 11 decoupled src  |
| Asymmetric Crypto (RSA-OAEP 2048)  | VERIFIED   | 100% native match (VA 0x1008773c0)  |
| Protocol Framing & Versioning      | VERIFIED   | Version 43, 28-bit sequence valid   |
| Password Salt Reversal             | VERIFIED   | 100% native match (VA 0x100877718)  |
| Address Block Layout (24 bytes)    | VERIFIED   | 100% native match (VA 0x1008a8604)  |
| Symmetric Crypto (Blowfish Filter) | DEFECT     | Prototype ECB vs Native Chained BF  |
| Test Independence & Oracles        | DEFECT     | Shared client code masked ECB defect|
| Transport Layer Readiness          | DEFECT     | In-memory only; no UDP daemon/port  |
| Security & Credential Hygiene      | EXCELLENT  | Zero leaks; strict log sanitization |
| Protected Binary Integrity         | VERIFIED   | 100% untouched baseline hashes      |
+------------------------------------+------------+-------------------------------------+
```

---

## 2. Synthesis: Verified Native Protocols vs Synthetic Constructs

### 2.1 Verified Native Protocol Features (`[VERIFIED NATIVE]`)
The prototype successfully achieves exact byte-level alignment with the native client binary in nine critical areas:
1. **Mercury Packet Header:** 1-byte flags (`FLAG_HAS_REQUESTS = 0x80`, `FLAG_HAS_SEQUENCE_NUMBER = 0x01`, `FLAG_HAS_ACKS = 0x02`), verified against Phase 6B.8.3 native disassembly.
2. **28-Bit Sequence Numbers:** Native Mercury 28-bit sequence number masking (`seq & 0x0FFFFFFF`), verified against Phase 6B.8.5 corrected gateway implementation.
3. **Request ID Correlation:** 32-bit little-endian `request_id` passed through request and echoed in reply bundle, enabling client-side `LoginHandler` callback routing.
4. **LogOn Protocol Version:** Version integer `43` (`0x0000002B`), verified at VA `0x1008772a0`.
5. **RSA Public Key Handshake:** RSA-2048 with OAEP padding and SHA-1 hash (`RSA_PKCS1_OAEP_PADDING`), verified at VA `0x1008773c0`.
6. **Blowfish Key Length:** 56-byte session key (`KEY_SIZE = 56`), verified against `EncryptionFilter::initKey` at VA `0x1030a211c`.
7. **Anti-Replay Nonce:** 64-bit (`uint64_t`) random client nonce extracted and checked against replay window.
8. **Password Salt Inversion:** Hardcoded salt prefix `"aec05336"` and byte decrement reversal (`ord(c) + 1` reversing `sub w23, w8, #1` at VA `0x100877718`).
9. **BaseApp Address Layout:** 20-byte native `Mercury::Address` (4B IP + 2B port + 14B sockaddr pad) padded to 24 bytes (multiple of 8), verified against `LoginHandler.baseAppAddr_` unpacking at VA `0x1008a8604` and `cmp w8, #5` at `0x1008a862c`.

### 2.2 Synthetic Server Conventions (`[SYNTHETIC ONLY]`)
The native iOS client disassembly reveals that client code at VA `0x1008a844c` evaluates **only** `status == 1` (`LOGON_STATUS_SUCCESS`). Any other status byte is immediately routed to the failure handler at VA `0x1008a84e0`, which reads the BigWorld error string and forwards it to the UI callback.

Therefore, the specific status codes defined in `src/auth.py` (`0x02` invalid password, `0x03` user not found, `0x04` banned, `0x05` server full, `0x06` version mismatch) are **synthetic server conventions**. They are harmless and safe to use because the client treats all non-1 statuses identically, displaying the accompanying server error string.

---

## 3. Critical Defects & Limitations Identified

### 3.1 Defect 1: Blowfish Cipher Mode Discrepancy (CRITICAL)
- **Disassembly Evidence:** Disassembly of `EncryptionFilter::decrypt` at VA `0x10091ca8c`–`0x10091cb80` and `EncryptionFilter::encrypt` at VA `0x10091c7f0`–`0x10091c834`, confirmed by BigWorld Technology 2.0.1 `encryption_filter.cpp`, proves that the native engine uses **BigWorld Plaintext-Chained Blowfish**:
  $$C_0 = E_K(P_0)$$
  $$C_i = E_K(P_i \oplus P_{i-1}) \quad \text{for } i \ge 1$$
- **Prototype Implementation:** `phase6B_13_loginapp_prototype/src/blowfish_filter.py` configured standard **Blowfish ECB** (`modes.ECB()`).
- **Technical Impact:** While Block 0 (bytes 0–7, containing the IP and Port) is identical between ECB and BigWorld Chaining, Blocks 1 and 2 (bytes 8–23, padding) differ. When decrypting an ECB address payload, the native client calculates $P_1' = D_K(C_1) \oplus P_0 = P_0$, injecting duplicate IP/port bytes into the address structure instead of zeroes. Furthermore, all subsequent multi-block Mercury packets on the encrypted BaseApp channel would fail decryption entirely.

### 3.2 Defect 2: Test Harness Circularity (METHODOLOGICAL)
- **Finding:** In `tests/test_synthetic_loginapp.py`, the test client `SyntheticLoginClient` was imported from `src/synthetic_client.py`, which directly imported `BlowfishAddressFilter` from `src/blowfish_filter.py`.
- **Impact:** Because both client and server shared the exact same ECB implementation, TC01 passed with a 100% success rate, giving false confidence and completely concealing the cipher mode defect.

### 3.3 Limitation 1: In-Memory Protocol Simulator vs Active Network Daemon
- **Finding:** In `src/loginapp_core.py`, `SyntheticLoginApp` only exposes `handle_datagram(datagram, client_ip)`.
- **Impact:** There is no active UDP socket bound, no `asyncio.DatagramProtocol`, and no process listening on port 20013. The prototype cannot receive packets over a real network interface without a network daemon wrapper.

---

## 4. Phase 14 Remediation Roadmap

Prior to connecting an original iOS client in Phase 14, the following three targeted remediations must be executed:

```
+---------------------------------------------------------------------------------------+
|                           PHASE 14 MANDATORY REMEDIATION ROADMAP                      |
+-----+-------------------------------+-------------------------------------------------+
| No. | Component                     | Required Technical Action                       |
+-----+-------------------------------+-------------------------------------------------+
|  1  | src/blowfish_filter.py        | Replace modes.ECB() with BigWorld Plaintext-    |
|     |                               | Chaining: Ci = E_K(Pi ^ Pi-1).                  |
+-----+-------------------------------+-------------------------------------------------+
|  2  | src/loginapp_daemon.py        | Implement asyncio.DatagramProtocol daemon       |
|     |                               | binding to 0.0.0.0:20013 with CLI runner.       |
+-----+-------------------------------+-------------------------------------------------+
|  3  | tests/test_golden_vectors.py  | Implement independent golden byte vector tests  |
|     |                               | decoupled from src/ modules.                    |
+-----+-------------------------------+-------------------------------------------------+
```

### 4.1 Plaintext-Chained Blowfish Implementation Reference
```python
# BigWorld Plaintext-Chained Blowfish Cipher for Phase 14 remediation:
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

class BigWorldBlowfishFilter:
    def __init__(self, key: bytes):
        self.key = key
        self.cipher = Cipher(algorithms.Blowfish(key), modes.ECB(), backend=default_backend())

    def encrypt(self, data: bytes) -> bytes:
        assert len(data) % 8 == 0
        encryptor = self.cipher.encryptor()
        out = bytearray(len(data))
        prev_p = 0
        for i in range(0, len(data), 8):
            p_val = int.from_bytes(data[i:i+8], 'little')
            xored = p_val ^ prev_p if i > 0 else p_val
            block = xored.to_bytes(8, 'little')
            out[i:i+8] = encryptor.update(block)
            prev_p = p_val
        return bytes(out)

    def decrypt(self, data: bytes) -> bytes:
        assert len(data) % 8 == 0
        decryptor = self.cipher.decryptor()
        out = bytearray(len(data))
        prev_p = 0
        for i in range(0, len(data), 8):
            decrypted = decryptor.update(data[i:i+8])
            d_val = int.from_bytes(decrypted, 'little')
            p_val = d_val ^ prev_p if i > 0 else d_val
            out[i:i+8] = p_val.to_bytes(8, 'little')
            prev_p = p_val
        return bytes(out)
```

---

## 5. Protected Binary Integrity Verification

In strict compliance with project constraints, the integrity of the original iOS game application was re-verified at the conclusion of this audit.

```
Target File: RoS-Legacy-iOS.ipa
Expected SHA-256: D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55
Actual SHA-256:   D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55
Integrity Status: 100% MATCH — ZERO BYTES MODIFIED

Target File: extracted/Payload/client.app/client
Expected SHA-256: 51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6
Actual SHA-256:   51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6
Integrity Status: 100% MATCH — ZERO BYTES MODIFIED
```

---

## 6. Audit Conclusion & Deliverable Sign-Off

The Phase 6.2B.13 Synthetic LoginApp Prototype establishes a solid, well-engineered foundation for the ROS Sothat private server project. It successfully implements the complex mathematical and cryptographic handshakes required by BigWorld Mercury protocols.

With the discovery and precise documentation of the **BigWorld Plaintext-Chained Blowfish mechanism** and the **transport daemon requirements**, the project now possesses complete technical clarity to proceed to **Phase 6.2B.14 (Operational Network Daemon & BaseApp Transition Implementation)** under controlled conditions.

### Deliverables Inventory in `phase6B_13_1_independent_audit/`:
1. `loginapp_code_review.md` (Module-by-module architectural and code audit)
2. `protocol_evidence_comparison.md` (Detailed native disassembly vs prototype matrix)
3. `test_independence_review.md` (Analysis of 16 tests and circular test harness)
4. `transport_implementation_status.md` (Assessment of in-memory simulator vs network daemon)
5. `security_review.md` (Audit of key management, nonces, rate limiting, and log privacy)
6. `phase6B_13_1_final_report.md` (Final audit synthesis and Phase 14 remediation roadmap)
