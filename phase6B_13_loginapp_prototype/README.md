# ROS Sothat — Synthetic LoginApp Prototype
## Phase 6.2B.13 Isolated Implementation

---

### 1. Overview

This directory contains the isolated synthetic `LoginApp` prototype for the ROS Sothat private-server project.

It provides a complete, tested Python implementation of the native BigWorld / Mercury authentication pipeline:
- Mercury UDP transport framing and footer demuxing.
- BigWorld RPC bundle demuxing (`LoginInterface::login`, Message ID `0x00`).
- RSA-OAEP SHA-1 asymmetric envelope decryption.
- `LogOnParams` deserialization (with `aec05336` salt reversal).
- Replay attack protection (128-bit client nonce tracking).
- In-memory synthetic account authentication.
- BaseApp address encryption (Blowfish 56-byte key).
- `LoginReply` handshake construction (Status `0x01` success and error replies).

---

### 2. Directory Structure

```
phase6B_13_loginapp_prototype/
├── .gitignore                      # Excludes private keys and test artifacts
├── README.md                       # Setup and execution guide
├── protocol_assumptions.md         # Protocol ground truth and verified evidence
├── implementation_report.md        # Implementation summary and test results
├── independent_verification_report.md # Final integrity and verification report
├── fixtures/
│   └── keys/
│       ├── README.md               # Warning: Synthetic development keys only
│       ├── dev_loginapp_priv.pem   # Synthetic RSA-2048 private key (fixture)
│       ├── dev_loginapp_pub.der    # DER public key (for entities/loginapp.pubkey)
│       └── dev_loginapp_pub.pem    # PEM public key
├── src/
│   ├── __init__.py
│   ├── mercury_parser.py           # Mercury flags & 28-bit sequence footer parser
│   ├── bundle_parser.py            # BigWorld bundle & string codec
│   ├── crypto.py                   # RSA-OAEP SHA-1 decryption engine
│   ├── logon_params.py             # LogOnParams serializer & salt decoder
│   ├── auth.py                     # Synthetic account repository & status codes
│   ├── session_manager.py          # Session tracking & nonce replay defense
│   ├── address.py                  # 20-byte/24-byte Mercury::Address struct
│   ├── blowfish_filter.py          # Blowfish address block cipher
│   ├── login_reply.py              # LoginReply datagram builder & parser
│   ├── audit_logger.py             # Structured JSON audit logger (zero secret leak)
│   ├── loginapp_core.py            # Central SyntheticLoginApp pipeline
│   └── synthetic_client.py         # Test harness client for automated tests
└── tests/
    └── test_synthetic_loginapp.py  # 16 automated pytest scenarios (100% passing)
```

---

### 3. How to Run Tests

From the project root (`D:\ROS-Legacy-Analysis\`):

```powershell
python -m pytest "D:\ROS-Legacy-Analysis\phase6B_13_loginapp_prototype\tests\test_synthetic_loginapp.py" -v
```

Expected output:
```
============================= 16 passed in 2.61s ==============================
```

---

### 4. Safety & Isolation Guarantees

1. **Zero External Network Traffic:** All tests operate strictly in-memory or on local loopback.
2. **Zero Database Impact:** Uses an isolated in-memory user repository; does not connect to production or development databases.
3. **Protected Assets Untouched:** The original Mach-O executable and `.ipa` archive are 100% byte-for-byte identical to baseline.
