# ROS Sothat — Phase 6.2B.13.4 Audit Deliverable 2
## LoginReply Address Layout Forensic Audit Report (CRITICAL)

**Phase:** Phase 6.2B.13.4 (Independent Audit)  
**Audit Target:** `D:\ROS-Legacy-Analysis\phase6B_13_3_udp_daemon\`  
**Target Focus:** `Mercury::Address` binary layout, Blowfish decryption, and report inconsistency  
**Audit Date:** 2026-11-13  
**Status:** FORENSIC AUDIT COMPLETE — ROOT CAUSE ISOLATED  

---

### 1. The Investigated Inconsistency

The Phase 6.2B.13.3 and Phase 6.2B.13.2 reports contain the following mutually contradictory assertions regarding the successful `LoginReply` address block:
1. They assert a **24-byte decrypted address payload**.
2. They assert a **20-byte `Mercury::Address` structure**.
3. They assert **18 trailing zero padding bytes**.

#### The Arithmetic Paradox:
$$\text{IPv4 Endpoint Data} = 4 \text{ bytes (IP)} + 2 \text{ bytes (Port)} = 6 \text{ bytes}$$
- If a structure is **20 bytes**, it can contain at most $20 - 6 = \mathbf{14}$ bytes of internal padding.
- If a structure has **18 trailing zero bytes**, its total length is $6 + 18 = \mathbf{24}$ bytes, making it impossible to be a 20-byte structure.

This audit conducted an exhaustive byte-level and disassembly inspection across the source code, test suites, golden vector fixtures, and the original iOS Mach-O client binary (`extracted/Payload/client.app/client`) to determine the exact ground truth.

---

### 2. Native iOS Client Disassembly Evidence (ARM64)

Direct analysis of the protected Mach-O binary at `extracted/Payload/client.app/client` establishes the exact native execution flow for `LoginReply` handling inside `LoginHandler::onLoginReply`:

#### A. Decryption Boundary and Block Alignment Assertion
```arm64
// Location: client Mach-O VA 0x1008a85e8 - 0x1008a85f0
0x1008a85e8: mov x0, x21          // Cipher filter object (EncryptionFilter)
0x1008a85ec: mov x1, x20          // Input stream (BinaryIStream containing reply payload)
0x1008a85f0: bl  #0x10091ca8c     // EncryptionFilter::decrypt

// Location: EncryptionFilter::decrypt at VA 0x10091caf4
0x10091caf4: tst w19, #7          // Assert (length & 7) == 0 (must be multiple of 8 bytes)
0x10091caf8: b.eq #0x10091cb2c    // Proceed to Blowfish PBC decryption
0x10091cafc: mov w8, #8           // Failure: input length is not an 8-byte multiple
0x10091cb04: adrp x0, #0x1030a2000 // Error log string
0x10091cb0c: bl  #0x101b634c0     // Abort decryption
```
**Fact 1:** The encrypted payload passed into `EncryptionFilter::decrypt` **MUST** be an integer multiple of 8 bytes (`tst w19, #7`). An input of 20 bytes is strictly rejected with an error. Therefore, the on-the-wire Blowfish ciphertext **must be at least 24 bytes** ($3 \times 8$).

#### B. Stream Unpacking into `baseAppAddr_`
```arm64
// Location: LoginHandler::onLoginReply at VA 0x1008a85f8 - 0x1008a861c
0x1008a85f8: ldr x8, [sp, #0x30]  // Decrypted stream (BinaryIStream)
0x1008a85fc: ldr x8, [x8, #0x10]  // Virtual method: BinaryIStream::retrieve(int nBytes)
0x1008a8600: mov x0, x21          // Stream pointer
0x1008a8604: mov w1, #0x14        // nBytes = 0x14 = 20 BYTES DECIMAL!
0x1008a8608: blr x8               // Retrieve exactly 20 bytes from decrypted stream
0x1008a860c: add x24, x19, #0x50  // x24 = &LoginHandler.baseAppAddr_
0x1008a8610: ldr q0, [x0]         // Load 16 bytes (128-bit vector) from stream buffer
0x1008a8614: ldr w8, [x0, #0x10]  // Load 4 bytes (32-bit word) from offset 16 (0x10)
0x1008a8618: str w8, [x24, #0x10] // Store 4 bytes into baseAppAddr_ + 16
0x1008a861c: str q0, [x24]        // Store 16 bytes into baseAppAddr_
```
**Fact 2:** The native client retrieves **exactly 20 bytes (`0x14`)** from the decrypted stream and stores them into the 20-byte in-memory structure `baseAppAddr_` (`x19 + 0x50`).

