# ROS Sothat — Phase 6.2B.13.3 Localhost UDP LoginApp Daemon

## 1. Overview

This directory contains the operational localhost-only UDP LoginApp daemon developed for the ROS Sothat private-server project.

Building upon the remediated BigWorld Plaintext-Chained Blowfish cipher from Phase 6.2B.13.2, Phase 6.2B.13.3 transitions the synthetic LoginApp from an in-memory protocol simulator into a real, operational network daemon communicating over operating system UDP sockets.

> **CRITICAL ARCHITECTURAL BOUNDARY:**
> - **Operational Level:** Localhost UDP Daemon (`127.0.0.1:20013`).
> - **Scope:** Validated against separate network-based synthetic clients.
> - **Production Readiness:** This is an operational prototype, NOT yet an original iOS client-compatible production server. BaseApp transition and physical Wi-Fi networking are handled in subsequent phases.

---

## 2. Directory Layout

```
D:\ROS-Legacy-Analysis\phase6B_13_3_udp_daemon\
├── fixtures/
│   ├── golden_vectors.json               # 10 verified golden vectors
│   └── keys/                             # RSA-2048 offline key fixtures
├── independent_reference/
│   └── independent_blowfish.py           # Decoupled reference & OpenSSL C Oracle
├── src/
│   ├── loginapp_daemon.py                # ASYNCIO UDP DAEMON (127.0.0.1:20013)
│   ├── udp_synthetic_client.py           # SEPARATE REAL UDP SOCKET CLIENT
│   ├── blowfish_filter.py                # BigWorld Plaintext-Chained Blowfish
│   ├── loginapp_core.py                  # Core authentication pipeline
│   ├── login_reply.py                    # LoginReply builder and parser
│   ├── bundle_parser.py                  # BigWorld bundle pack/unpack
│   ├── mercury_parser.py                 # Mercury packet header framing
│   ├── logon_params.py                   # LogOnParams serializer/deserializer
│   ├── crypto.py                         # RSA-OAEP SHA-1 cryptographic engine
│   ├── session_manager.py                # Nonce replay & session management
│   ├── auth.py                           # Account repo & salt reversal
│   ├── address.py                        # MercuryAddress 24-byte packer
│   └── audit_logger.py                   # Structured log sanitizer
└── tests/
    ├── conftest.py                       # Python path discovery
    ├── test_udp_daemon.py                # 16 REAL LOCALHOST UDP INTEGRATION TESTS
    ├── test_blowfish_golden_vectors.py   # 14 golden vector and negative tests
    ├── test_login_reply_interoperability.py # 5 end-to-end interoperability tests
    └── test_synthetic_loginapp.py        # 16 original regression tests
```

---

## 3. How to Run

### 3.1 Running the UDP Daemon
```powershell
python -m src.loginapp_daemon --host 127.0.0.1 --port 20013 --key fixtures/keys/dev_loginapp_priv.pem
```

Expected startup output:
```
[LoginAppDaemon] Bound and listening on UDP 127.0.0.1:20013
```

### 3.2 Running the Master Test Suite (51 Automated Tests)
```powershell
python -m pytest tests -v
```

Expected summary:
```
============================= 51 passed in 15.86s =============================
```
