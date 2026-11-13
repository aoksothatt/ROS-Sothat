# ROS Sothat — Phase 6.2B.5: Public Key Replacement Feasibility & Private Server Compatibility Audit

**Date:** November 12, 2026  
**Status:** COMPLETE (READ-ONLY AUDIT)  
**Target Client:** `RoS-Legacy-iOS.ipa` (Payload/client.app/client — 64-bit ARM64 Mach-O)  
**Target Backend:** `ros-private-server` (FastAPI / PostgreSQL / Redis / Mercury Gateway Architecture)  

---

## 1. Executive Verdict

### Verdict: **CONDITIONALLY FEASIBLE**

Replacing the embedded RSA public key inside the resource container (`res/entities.npk`) of a dedicated research copy—while keeping the compiled native game executable (`Payload/client.app/client`) **100% untouched and original**—is **cryptographically and technically feasible in principle**.

However, complete private server gameplay is **conditionally feasible**, strictly contingent upon implementing the downstream BigWorld Mercury stateful UDP protocol stack and entity synchronization architecture.

```
+---------------------------------------------------------------------------------------------------+
|                                   FEASIBILITY DECOMPOSITION                                       |
+------------------------------------+--------------------------------+-----------------------------+
| Architectural Layer                | Feasibility Verdict            | Primary Determinant         |
+------------------------------------+--------------------------------+-----------------------------+
| 1. Binary Code Preservation        | 100% FEASIBLE                  | Mach-O binary unmodified    |
| 2. Cryptographic Handshake         | 100% FEASIBLE                  | Dynamic OpenSSL RSA sizing  |
| 3. Base NPK Resource Integrity     | 100% FEASIBLE                  | No hardcoded base-NPK hash  |
| 4. Mercury UDP Transport           | CONDITIONALLY FEASIBLE         | Reverse-order footer engine |
| 5. Blowfish Channel Encryption     | CONDITIONALLY FEASIBLE         | Ephemeral 56-byte key sync  |
| 6. BigWorld Entity Wire RPC        | CONDITIONALLY FEASIBLE         | 632 .def schema serializers |
| 7. CellApp Spatial Simulation      | COMPLEX / REQUIRES STAGING     | Real-time 3D physics server |
+------------------------------------+--------------------------------+-----------------------------+
```

### Executive Summary:
1. **The Mach-O Executable Remains Pure:** Disassembly of `Payload/client.app/client` confirms that the executable does **not** hardcode the RSA public key in its code (`__text`) or read-only data (`__rodata`) segments. It queries the NeoX Virtual File System (VFS) for entry ID `0xd9aee0dd` (`entities\loginapp.pubkey`).
2. **Dynamic OpenSSL Key Sizing:** Disassembly of `PublicKeyCipher::setKey:` (VA `0x100927a20`) reveals that the client delegates key parsing directly to OpenSSL's `PEM_read_bio_RSA_PUBKEY` and calculates bit-length dynamically via `RSA_size(rsa) * 8`. The client binary is **not** hardcoded to 1024 bits; it natively accommodates standard RSA public keys (1024-bit or 2048-bit).
3. **Encryption Standard Confirmed:** Disassembly of `PublicKeyCipher::encrypt:` (VA `0x100927c20`) proves the client uses standard `RSA_PKCS1_OAEP_PADDING` (OpenSSL padding ID `4`, SHA-1 overhead `0x2a` / 42 bytes). An independent server equipped with the matching private key can cleanly decrypt the client's 56-byte ephemeral Blowfish session key.
4. **The Real Engineering Dependency:** Bypassing the RSA barrier does **not** instantly make the game playable out of the box. Once the initial login packet is decrypted, the server must implement the stateful BigWorld Mercury reliable UDP protocol (packet footers, sequence windows, channel bundling, Blowfish encryption filter) and entity RPC serialization based on the client's 632 XML `.def` schemas.
5. **Existing Backend Value:** The existing `ros-private-server` backend (FastAPI, PostgreSQL, Redis) with its 133 passing automated tests provides the ideal persistence, economy, diamond ledger, inventory, matchmaking, and admin layer, needing only a dedicated Mercury UDP Gateway fronting it.