#### C. Unread Stream Inspection and Cookie Branch
```arm64
// Location: LoginHandler::onLoginReply at VA 0x1008a8620 - 0x1008a8660
0x1008a8620: ldr w8, [sp, #0x48]  // Stream write/end position
0x1008a8624: ldr w9, [sp, #0x58]  // Stream read position (now 20)
0x1008a8628: sub w8, w8, w9       // Remaining unread bytes = total_decrypted - 20
0x1008a862c: cmp w8, #5           // Compare remaining unread bytes with 5
0x1008a8630: b.lt #0x1008a86e8    // If remaining < 5, BRANCH TO BASEAPP CONNECT!
// ... (optional session key rotation check at 0x1008a8654: 0x32ef9816)
0x1008a86e8: ldr w0, [x24]        // Load IPv4 address (offset 0 of baseAppAddr_)
0x1008a86f4: bl  #0x100916a94     // inet_ntop(AF_INET, ...)
```
**Fact 3:** When the server sends a 24-byte payload, the client reads 20 bytes for the address, leaving $24 - 20 = 4$ unread bytes in the decrypted stream. At line `0x1008a862c`, the client evaluates `cmp w8, #5`. Since $4 < 5$, `b.lt #0x1008a86e8` triggers immediately, bypassing cookie checking and jumping directly to connecting to the BaseApp address. The 4 trailing bytes are harmlessly discarded by the client stream teardown.

#### D. Structure Field Usage
```arm64
// Location: Address field accesses in LoginHandler
0x1008a872c: ldr  w8, [x19, #0x50] // Offset 0: 32-bit uint32 IPv4 address
0x1008a87b8: ldrh w4, [x19, #0x54] // Offset 4: 16-bit uint16 UDP port
```
**Fact 4:** Inside the 20-byte `baseAppAddr_` struct:
- Offset `0..3` (4 bytes): `ip` (network byte order uint32).
- Offset `4..5` (2 bytes): `port` (network byte order uint16).
- Offset `6..19` (14 bytes): Unused in IPv4 mode. In Darwin/NetEase IPv6 conversion mode (`Address::convertToIPV6` at VA `0x100916b80`), this storage holds the 128-bit IPv6 address and socket family indicators.

---

### 3. Source Code and Test Implementation Inspection

#### A. Server Serialization (`src/address.py` and `src/login_reply.py`)
In `phase6B_13_3_udp_daemon/src/address.py`:
```python
def pack_20b(self) -> bytes:
    """Serializes endpoint into raw 20-byte Mercury::Address struct."""
    ip_bytes = socket.inet_aton(self.ip)       # 4 bytes
    port_bytes = struct.pack('!H', self.port)   # 2 bytes
    padding = b'\x00' * 14                      # 14 bytes struct alignment
    return ip_bytes + port_bytes + padding      # EXACTLY 20 BYTES

def pack_24b(self) -> bytes:
    """Serializes endpoint into 24 bytes (padded to multiple of 8 for Blowfish)."""
    raw_20 = self.pack_20b()
    return raw_20 + (b'\x00' * 4)               # 4 bytes Blowfish block padding
```
In `phase6B_13_3_udp_daemon/src/login_reply.py`, line 43:
```python
addr_plain_24 = baseapp_addr.pack_24b()
addr_encrypted = BlowfishAddressFilter.encrypt(addr_plain_24, session_key)
```
**Code Finding 1:** The server implementation **correctly** distinguishes between the 20-byte native `Mercury::Address` struct (`pack_20b()`) and the 24-byte Blowfish block-aligned payload (`pack_24b()`).

#### B. Client Decoder Slicing (`src/udp_synthetic_client.py` and tests)
In `phase6B_13_3_udp_daemon/src/udp_synthetic_client.py`, lines 135–144:
```python
decrypted_addr = self.independent_blowfish.decrypt(encrypted_addr)
assert len(decrypted_addr) == 24

ip_bytes = decrypted_addr[0:4]
port_bytes = decrypted_addr[4:6]
padding = decrypted_addr[6:24]      # 24 - 6 = 18 BYTES!

result["ip"] = socket.inet_ntoa(ip_bytes)
result["port"] = struct.unpack("!H", port_bytes)[0]
result["padding"] = padding
```
In `tests/test_login_reply_interoperability.py`, line 121:
```python
assert decoded["padding"] == b"\x00" * 18
```
In `tests/test_udp_daemon.py`, line 100:
```python
assert res["padding"] == b"\x00" * 18
```
In `tests/test_udp_daemon.py`, line 313 (TC16):
```python
expected_addr = socket.inet_aton("127.0.0.1") + (20014).to_bytes(2, "big") + (b"\x00" * 18)
assert ossl_plain == expected_addr
```
**Code Finding 2:** The synthetic client decoder and test fixtures treat the entire 24-byte decrypted block as a single monolithic unit. Because the first 6 bytes are IP and port, the decoder treats the remaining $24 - 6 = 18$ bytes as a single `padding` slice (`decrypted_addr[6:24]`).

