# ROS Sothat — Phase 6.2B.13.1 Transport Implementation Status

## 1. Executive Summary

This document evaluates the operational transport readiness of the Phase 6.2B.13 Synthetic LoginApp Prototype (`phase6B_13_loginapp_prototype/`).

The audit concludes that while Phase 13 successfully implemented the binary serialization and deserialization formats for Mercury packet headers and BigWorld bundle frames, **the prototype does not contain an active network transport layer**. The current codebase is an **in-memory protocol simulator and codec library**, not an operational network daemon. It cannot bind to a network port, listen on UDP sockets, or receive datagrams over the wire from an external iOS client or testing tool.

---

## 2. In-Memory Protocol Simulator vs Operational Network Daemon

### 2.1 Code Inspection of `src/loginapp_core.py`
The primary entry point of the prototype is the `SyntheticLoginApp` class in `phase6B_13_loginapp_prototype/src/loginapp_core.py`:

```python
class SyntheticLoginApp:
    def __init__(self, private_key_pem: bytes, ...):
        # Initializes in-memory managers (auth, session, rate_limiter, audit)
        ...

    def handle_datagram(self, datagram: bytes, client_ip: str = "127.0.0.1") -> Optional[bytes]:
        """Process a single incoming Mercury UDP datagram in memory."""
        ...
        return reply_bytes
```

### 2.2 Absence of Operating System Network Calls
A codebase-wide search across `phase6B_13_loginapp_prototype/` reveals:
- **Zero occurrences** of `socket.socket()`, `socket.bind()`, or `socket.recvfrom()`.
- **Zero occurrences** of `asyncio.DatagramProtocol` or `loop.create_datagram_endpoint()`.
- **Zero occurrences** of background listener threads or event loops.
- **Zero CLI entry points** or runner scripts (`__main__.py`, `server.py`, or `run.py`).

The prototype can only be executed by passing raw `bytes` directly into the `handle_datagram` method within a Python interpreter session or automated test runner.

---

## 3. Mercury Transport Layer Feature Assessment

| Transport Feature | Required Native Behavior | Current Prototype Status | Gap / Limitation |
| :--- | :--- | :--- | :--- |
| **Datagram I/O** | Active UDP socket bound to `0.0.0.0:20013`. | **NOT IMPLEMENTED** | Cannot receive packets over physical or virtual network interfaces. |
| **Mercury Packet Framing** | 1-byte flags + optional 4-byte sequence + optional request/ack counts. | **IMPLEMENTED** (`MercuryParser`) | Fully handles native header structure for single packets. |
| **28-Bit Sequence Handling** | Sequence numbers wrapped at $2^{28}-1$ ($0x0FFFFFFF$). | **IMPLEMENTED** (`MercuryParser`) | Correctly packs and extracts sequence numbers. |
| **Request Correlation** | 4-byte `request_id` mapped between request bundle and reply bundle. | **IMPLEMENTED** (`BundleParser`) | Tracks and mirrors client `request_id` in response. |
| **Single-Packet Bundles** | Login request/reply contained entirely within one UDP MTU ($\le 1472$ B). | **IMPLEMENTED** (`BundleParser`) | Fully supported for typical login payloads (~300–400 B). |
| **Multi-Packet Bundles** | Fragmented bundles spanning multiple UDP datagrams (`FLAG_IS_FRAGMENT`). | **NOT IMPLEMENTED** | If a client packet exceeds MTU, parsing will abort or truncate. |
| **Channel State Machine** | Reliable channel (`Mercury::Channel`) with sequence ACKs and retransmits. | **NOT IMPLEMENTED** | Unreliable channel handling only; ACKs are extracted but not tracked in window. |
| **Packet Loss & Retries** | Retransmit unacknowledged packets after RTT-based timeout. | **NOT IMPLEMENTED** | Relies entirely on client-side retransmission if datagram is dropped. |
| **Graceful Shutdown** | Handling OS signals (`SIGINT`, `SIGTERM`), flushing logs, closing sockets. | **NOT IMPLEMENTED** | No daemon lifecycle management exists. |

---

## 4. Architectural Analysis: Why In-Memory Was Acceptable for Phase 13

In Phase 6.2B.13, the primary objective was to validate:
1. RSA-2048 OAEP decryption of the native client's LogOnParams payload.
2. Extraction and negotiation of the 56-byte Blowfish session key.
3. Verification of the password salting prefix (`"aec05336"`).
4. Generation of the 24-byte zero-padded BaseApp address payload.

Isolating the cryptographic and structural parsing logic from operating system socket I/O allowed the developer to construct rapid, deterministic, and sandboxed unit tests without requiring network port allocation or OS firewall permissions.

However, **it is critical to distinguish between a verified codec library and a deployable server**. Claiming that the ROS Sothat LoginApp is "functional" would be misleading until an active UDP daemon is implemented.

---

## 5. Blueprint for Phase 14 Network Daemon Implementation

To bridge the gap between the in-memory simulator and an operational private server daemon in Phase 14, the following transport components must be constructed:

### 5.1 Architecture Design (`src/loginapp_daemon.py`)
```
+-------------------------------------------------------+
|                Operating System Network Stack         |
|                     UDP Port 20013                    |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
|             asyncio.DatagramProtocol                  |
|  - datagram_received(data, addr)                      |
|  - error_received(exc)                                |
|  - sendto(reply_data, addr)                           |
+---------------------------+---------------------------+
                            |
                            v
+-------------------------------------------------------+
|             SyntheticLoginApp Core Engine             |
|  - IP Rate Limiting                                   |
|  - Mercury Packet Parsing                             |
|  - Bundle & Crypto Processing                         |
|  - Login Reply Generation                             |
+-------------------------------------------------------+
```

### 5.2 Key Daemon Requirements
1. **Asynchronous Non-Blocking I/O:**
   - Use Python's built-in `asyncio` event loop with `create_datagram_endpoint`.
   - Support concurrent datagram handling without blocking the event loop on crypto operations (offload RSA-2048 decryption to `loop.run_in_executor` or a thread pool worker).
2. **Configuration & CLI Runner:**
   - Command-line arguments (`--host`, `--port`, `--private-key`, `--baseapp-ip`, `--baseapp-port`, `--log-level`).
   - Sensible production defaults (`0.0.0.0:20013`, BaseApp at `127.0.0.1:20014`).
3. **Signal & Exception Handling:**
   - Graceful capture of `SIGINT` (Ctrl+C) and `SIGTERM`.
   - Comprehensive exception guards in `datagram_received` to prevent daemon termination on malformed datagrams.
4. **Health & Prometheus Metrics (Optional/Future):**
   - Datagram counters (received, processed, rejected, rate-limited, dropped).
