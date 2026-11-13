# BigWorld RPC Message Bundle Boundary
## Demarcation Between Mercury Transport and Application RPC

---

### 1. Conceptual Framework

A fundamental architecture characteristic of the BigWorld Technology engine (and NetEase's derivative NeoX client) is the clear separation between:
1. **Mercury Transport Layer:** Responsible for UDP datagram transmission, packet reliability, sequence tracking (28-bit sequence numbers), fragment reassembly, packet piggybacking, and datagram-level Blowfish PBC encryption.
2. **BigWorld RPC Layer (`Mercury::Bundle`):** An application-level message stream multiplexer. Multiple distinct RPC calls, method invocations, and acknowledgments are serialized sequentially into a single byte stream called a **Bundle**, which is subsequently encapsulated into one or more Mercury packets.

```
+-----------------------------------------------------------------------------------------+
|                                    MERCURY PACKET                                       |
|  +---------------------+---------------------------------------+---------------------+  |
|  | Mercury Flags (2B)  |           BIGWORLD BUNDLE             |   Mercury Footer    |  |
|  | (0x0040, 0x0010,..) |  (One or more concatenated messages)  | (Seq, ACKs, ReqID)  |  |
|  +---------------------+---------------------------------------+---------------------+  |
+-----------------------------------------------------------------------------------------+
                                    |
                                    v
     +------------------------------+------------------------------+
     |                                                             |
     v                                                             v
+-----------------------------+               +-----------------------------+
|      RPC Message #1         |     ...       |      RPC Message #N         |
| +--------+--------+-------+ |               | +--------+--------+-------+ |
| | Msg ID | Length | Body  | |               | | Msg ID | Length | Body  | |
| |  (1B)  | (0-4B) | (var) | |               | |  (1B)  | (0-4B) | (var) | |
| +--------+--------+-------+ |               | +--------+--------+-------+ |
+-----------------------------+               +-----------------------------+
```

---

### 2. `Mercury::Bundle` Message Wire Framing

Every message packed into a BigWorld `Bundle` begins with a 1-byte Message ID, followed optionally by a length field, an optional Request ID (if the message expects a reply), and the application argument payload.

#### 2.1 Message ID Format
- **Type:** `uint8_t` (1 byte).
- **Value Range:** `0x00` through `0xFD` for defined interface methods.
- **Special Values:**
  - `0xFE` / `0xFF`: Reserved for system control and generic reply messages (`REPLY_MESSAGE`).
- **Native Disassembly:** In `Bundle::startMessage` at VA `0x100917bdc`–`0x100917be4`:
  ```arm64
  0x100917bdc: ldr  x8, [x20, #0x90]   ; x8 = pointer to InterfaceElement
  0x100917be0: ldrb w8, [x8]           ; w8 = InterfaceElement.id (uint8_t)
  0x100917be4: strb w8, [x0]           ; write 1-byte Message ID to stream
  ```

#### 2.2 Message Length Framing
The presence and format of length bytes are governed by the `InterfaceElement` specification:
- `lengthStyle_` (`0` = Fixed, `1` = Variable)
- `lengthParam_` (Number of fixed bytes, or width of variable length field)

##### Case 1: Fixed-Length Messages (`lengthStyle == 0`)
- **Length Overhead:** 0 bytes.
- The wire payload size is known implicitly by both sender and receiver from the interface definition table.
- Native code: `InterfaceElement::expandLength` at VA `0x10091dc04` confirms payload size equals `lengthParam_`.

##### Case 2: Variable-Length Messages (`lengthStyle == 1`)
Length is encoded in little-endian format immediately following the Message ID:
- **`VAR(1B)` (`lengthParam == 1`):** 1 byte length (`0x00`–`0xFE`). If length exceeds 254 bytes, an overflow error is generated.
- **`VAR(2B)` (`lengthParam == 2`):** 2 bytes little-endian `uint16_t` (`0x0000`–`0xFFFE`).
- **`VAR(3B)` (`lengthParam == 3`):** 3 bytes little-endian `uint24` (`0x000000`–`0xFFFFFE`).
- **`VAR(4B)` (`lengthParam == 4`):** 4 bytes little-endian `uint32_t`.

Native disassembly at VA `0x10091dd28`–`0x10091dd94` (`InterfaceElement::expandLength`):
```arm64
; Case 1: VAR(1B)
0x10091dc44: strb  w20, [x1, #1]       ; 1 byte length
; Case 2: VAR(2B)
0x10091dd94: sturh w20, [x1, #1]       ; 2 bytes length (uint16 LE)
; Case 3: VAR(3B)
0x10091dd28: strb  w20, [x1, #1]       ; byte 0
0x10091dd2c: lsr   w8, w20, #8
0x10091dd30: strb  w8, [x1, #2]        ; byte 1
0x10091dd34: lsr   w8, w20, #16
0x10091dd38: strb  w8, [x1, #3]        ; byte 2
; Case 4: VAR(4B)
0x10091dd50: stur  w20, [x1, #1]       ; 4 bytes length (uint32 LE)
```

#### 2.3 Request Message Framing
When a message expects a reply, the sender invokes `Bundle::startRequest` (VA `0x100917c04`):
1. Allocates 4 bytes for `requestID` (or `replyID`) immediately preceding the message argument stream:
   ```arm64
   0x100917c24: mov  w1, #4
   0x100917c28: mov  w2, #4
   0x100917c2c: bl   #0x100917d34      ; allocate 4 bytes on stream
   ```
2. Increments the packet's request counter at VA `0x100917cf8` (`strb w9, [x8, #0x30]`).
3. During packet finalization, Mercury flag `0x0001` (`HAS_REQUESTS`) is set on the packet header, and the `firstRequestID` is recorded in the Mercury packet footer.

---

### 3. Native Interface Tables

Through static disassembly of the interface registration routines in `extracted/Payload/client.app/client` (VA `0x1008cde00`–`0x1008ce300`), the complete interface tables have been mapped.

#### 3.1 `LoginInterface` (LoginApp Inbound RPC)
Registered at VA `0x1008cde04`–`0x1008cde7c` (`name = "LoginInterface"` at VA `0x10309d15e`).

| Message ID | Method Name | Length Style | Length Param | String VA | Purpose |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **`0x00`** | `login` | `VARIABLE` | 2 bytes (`uint16`) | `0x1030453ed` | Primary authentication request carrying `LogOnParams` |
| **`0x01`** | `probe` | `FIXED` | 0 bytes | `0x10309d16d` | Latency / server liveness probe |

#### 3.2 `BaseAppExtInterface` (BaseApp Inbound RPC)
Registered at VA `0x1008cde84`–`0x1008ce138` (`name = "BaseAppExtInterface"` at VA `0x10309d173`).

| Message ID | Method Name | Length Style | Length Param | Registration PC | Description |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **`0x00`** | `baseAppLogin` | `VARIABLE` | 2 bytes | `0x1008cdeac` | Initial session attachment to BaseApp |
| **`0x01`** | `authenticate` | `FIXED` | 4 bytes | `0x1008cded0` | Session token re-authentication |
| **`0x02`** | `avatarUpdateImplicit` | `FIXED` | 24 bytes | `0x1008cdef8` | Avatar position/physics update (implicit) |
| **`0x03`** | `avatarUpdateExplicit` | `FIXED` | 32 bytes | `0x1008cdf1c` | Avatar position/physics update (explicit) |
| **`0x04`** | `avatarUpdateWardImplicit` | `FIXED` | 24 bytes | `0x1008cdf40` | Ward / spectator update (implicit) |
| **`0x05`** | `avatarUpdateWardExplicit` | `FIXED` | 32 bytes | `0x1008cdf64` | Ward / spectator update (explicit) |
| **`0x06`** | `switchInterface` | `FIXED` | 0 bytes | `0x1008cdf88` | Interface state transition notification |
| **`0x07`** | `requestEntityUpdate` | `VARIABLE` | 2 bytes | `0x1008cdfac` | Request full entity state sync |
| **`0x08`** | `enableEntities` | `FIXED` | 8 bytes | `0x1008cdfd0` | Confirm client ready for entity population |
| **`0x09`** | `setSpaceViewportAck` | `FIXED` | 8 bytes | `0x1008cdff4` | Space viewport switch acknowledgment |
| **`0x0A`** | `setVehicleAck` | `FIXED` | 8 bytes | `0x1008ce018` | Boarding/vehicle transition acknowledgment |
| **`0x0B`** | `restoreClientAck` | `FIXED` | 4 bytes | `0x1008ce03c` | Client reconnection recovery acknowledgment |
| **`0x0C`** | `identifyVersionPoint` | `VARIABLE` | 2 bytes | `0x1008ce060` | Client resource version identification |
| **`0x0D`** | `summariseVersionPoint` | `VARIABLE` | 2 bytes | `0x1008ce084` | Resource manifest summary negotiation |
| **`0x0E`** | `commenceResourceDownload` | `VARIABLE` | 2 bytes | `0x1008ce0a8` | Dynamic patch resource streaming |
| **`0x0F`** | `disconnectClient` | `FIXED` | 1 byte | `0x1008ce0cc` | Clean client voluntary disconnect |
| **`0x10`** | `resourceVersionTag` | `FIXED` | 1 byte | `0x1008ce0f0` | Resource tag synchronization |
| **`0x11`** | `entityMessage` | `VARIABLE` | 2 bytes | `0x1008ce118` | Routed entity RPC / script call |

#### 3.3 `ClientInterface` (Client Inbound RPC)
Registered at VA `0x1008ce13c` (`name = "ClientInterface"` at VA `0x10309d2d9`).
Discovered handlers include:
- `createBasePlayer`: Instantiates local player entity upon BaseApp login.
- `createCellPlayer`: Transitions player into cell space / AoI.
- `createEntity` / `updateEntity`: Entity lifecycle management.
- `enterAoI` / `leaveAoI`: Area of Interest spatial subscription.
- `setGameTime`: Synchronizes server game tick.
- `resetEntities`: Wipes spatial entity table on teleport or disconnect.

---

### 4. Transport vs RPC Boundary Summary

| Feature | Mercury Transport Layer | BigWorld RPC Layer |
| :--- | :--- | :--- |
| **PDU Unit** | UDP Datagram (`Packet`) | Multiplexed Stream (`Bundle`) |
| **Header Fields** | Flags (`0x0001`–`0x0200`) | Message ID (`uint8_t`), Length (0–4B) |
| **Footer Fields** | Sequences, ACKs, Piggybacks | None (all within message body) |
| **Reliability Scope** | Retransmissions, Channel Sequences | Logical requests and responses (`replyID`) |
| **Encryption Scope** | Entire datagram (Blowfish PBC) | Application-level (RSA-OAEP during login only) |