---

### 4. Root Cause Determination: Report Error vs Implementation Error

| Component | Code / Text Statement | Correct? | Explanation |
| :--- | :--- | :--- | :--- |
| **Server Code** (`src/address.py`) | `pack_20b()` (20B) + 4B pad = `pack_24b()` (24B) | **YES** | Accurately models the 20B struct and 4B cipher pad. |
| **Server Builder** (`login_reply.py`) | Encrypts 24 bytes via Blowfish PBC | **YES** | Matches native client assertion `tst w19, #7`. |
| **Native iOS Binary** (`client`) | Reads 20B (`0x14`), ignores remaining 4B | **YES** | Native client behavior at `0x1008a8604` & `0x1008a862c`. |
| **Phase 13.2 / 13.3 Reports** | *"extracting the exact 20-byte Mercury::Address with 18 trailing zero bytes"* | **NO (ERROR)** | **Documentation error.** A 20-byte address cannot contain 18 trailing zero bytes. |
| **Client Decoder** (`udp_synthetic_client.py`) | Slices `decrypted_addr[6:24]` as 18B `padding` | **IMPRECISE** | Functionally valid on wire, but conflates struct pad with cipher pad. |

#### Root Cause Conclusion:
The inconsistency in the Phase 6.2B.13.3 report was a **documentation conflation / phrasing error**, NOT an implementation or wire protocol failure:
1. The author of the report observed that in the 24-byte decrypted block, the endpoint is represented by 6 bytes of data (4B IP + 2B port) followed by 18 zero bytes.
2. The author conflated the **20-byte `Mercury::Address` struct** with the **24-byte decrypted Blowfish payload**, mistakenly writing that the 20-byte struct contained 18 trailing zeroes.
3. The underlying server implementation in `src/address.py` and `src/login_reply.py` is **100% correct and compatible** with the native Mach-O binary.

---

### 5. Definitive Ground Truth Specifications

To eliminate future ambiguity in Phase 14, the exact binary layout is formally documented:

#### A. Decrypted Payload Length
- **Exact Size:** **24 bytes** ($3 \times 8$-byte Blowfish blocks).

#### B. `Mercury::Address` In-Memory Field Layout (20 bytes)
```
+---------------+---------------+---------------------------------------+
| Offset (Hex)  | Length (Bytes)| Field Description                     |
+---------------+---------------+---------------------------------------+
| 0x00 .. 0x03  |    4 bytes    | IPv4 Address (Network Byte Order)     |
| 0x04 .. 0x05  |    2 bytes    | UDP Port (Network Byte Order)         |
| 0x06 .. 0x13  |   14 bytes    | Internal Struct Alignment / Reserved  |
+---------------+---------------+---------------------------------------+
| TOTAL SIZE    |   20 bytes    | Native Mercury::Address Struct        |
+---------------+---------------+---------------------------------------+
```

#### C. Wire Encryption Payload Layout (24 bytes)
```
+---------------+---------------+---------------------------------------+
| Offset (Hex)  | Length (Bytes)| Payload Component                     |
+---------------+---------------+---------------------------------------+
| 0x00 .. 0x03  |    4 bytes    | IP Address                            |
| 0x04 .. 0x05  |    2 bytes    | UDP Port                              |
| 0x06 .. 0x13  |   14 bytes    | Internal Struct Padding (Zeros)       |
| 0x14 .. 0x17  |    4 bytes    | Blowfish 8-Byte Block Alignment Pad   |
+---------------+---------------+---------------------------------------+
| TOTAL SIZE    |   24 bytes    | Decrypted Blowfish Block (3 x 8B)     |
+---------------+---------------+---------------------------------------+
```

#### D. Padding Breakdown
- **Internal Struct Padding:** Exactly **14 bytes** (`0x00 * 14`).
- **Transport Alignment Padding:** Exactly **4 bytes** (`0x00 * 4`).
- **Total Consecutive Trailing Zeroes:** Exactly **18 bytes** ($14 + 4 = 18$).
- **Padding Classification:**
  - The 14 bytes are an intrinsic structural attribute of `Mercury::Address` in NetEase's BigWorld fork (allocated for IPv6 expansion).
  - The 4 bytes are strictly an encryption transport requirement imposed by Blowfish 64-bit block alignment (`round_up_8(20) = 24`).
