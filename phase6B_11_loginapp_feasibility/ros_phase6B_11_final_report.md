# ROS Sothat — Phase 6.2B.11 Final Report
# Untouched Executable Resource Packaging and LoginApp Implementation Feasibility

**Author:** Antigravity (Google DeepMind Team)  
**Project:** ROS Sothat — Original Rules of Survival Legacy iOS Private Server  
**Mode:** Strict Read-Only Technical Feasibility Investigation  
**Date:** November 13, 2026  
**Status:** COMPLETED — STRICT READ-ONLY AUDIT  

---

## 1. Executive Summary

Phase 6.2B.11 conducted an in-depth, strictly read-only technical feasibility audit into **Approach B (Level 2)**: preserving the original Mach-O executable (`client`) 100% byte-for-byte, providing the private server's public key (`entities/loginapp.pubkey`) via standard application resource packaging, and designing the private `LoginApp` authentication pipeline.

Through static ARM64 disassembly, symbol cross-referencing, NPK binary format extraction, and iOS security analysis, we have confirmed:

1. **The Mach-O Executable Can Remain 100% Untouched:**  
   The native game binary contains zero hardcoded public keys and natively looks up `"entities\\loginapp.pubkey"` via `BWResource::openSection` (VA `0x10093e078`).
2. **NPK Modification is Not Required:**  
   The NeoX Virtual File System (VFS) queries discrete loose files in `%APP_DIR%/` before scanning `.npk` archives. Placing `entities/loginapp.pubkey` directly into `Payload/client.app/entities/` satisfies the engine's lookup without modifying `script.npk` or recalculating archive checksums.
3. **iOS Code Signing Reality:**  
   Apple Mobile File Integrity (AMFI) cryptographically seals all bundle resources via `_CodeSignature/CodeResources`. Adding the public key requires generating a new `CodeResources` file and re-signing the application bundle with a developer or personal certificate. Crucially, the Mach-O machine code (`__TEXT, __text`) and data sections remain **100% bit-for-bit identical**.
4. **LoginApp Wire Format is Fully Mapped:**  
   The native login request (`LoginInterface::login`, MsgID `0x00`, `LOGIN_VERSION = 43`, RSA-OAEP SHA-1 encryption, 56-byte client Blowfish key) and handshake reply format (`LoginReply`, `LOGON_STATUS_SUCCESS = 0x01`, Blowfish-encrypted 20-byte BaseApp address) are fully documented and ready for implementation.
5. **Technical Viability is Formally Demonstrated:**  
   Approach B (Level 2) is **statically and mathematically demonstrated** to be the least invasive, technically viable deployment path.

---

## 2. Summary of Findings by Task

### Task 1: Resource Loading Control Flow
- Traced the complete invocation chain from the Python script binding `BigWorld.logOn` (VA `0x10089feb0`) through `0x10089fd30`, `0x100877664`, `ServerConnection::logOn` (VA `0x1008ab5c8`), to `ServerConnection::logOnBegin` (VA `0x1008abb94`).
- Confirmed that `ServerConnection::logOnBegin` evaluates register `x4` (stored in `x22`): if non-null and non-empty, it uses `x4`; if null or empty, it loads the default string `"entities\\loginapp.pubkey"` (VA `0x10309c3b8`).
- Confirmed that `ServerConnection::setKeyFromResource` (VA `0x1008ab400`) invokes `BWResource::openSection` to resolve the file through NeoX VFS.
- Confirmed that an external Windows launcher cannot supply or redirect this parameter at runtime on an iOS device.

### Task 2: NPK Archive & Application Resource Packaging
- Disassembled `package.npkpackage::LoadHeader` (VA `0x101b64e58`) and reverse-engineered the NetEase `NXPK` binary format:
  - 24-byte header: `NXPK` magic, entry count, reserved bytes, version, table offset.
  - 28-byte entry index table: `[path_hash, data_offset, compressed_size, uncompressed_size, crc1, crc2, flags]`.
  - Verified against `script.npk` (size 51,783,198 bytes, 3,983 entries, table offset 51,671,674, matching byte-for-byte).
- Verified that NeoX VFS prioritizes discrete filesystem files over packaged `.npk` archives.
- Confirmed that loose files in `%APP_DIR%/` do not require manifest entries, NPK index updates, or archive rebuilds.

### Task 3: iOS Code Signing & Sideloading Requirements
- Verified that `RoS-Legacy-iOS.ipa` currently lacks `_CodeSignature/CodeResources` and `embedded.mobileprovision` (it cannot run on stock iOS devices as-is).
- Established that adding `entities/loginapp.pubkey` requires generating a new `_CodeSignature/CodeResources` manifest.
- Confirmed that standard re-signing tools (`codesign`, `zsign`, `AltSign`) regenerate the signature block without modifying the binary's executable instructions or memory layout.
- Evaluated physical installation options: AltStore (7-day free refresh), Sideloadly, Paid Apple Developer Account ($99/year, 1-year ad-hoc install), and TrollStore (permanent install on iOS 14.0–16.6.1).