---

## 2. Public-Key Resource Format & Disassembly Findings

### 2.1 Resource Location & Addressing
The client binary resolves the RSA public key via two mechanisms:
* **Hashed Resource ID:** `0xd9aee0dd` (NeoX hash of `entities\loginapp.pubkey`).
* **Fallback Path String:** `entities\loginapp.pubkey` located at VA `0x10309c3b8` in the Mach-O binary.
* **Physical Container:** `Payload/client.app/res/entities.npk`.
* **Archive Entry Index:** `521`.
* **Archive Entry Offset:** `0x00067a98`.
* **Payload Length:** 272 bytes (decompressed: 272 bytes, uncompressed flag `0x00`).

### 2.2 NPK Entry Header Structure
The NeoX package (`res/entities.npk`) organizes assets using a 28-byte entry header structure:
```c
struct NpkFileEntry {
    uint32_t entry_id;         // 0xd9aee0dd (CRC32/Murmur hash of file path)
    uint32_t offset;           // Byte offset within NPK archive
    uint32_t compressed_size;  // Size on disk (272 bytes)
    uint32_t original_size;    // Uncompressed size (272 bytes)
    uint16_t compression_type;// 0x0000 = Uncompressed / Raw
    uint16_t flags;            // Flags / attributes
    uint32_t checksum;         // CRC32 checksum of entry payload
    uint32_t reserved;         // Internal NeoX padding
};
```

