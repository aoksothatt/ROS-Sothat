# ROS Sothat — Phase 6.2B.13.3 Transport Architecture Specification

## 1. Overview & System Context

Phase 6.2B.13.3 implements the network transport layer for the ROS Sothat synthetic LoginApp.

Prior to this phase, the LoginApp operated solely as an in-memory protocol library (`SyntheticLoginApp.handle_datagram(data: bytes)`). The daemon architecture introduced in `src/loginapp_daemon.py` wraps the verified core inside an asynchronous network service communicating over operating system UDP sockets bound strictly to `127.0.0.1:20013`.

---

## 2. Transport Layer Architecture

```
+---------------------------------------------------------------------------------------+
|                               OS Network Stack (Loopback)                             |
|                                     127.0.0.1:20013                                   |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v  (Raw UDP Datagram)
+---------------------------------------------------------------------------------------+
|                             LoginAppProtocol (asyncio)                                |
|  - connection_made: Logs startup & captures sockname.                                 |
|  - datagram_received:                                                                 |
|      * Empty Packet Guard: Rejects 0-byte datagrams.                                  |
|      * Oversized Packet Guard: Drops packets > 2048 bytes.                            |
|      * Async Offloading: Dispatches processing to thread pool.                       |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v  (concurrent.futures ThreadPool)
+---------------------------------------------------------------------------------------+
|                             SyntheticLoginApp Core Pipeline                           |
|  1. Rate Limiting Check (Token Bucket / Window per IP).                               |
|  2. Mercury Header Framing (Flags, 28-bit sequence number).                           |
|  3. BigWorld Bundle Unpacking (MsgID 0x00, Version 43).                               |
|  4. RSA-OAEP SHA-1 Decryption (256B -> Plaintext LogOnParams).                        |
|  5. LogOnParams Deserialization & Salt Reversal ('aec05336' + byte decrement).       |
|  6. Replay Check (64-bit client nonce cache).                                         |
|  7. In-Memory Authentication.                                                         |
|  8. Address Encryption (BigWorld Plaintext-Chained Blowfish with 56B session key).     |
|  9. LoginReply Bundle Formatting (0xFF reply frame, correlated request ID).           |
+-------------------------------------------+-------------------------------------------+
                                            |
                                            v  (Reply Datagram Bytes)
+---------------------------------------------------------------------------------------+
|                               transport.sendto(reply, addr)                           |
+---------------------------------------------------------------------------------------+
```

---

## 3. Protocol & Daemon Component Details

### 3.1 Non-Blocking Asynchronous Concurrency
Asymmetric RSA-2048 OAEP private-key decryption consumes approximately 1–2 milliseconds of CPU time per request. Executing this operation directly on the `asyncio` event loop thread would block all socket I/O, leading to dropped datagrams under concurrent client bursts.

`LoginAppProtocol` resolves this bottleneck by delegating execution to the default thread pool executor:
```python
loop = asyncio.get_running_loop()
reply_bytes = await loop.run_in_executor(
    None,
    self.app.handle_datagram,
    data,
    client_ip
)
```
This design guarantees that the socket receiver continues buffering incoming packets while worker threads compute cryptographic transformations.

### 3.2 Datagram Size & Input Validation
- **Empty Datagrams:** Dropped immediately without invoking processing logic.
- **Oversized Datagrams:** Standard Mercury login bundles are ~300–400 bytes. Datagrams exceeding `MAX_DATAGRAM_SIZE = 2048` bytes are dropped and increment the `packets_dropped` metric.
- **Malformed Frames:** All exceptions inside `_process_datagram_async` are caught, incrementing `error_count` without crashing the daemon process.

### 3.3 Loopback Binding Enforcement
To strictly comply with security directives prohibiting exposure on public interfaces or local networks:
```python
if host not in ("127.0.0.1", "localhost"):
    raise ValueError(
        f"Security Violation: LoginApp daemon is restricted to 127.0.0.1 (localhost). "
        f"Attempted bind to '{host}' is strictly forbidden."
    )
```

---

## 4. UDP Synthetic Client Architecture

`src/udp_synthetic_client.py` implements `UdpSyntheticClient`, an operational client harness that communicates strictly via operating system UDP sockets:
1. Opens `socket.socket(socket.AF_INET, socket.SOCK_DGRAM)`.
2. Sends the binary login datagram to `127.0.0.1:20013`.
3. Waits for the reply with a 2.0-second timeout.
4. Independently decodes the binary reply:
   - Validates `0xFF` BigWorld reply message ID.
   - Correlates 32-bit `request_id`.
   - Decrypts the 24-byte address payload using `IndependentBigWorldBlowfish`.
   - Asserts the 4-byte IP, 2-byte port, and 18 zero padding bytes.
5. Zero calls to `SyntheticLoginApp` internal methods.