### Task 4: Private LoginApp Protocol Implementation Design
- Designed the conceptual architecture for the private `LoginApp`:
  1. Receive UDP datagrams on port `20013`.
  2. Parse native Mercury framing (`HAS_REQUESTS`, `HAS_SEQUENCE_NUMBER`, 28-bit sequence number).
  3. Demux BigWorld RPC bundle header (Message ID `0x00`, 2-byte length, 4-byte Request ID).
  4. Verify `LOGIN_VERSION = 43` (`0x0000002b`).
  5. Decrypt RSA-OAEP SHA-1 ciphertext using `private_server.key`.
  6. Deserialize `LogOnParams`: username, password (desalting `aec05336` prefix), 56-byte Blowfish key, 16-byte nonce, 4-byte client flags.
  7. Validate credentials against FastAPI backend (`ros-private-server`).
  8. Encrypt 20-byte BaseApp address with the client's 56-byte Blowfish key.
  9. Transmit `LoginReply` with status `0x01` (`LOGON_STATUS_SUCCESS`).

### Task 5: BaseApp Transition Requirements
- Disassembled `BaseAppExtInterface` (Message IDs `0x00`–`0x11`), establishing the wire specifications for `baseAppLogin` (`0x00`), `authenticate` (`0x01`), and movement updates.
- Identified the transition from unencrypted transport to **full-datagram Blowfish PBC encryption** on the BaseApp channel.
- Identified the minimal sequence of `ClientInterface` callbacks required to bring the client into an active lobby:
  - `resetEntities`
  - `setGameTime`
  - `createBasePlayer` (spawns player avatar, sets diamonds, gold, skins, and stats)
  - `spaceData` (loads lobby scene parameters)

### Task 6: Architecture Decision Matrix
- Compared Approaches A, B (Level 2), and C (Level 3).
- Approach A is technically blocked on physical stock devices (missing key, unsigned IPA, sandbox isolation).
- Approach C (binary patching) violates the project charter and is unnecessary.
- **Approach B (Level 2) is formally recommended** as the least invasive technically viable solution.
- The resource packaging method is **statically and mathematically demonstrated**.

---

## 3. Index of Deliverables

All detailed research documents are located in `D:\ROS-Legacy-Analysis\phase6B_11_loginapp_feasibility\`:

1. [resource_lookup_control_flow.md](file:///D:/ROS-Legacy-Analysis/phase6B_11_loginapp_feasibility/resource_lookup_control_flow.md) — Complete native disassembly trace of `BigWorld.logOn` to `ServerConnection::logOnBegin`.
2. [npk_resource_mount_analysis.md](file:///D:/ROS-Legacy-Analysis/phase6B_11_loginapp_feasibility/npk_resource_mount_analysis.md) — NeoX `NXPK` binary format specification, header layout, and VFS discrete precedence analysis.
3. [ios_resource_signing_analysis.md](file:///D:/ROS-Legacy-Analysis/phase6B_11_loginapp_feasibility/ios_resource_signing_analysis.md) — Apple AMFI, CodeResources sealing, provisioning profiles, and sideloading channels.
4. [private_loginapp_design.md](file:///D:/ROS-Legacy-Analysis/phase6B_11_loginapp_feasibility/private_loginapp_design.md) — Complete end-to-end specification for the private LoginApp gateway.
5. [baseapp_transition_requirements.md](file:///D:/ROS-Legacy-Analysis/phase6B_11_loginapp_feasibility/baseapp_transition_requirements.md) — `BaseAppExtInterface` mapping and `createBasePlayer` lobby transition roadmap.
6. [architecture_decision.md](file:///D:/ROS-Legacy-Analysis/phase6B_11_loginapp_feasibility/architecture_decision.md) — Comparison matrix and demonstration status of Approach B.
7. [ros_phase6B_11_final_report.md](file:///D:/ROS-Legacy-Analysis/phase6B_11_loginapp_feasibility/ros_phase6B_11_final_report.md) — This master synthesis document.

---

## 4. Final Integrity Verification

The read-only integrity of all protected assets was recalculated and verified:

```
Algorithm       Hash                                                             Path
---------       ----                                                             ----
SHA256          51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6 D:\ROS-Legacy-Analysis\extracted\Payload\client.app\client
SHA256          D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55 D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa
```

### Confirmation Checklist:
- [x] Original Mach-O executable `client` is **100% byte-for-byte unchanged**.
- [x] Original IPA `RoS-Legacy-iOS.ipa` is **100% byte-for-byte unchanged**.
- [x] Backend source code (`ros-private-server/`) is **100% unchanged**.
- [x] Synthetic Mercury gateway (`phase6B_8_local_gateway/`) is **100% unchanged**.
- [x] Databases are **completely untouched**.
- [x] Zero network sockets opened; zero external packets sent.
- [x] No physical iOS device connected; no replacement IPA created.

---

## 5. Stop Condition

Phase 6.2B.11 is strictly complete. All research objectives and design requirements have been met.

No implementation has been undertaken. We await explicit user authorization before initiating Phase 6.2B.12.