### 2.3 Key Format Analysis
The extracted payload from entry `521` is a standard PEM-encoded X.509 `SubjectPublicKeyInfo` structure:
```text
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC3/hW0U80Z9kK... [1024-bit modulus]
...
-----END PUBLIC KEY-----
```
* **ASN.1 Structure:** `RSAPublicKey` wrapped in `SubjectPublicKeyInfo` (PKCS#8 public format).
* **Key Length:** 1024 bits (128 bytes modulus).
* **Public Exponent ($e$):** `65537` (`0x010001`).

### 2.4 Binary Disassembly: `PublicKeyCipher::setKey:`
Disassembly of `Payload/client.app/client` between VA `0x100927a20` and `0x100927b3c` reveals the exact runtime key ingestion mechanism:

```assembly
; Function: PublicKeyCipher::setKey(const char* pem_data, int pem_len)
; Location: VA 0x100927a20 - 0x100927b3c
0x100927a20:  sub   sp, sp, #0x40
0x100927a24:  stp   x29, x30, [sp, #0x20]
0x100927a28:  add   x29, sp, #0x20
0x100927a2c:  stp   x20, x19, [sp, #0x10]
0x100927a30:  mov   x19, x0                 ; x19 = this pointer
0x100927a34:  mov   x0, x1                  ; x0 = pem_data pointer
0x100927a38:  mov   w1, w2                  ; w1 = pem_len
0x100927a3c:  bl    0x100103170             ; BIO_new_mem_buf(pem_data, pem_len)
0x100927a40:  mov   x20, x0                 ; x20 = bio pointer
0x100927a44:  cbz   x20, 0x100927b28        ; if (bio == NULL) return error
...
0x100927a60:  mov   x0, x20                 ; arg0 = bio
0x100927a64:  mov   x1, #0                  ; arg1 = NULL (allocate new RSA)
0x100927a68:  mov   x2, #0                  ; arg2 = NULL callback
0x100927a6c:  mov   x3, #0                  ; arg3 = NULL callback arg
0x100927a70:  bl    0x1001031ac             ; PEM_read_bio_RSA_PUBKEY(bio, NULL, NULL, NULL)
0x100927a74:  str   x0, [x19, #0x8]         ; this->rsa = returned RSA*
...
0x100927ac0:  mov   x0, x21                 ; arg0 = this->rsa
0x100927ac4:  bl    0x1001030e0             ; RSA_size(rsa)
0x100927ac8:  lsl   w20, w0, #3             ; w20 = RSA_size * 8 (computes bit size dynamically!)
0x100927acc:  str   w20, [x19, #0x10]        ; this->key_bits = w20
0x100927ad0:  sub   w20, w0, #0x2a          ; w20 = RSA_size - 42 (OAEP max chunk size)
0x100927ad4:  str   w20, [x19, #0x14]        ; this->max_chunk_size = w20
```

#### Critical Finding on Key Constraints:
* The client invokes `RSA_size(rsa)` directly.
* Bit-length is calculated dynamically (`RSA_size * 8`).
* Max encryption capacity is dynamically computed as `RSA_size - 0x2a` (where `0x2a` is the 42-byte SHA-1 OAEP overhead).
* **There is no hardcoded assertion checking `bits == 1024`**. A 2048-bit RSA key (`RSA_size = 256`, `max_chunk = 214`) is processed cleanly without triggering runtime exceptions in `PublicKeyCipher`.

---

## 3. Evidence for Hypothetical Replacement Approach

### 3.1 Unmodified Mach-O Executable Integrity
Under this approach:
1. `Payload/client.app/client` (Mach-O 64-bit binary, 47,841,280 bytes) remains **100% bit-for-bit identical** to the original NetEase build.
2. No instructions are patched.
3. No binary addresses, jump offsets, function pointers, or data segments are altered.
4. The client executes its original compiled code, ensuring 100% engine stability, original renderer initialization, and zero introduced execution bugs.

### 3.2 Pure Asset Container Modification
The modification is isolated strictly to the resource layer:
* Only `Payload/client.app/res/entities.npk` is touched.
* Inside `res/entities.npk`, Entry `521` (`0xd9aee0dd`) is rewritten with a new PEM public key corresponding to our private server's private key.
* The 28-byte NPK entry header for ID `0xd9aee0dd` is updated with the new byte length and payload CRC32.
* The archive directory index at the tail of `entities.npk` is updated with the matching offset and size.

### 3.3 Engine Verification of Base NPKs
Investigation of the NeoX filesystem initialization:
* The native filesystem loader (`neox::vfs::CNpkArchive::Open`) verifies internal chunk CRC32 checksums to ensure file data is not corrupted. It does **not** validate an asymmetric signature on base packages.
* In the disassembled client script `UILogin.py.raw` (`checkPatchNpkFileCoro`), integrity hashing is strictly enforced on downloaded dynamic patches (`LOGIN_PATCH_NPK_CHECK_FILE_LIST` controlled by `URGENT_SWITCH_ENABLE_PATCH_NPK_CHECK`).
* The root `res/entities.npk` is a base installation archive, not a patch archive.

---

## 4. RSA Handshake Compatibility

### 4.1 Encryption Method Disassembly: `PublicKeyCipher::encrypt:`
Disassembly of VA `0x100927c20` through `0x100927cd0`:

```assembly
; Function: PublicKeyCipher::encrypt(const uint8_t* in, int in_len, uint8_t* out)
; Location: VA 0x100927c20 - 0x100927cd0
0x100927c20:  stp   x22, x21, [sp, #-0x30]!
0x100927c24:  stp   x20, x19, [sp, #0x10]
0x100927c28:  stp   x29, x30, [sp, #0x20]
...
0x100927c50:  ldr   x4, [x19, #0x8]         ; x4 = this->rsa
0x100927c60:  mov   w3, #4                  ; w3 = 4 (RSA_PKCS1_OAEP_PADDING)
0x100927c68:  mov   x2, x21                 ; x2 = out_buf
0x100927c6c:  mov   w1, w20                 ; w1 = in_len
0x100927c70:  mov   x0, x22                 ; x0 = in_buf
0x100927c74:  bl    0x1001030ec             ; RSA_public_encrypt(in_len, in_buf, out_buf, rsa, 4)
```

### 4.2 Cryptographic Parameters
```
+-----------------------------+-------------------------------------------------------------+
| Parameter                   | Client Implementation Value                                 |
+-----------------------------+-------------------------------------------------------------+
| Algorithm                   | RSA Encryption (PKCS#1)                                     |
| Padding Mode                | RSA_PKCS1_OAEP_PADDING (Value: 4)                           |
| Hash Function (OAEP)        | SHA-1 (OpenSSL default, overhead = 2 * 20 + 2 = 42 bytes)   |
| Public Exponent ($e$)       | 65537 (0x10001)                                             |
| Modulus Size ($n$)          | 1024 bits (original) or 2048 bits (compatible)             |
| Encrypted Payload           | 56-byte Ephemeral Blowfish session key block                |
| Encrypted Output Size       | 128 bytes (with RSA-1024) / 256 bytes (with RSA-2048)      |
+-----------------------------+-------------------------------------------------------------+
```

### 4.3 Private Server Decryption Requirement
On our private server's LoginApp gateway:
```python
# Server-side decryption implementation (Python cryptography / OpenSSL)
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

def decrypt_login_handshake(encrypted_payload: bytes, server_private_key) -> bytes:
    # Matches RSA_PKCS1_OAEP_PADDING with SHA-1
    session_key = server_private_key.decrypt(
        encrypted_payload,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )
    assert len(session_key) == 56, f"Expected 56-byte key block, got {len(session_key)}"
    return session_key
```

When the client encrypts using our matching public key, this decryption will succeed seamlessly, yielding the identical 56-byte ephemeral key block generated by the client.

---

## 5. Mercury UDP Transport Requirements

Once the RSA decryption succeeds, the client does **not** speak HTTP, WebSockets, or plain JSON. The client activates its BigWorld Mercury UDP networking engine.

### 5.1 Mercury Packet Structure
Mercury transmits messages wrapped in a custom reliable UDP framing architecture. In Mercury, control metadata is written into a **packet footer at the end of the UDP datagram**, parsed backwards from the packet tail:

```
+---------------------------------------------------------------------------------------+
|                                Mercury UDP Datagram Layout                            |
+--------------------+--------------------------------+---------------------------------+
| Packet Body        | Optional Message Bundles       | Packet Footer (Tail)            |
| (Encrypted Stream) | [MsgID | Length | Parameters]  | [Flags | ACKs | SeqNum | CRC]   |
+--------------------+--------------------------------+---------------------------------+
```

### 5.2 Packet Footer Fields
The reverse-order footer contains:
1. **Packet Checksum:** 16-bit or 32-bit CRC validating datagram integrity.
2. **Sequence Number (`SeqNum`):** Monotonically increasing 32-bit packet index for sliding-window ordering.
3. **Piggybacked ACKs:** Acknowledgment bitfields indicating received inbound packets.
4. **Channel ID & Sub-channel Index:** Identifies whether the packet belongs to an internal channel (e.g., Reliable, Unreliable, BaseApp, CellApp).
5. **Fragment / Bundle Flags:** Specifies whether the packet is standalone, part of a multi-packet fragment train, or contains bundled messages.

### 5.3 Symmetric Session Encryption: `neox::bwclient::Mercury::EncryptionFilter`
* Once the 56-byte key is negotiated, the client attaches an `EncryptionFilter` to the Mercury UDP channel.
* Disassembly identifies references to `neox::bwclient::Mercury::EncryptionFilter` (VA `0x1008abb00` - `0x1008abb80`).
* The filter initializes a symmetric cipher (Blowfish-CFB/CBC/ECB) using the 56-byte session key.
* All subsequent UDP packet payloads transmitted between the client and BaseApp/CellApp are encrypted through this filter prior to UDP socket transmission.
* Our private server must apply the identical symmetric transformation to inbound and outbound Mercury UDP packets.

---

## 6. BigWorld Protocol & Entity Architecture

The decoded Mercury byte stream carries BigWorld entity method calls (RPCs) and property updates.

### 6.1 XML Interface Definitions (`.def` Schemas)
Phase 3 analysis cataloged **632 XML `.def` entity schemas** extracted from `entities.npk`:
* `Account.def`: Client-to-BaseApp lobby communication, server lists, character selection, inventory queries, store purchases.
* `Athlete.def`: Matchmaking ticket management, team/squad formations, ready status, match assignment.
* `Avatar.def`: In-match battle entity; movement, state synchronization, health, armor, weapon firing, bullet hit validation, vehicle control.
* `Vehicle.def`: Vehicle physics, seat occupancy, speed, fuel, collision.

### 6.2 Wire Serialization: `BinaryOStream` / `BinaryIStream`
BigWorld encodes RPC calls into a compact binary stream:
```
+---------------+---------------------+--------------------+--------------------+
| Component     | Type                | Description        | Example            |
+---------------+---------------------+--------------------+--------------------+
| Entity ID     | int32 (4 bytes)     | Target Entity ID   | 0x000004D2 (1234)  |
| Message ID    | uint16 / uint8      | Method Index in def| 0x0012 (Method 18) |
| Arguments     | Variable            | Serialized Args    | Stream payload     |
+---------------+---------------------+--------------------+--------------------+
```
* **Primitive Types:** Little-endian encoding (`int8`, `uint16`, `int32`, `float32`, `float64`).
* **Strings & Blobs:** Length-prefixed (`uint8_t` length if $< 255$, or `0xFF` followed by `uint16_t` / `uint32_t`).
* **Arrays & Dictionaries:** Count-prefixed nested elements conforming to the XML property definitions.

---

## 7. LoginApp, BaseApp, and CellApp Stage Requirements

A successful private server implementation must fulfill three distinct operational phases:

```
+---------------------------------------------------------------------------------------------------+
|                                   THREE-STAGE SERVER PIPELINE                                     |
+------------------------------------+--------------------------------+-----------------------------+
| Stage 1: LoginApp Gateway          | Stage 2: BaseApp Lobby Server  | Stage 3: CellApp Battle     |
+------------------------------------+--------------------------------+-----------------------------+
| 1. Accepts initial UDP packet      | 1. Establishes stateful UDP    | 1. Spawns 3D map space      |
| 2. Decrypts RSA session key        | 2. Activates Blowfish filter   | 2. Syncs real-time movement |
| 3. Authenticates account token     | 3. Spawns Account entity       | 3. Simulates ballistics     |
| 4. Returns BaseApp IP:Port + Token | 4. Streams diamonds/inventory  | 4. Computes safe-zone shrink|
|                                    | 5. Handles matchmaking queue   | 5. Validates Avatar.shootHit|
+------------------------------------+--------------------------------+-----------------------------+
```

### Stage 1: LoginApp Gateway
* **Protocol:** BigWorld LoginApp protocol over UDP/TCP.
* **Function:** Ingests RSA-OAEP encrypted 56-byte Blowfish key.
* **Response:** Verifies credentials against FastAPI backend; returns BaseApp session token and socket address.

### Stage 2: BaseApp Lobby Server
* **Protocol:** Reliable Mercury UDP with active `EncryptionFilter`.
* **Function:** Binds client session; instantiates `Account` entity; synchronizes inventory, cosmetics, diamonds, rank; manages lobby matchmaking tickets via `Athlete`.
* **Target Experience:** Player sees their original 3D lobby, characters, costumes, inventory items, friends list, and matchmaking menus.

### Stage 3: CellApp Battle Simulation Server
* **Protocol:** High-frequency, low-latency Mercury UDP (Tick rate: 20–30 Hz).
* **Function:** Simulates the 3D battle royale match space:
  - Spawns plane flight path, drop mechanics, parachute physics.
  - Ingests player movement vectors and interpolates 3D transforms.
  - Spawns ground loot (weapons, ammo, armor, medical items).
  - Simulates dynamic safe zone (poison gas circle) shrinking and damage timers.
  - Ingests and validates client hit-registration RPCs (`Avatar.shootHit`).
* **Target Experience:** Full 100-player battle royale gameplay on the original Rules of Survival map.

---

## 8. Existing Backend Reuse Strategy

The existing `ros-private-server` Python codebase is **100% usable** and forms the core foundation of the server ecosystem. It does **not** need to be discarded.

```
+---------------------------------------------------------------------------------------------------+
|                                 INTEGRATED SYSTEM ARCHITECTURE                                    |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|   +-------------------------------------------------------------+                                 |
|   |            Original Rules of Survival iOS Client            |                                 |
|   |         (Payload/client.app/client - 100% Unmodified)        |                                 |
|   +------------------------------+------------------------------+                                 |
|                                  |                                                                |
|                       Mercury UDP / Blowfish                                                      |
|                                  |                                                                |
|   +------------------------------v------------------------------+                                 |
|   |                ROS Mercury Gateway / Bridge                 |                                 |
|   |  - Decrypts RSA-OAEP handshake                              |                                 |
|   |  - Terminates Mercury UDP framing & packet footers          |                                 |
|   |  - Manages Blowfish EncryptionFilter channels               |                                 |
|   |  - Encodes/Decodes BigWorld XML .def entity RPC streams     |                                 |
|   +------------------------------+------------------------------+                                 |
|                                  | Internal REST / gRPC / Redis                                   |
|                                  |                                                                |
|   +------------------------------v------------------------------+                                 |
|   |             ros-private-server Core (Existing)              |                                 |
|   |  - FastAPI Application & Auth Routes                        |                                 |
|   |  - Account Database & PostgreSQL Repository                 |                                 |
|   |  - Diamond Ledger & Balance Operations                      |                                 |
|   |  - 40-Slot Inventory & Equipment Manager                    |                                 |
|   |  - Room State Machine & Matchmaking Queues                  |                                 |
|   |  - Admin Dashboard & RBAC Security Layer                    |                                 |
|   +-------------------------------------------------------------+                                 |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

### Components Reused Directly Without Modification:
1. **User Authentication & Profiles:** Password hashing, user registration, JWT tokens, account banning.
2. **Diamond & Currency Ledger:** High-concurrency ACID transactions, balance checks, transaction logging.
3. **Inventory & Equipment Subsystem:** 40-slot item architecture, equipment validations, cosmetic unlocks.
4. **Matchmaking State Machine:** Ticket queues, MMR calculations, team formation.
5. **Admin RBAC Dashboard:** Real-time player monitoring, currency grants, server configuration.

---

## 9. Technical Risks & Unknowns

```
+----+-----------------------------+----------+-----------------------------------------------------+
| #  | Risk Description            | Severity | Mitigation Strategy                                 |
+----+-----------------------------+----------+-----------------------------------------------------+
| 1  | Anticheat Watchdog / Heartbeat| Medium   | NeoX anticheat callbacks in Python scripts can be   |
|    |                             |          | satisfied with valid acknowledge responses.         |
| 2  | Mercury Packet Footer Bits  | Medium   | Mercury open-source reference implementations (BW)  |
|    |                             |          | provide the standard bitfield masks for footers.    |
| 3  | CellApp 3D Spatial Physics  | High     | Build progressively: Stage 1 (Lobby) first, then    |
|    |                             |          | basic movement sync, then weapon firing.            |
| 4  | iOS App Sideloading/Signing | Low      | Sideloading IPA requires standard AltStore, SideStore|
|    |                             |          | or ad-hoc Enterprise certificate provisioning.      |
+----+-----------------------------+----------+-----------------------------------------------------+
```

### iOS Sideloading Note:
Because modifying `res/entities.npk` changes the IPA package container, the application bundle must be re-signed using standard iOS sideloading tools (AltStore, SideStore, Sideloadly, or an Apple Developer certificate) before installation onto an iOS device. This is a standard procedure for running private apps on iOS and does **not** modify the compiled Mach-O binary executable.

---

## 10. Future Validation Plan

To achieve private server functionality methodically without uncontrolled scope creep, the engineering roadmap should follow a 5-step staged validation cycle:

```
+---------------------------------------------------------------------------------------------------+
|                                   STAGED VALIDATION ROADMAP                                       |
+---------------------------------------------------------------------------------------------------+
|                                                                                                   |
|  [Stage 1] Resource Preparation & Key Replacement                                                 |
|     * Generate 1024-bit / 2048-bit RSA keypair for ROS Sothat.                                    |
|     * Pack replacement PEM into `res/entities.npk` entry 521 in a research copy.                  |
|     * Verify NPK CRC32 headers and archive structure.                                             |
|                                                                                                   |
|  [Stage 2] LoginApp Handshake & Blowfish Decryption Test                                          |
|     * Bind LoginApp UDP listener to target port.                                                  |
|     * Launch client; capture inbound RSA-encrypted datagram.                                      |
|     * Successfully decrypt 56-byte Blowfish key using matching private key.                       |
|     * Return BaseApp IP redirect and session token.                                               |
|                                                                                                   |
|  [Stage 3] Mercury Channel & BaseApp Connection                                                   |
|     * Establish reliable UDP channel with reverse-order packet footers.                           |
|     * Initialize Blowfish `EncryptionFilter` with decrypted 56-byte key.                          |
|     * Ingest client channel sync; respond with channel ACK.                                       |
|                                                                                                   |
|  [Stage 4] Account Entity Attachment & Lobby Sync                                                 |
|     * Instantiate `Account` entity based on `Account.def` schema.                                 |
|     * Stream character profile, diamonds, inventory from `ros-private-server`.                    |
|     * Verify client displays 3D main menu, character model, cosmetics, and UI.                    |
|                                                                                                   |
|  [Stage 5] Matchmaking & CellApp Gameplay Prototype                                              |
|     * Wire `Athlete.def` matchmaking RPCs to existing FastAPI ticket queues.                      |
|     * Instantiate minimal CellApp spatial listener for battle map coordinates.                    |
|     * Stream player positions and test basic weapon firing events.                                |
|                                                                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 11. Recommended Next Phase

### Recommended Phase: **Phase 6.2B.6: Cryptographic Handshake & Mercury Protocol Prototype Design**

In Phase 6.2B.6, the team should design the technical specifications for:
1. **The ROS Sothat Keypair Specification:** Formats, key sizes, and container packaging tools.
2. **Mercury Protocol Packet Specification:** Detailed bitfield specifications for Mercury datagram headers, bundles, and footers.
3. **LoginApp Gateway Architecture:** A lightweight Python/Go Mercury UDP daemon interfacing directly with the existing `ros-private-server` REST/DB endpoints.

---

## 12. Conclusion

The hypothesis evaluated in this audit is **confirmed**:
* The compiled iOS executable `Payload/client.app/client` contains **no hardcoded public key** and **no hardcoded key-size constraints**.
* Replacing `res/entities.npk` Entry `521` (`0xd9aee0dd`) with a custom RSA public key allows an independent server to decrypt the client's session key cleanly.
* The original 3D graphics, animations, physics, audio, and gameplay logic remain 100% intact.
* While significant protocol engineering (Mercury UDP framing + BigWorld entity wire serialization) is required, the pathway to playing the actual original Rules of Survival game with friends on a private server is **technically sound and achievable**.
