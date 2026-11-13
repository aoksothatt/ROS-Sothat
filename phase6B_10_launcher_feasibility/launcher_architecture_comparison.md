# Launcher Architecture Comparison & Feasibility Audit
## Evaluation of Private Server Deployment Models for ROS Legacy

---

### 1. Architectural Scope

This audit evaluates five potential deployment architectures for connecting the original Rules of Survival Legacy client to the ROS Sothat private server. Each approach is analyzed independently against:
- Technical feasibility on target platforms.
- Required operating system and hardware.
- Privilege and permission requirements.
- Impact on IPA file integrity and Apple code signing.
- Compatibility with the project constraint: *"The original IPA must remain completely unchanged."*

---

### 2. Independent Evaluation of Approaches

---

#### Approach A: Windows Launcher as IPA Sideloading & Account Manager (Game Runs on iOS)

##### Architectural Description
A Windows desktop program serves as a companion tool. Players connect their iPhone/iPad via USB to their Windows PC. The launcher:
1. Authenticates or registers player accounts on the private server web portal.
2. Sideloads the game IPA onto the player's connected iOS device using standard sideloading protocols (similar to Sideloadly or AltServer).
3. The game runs natively on the player's iOS device and connects over Wi-Fi / cellular to the private server.

##### Evaluation Parameters
- **Technical Feasibility:** **High (for installation)**; **Incomplete (for login without key solution)**.
  - Sideloading over USB via `usbmuxd` / `libimobiledevice` is an established, industry-standard mechanism.
  - However, the Windows launcher has zero runtime control over the iOS game once launched. It cannot inject the private server public key into the running iOS app.
- **Required Platform:**
  - Manager: Windows 10 / 11 PC (with Apple Mobile Device Support / iTunes drivers).
  - Game Client: Physical iPhone / iPad running iOS 16.0+.
- **Required Permissions:** Standard user on Windows; USB trust pairing ("Trust This Computer") on iOS.
- **Does IPA Change on Disk?** Yes during sideloading. iOS sideloading embeds a provisioning profile (`embedded.mobileprovision`) and updates the code signature.
- **Is Re-Signing Required?** **Yes.** Physical iOS devices will reject unsigned IPAs.
- **Project Charter Conflict:** Moderate conflict. Original binary `client` remains unchanged, but the `.ipa` container is signed.
- **Demonstrated vs. Theoretical:** **Demonstrated**. Used by millions of users via AltStore, Sideloadly, and TrollStore.

---

#### Approach B: Launcher-Controlled External Resource Directory

##### Architectural Description
The iOS game client is instructed to read game assets, configuration, and `entities\loginapp.pubkey` from an external directory on the local network or USB connection managed by the Windows launcher.

##### Evaluation Parameters
- **Technical Feasibility:** **IMPOSSIBLE on iOS**.
  - iOS apps execute within a strict kernel sandbox (`/var/mobile/Containers/Data/Application/<UUID>/`).
  - The iOS kernel (`sandbox.kext`) strictly prohibits an app from opening file paths outside its sandbox container.
  - Network-attached storage (SMB/NFS) or USB file access requires dedicated networking code in the client executable. Disassembly of NeoX VFS (`BWResource`) proves it only searches local mounts (`%APP_DIR%`, `%DOC_DIR%`, `%WORK_DIR%`).
  - `UIFileSharingEnabled` is set to `False` in `Info.plist`, preventing even iTunes USB file sharing.
- **Required Platform:** Stock iOS device.
- **Required Permissions:** Sandbox escape (requires kernel jailbreak).
- **Does IPA Change on Disk?** No.
- **Is Re-Signing Required?** Yes (for basic iOS installation).
- **Project Charter Conflict:** Severe (fundamentally non-viable on iOS).
- **Demonstrated vs. Theoretical:** **Disproven / Non-viable**.

---

#### Approach C: Operating-System-Level File / Resource Redirection

##### Architectural Description
The file lookup for `"entities\\loginapp.pubkey"` is redirected at the operating system or runtime dynamic linker layer:
1. Intercepting `open()`, `stat()`, or `BWResource::openSection()` using dynamic function hooking (`DYLD_INSERT_LIBRARIES` or MobileSubstrate / Frida).
2. Diverting the file read to a local file containing the private server's RSA public key.

##### Evaluation Parameters
- **Technical Feasibility:** **Feasible on Jailbroken iOS; Impossible on Stock iOS**.
  - On non-jailbroken iOS, `DYLD_INSERT_LIBRARIES` is blocked by AMFI for non-debuggable binaries.
  - On jailbroken iOS (or devices with TrollStore supporting the CoreTrust exploit on iOS 15.0–16.6.1), dynamic libraries (`.dylib`) can be injected to intercept VFS calls and return the private public key seamlessly in RAM.
- **Required Platform:** Jailbroken iPhone / iPad (or TrollStore-compatible iOS version).
- **Required Permissions:** Root / Kernel read-write.
- **Does IPA Change on Disk?** **No.** The original IPA remains 100% bit-for-bit identical on disk.
- **Is Re-Signing Required?** **No on TrollStore**; Yes on standard jailbreak (ad-hoc signing permitted).
- **Project Charter Conflict:** **None.** Perfectly satisfies the untouched IPA requirement, but restricts user device compatibility to jailbroken or TrollStore-eligible iOS devices.
- **Demonstrated vs. Theoretical:** **Demonstrated**. Standard technique in iOS game security research and private server development.

---

#### Approach D: Modified Application Resources (Original Executable Preserved)

##### Architectural Description
The original Mach-O executable `client` is kept **100% untouched** (SHA-256 hash perfectly preserved). However, the IPA container or its bundled resource packages are modified:
1. The private server's RSA public key is added as `Payload/client.app/entities/loginapp.pubkey` or packaged into `res/entities.npk`.
2. The server IP address or domain is updated in `neox.xml` or `script.npk`.
3. The modified package is re-signed with a valid developer or personal certificate and installed onto player iOS devices.

##### Evaluation Parameters
- **Technical Feasibility:** **High**.
  - NeoX VFS automatically resolves `entities/loginapp.pubkey` from the discrete filesystem in `%APP_DIR%`.
  - The client successfully encrypts `LogOnParams` with the private server's key, allowing clean decryption by `LoginApp`.
- **Required Platform:** Any standard physical iOS device (iOS 16.0+). No jailbreak required.
- **Required Permissions:** Standard user with personal Apple ID (free) or Developer Certificate.
- **Does IPA Change on Disk?** **Yes.** The `.ipa` archive contains an added resource file.
- **Is Re-Signing Required?** **Yes.** Adding any file alters `_CodeSignature/CodeResources` and requires a fresh code signature.
- **Project Charter Conflict:** Partial. The Mach-O binary executable `client` remains 100% identical and unmodified, but the outer `.ipa` zip archive is modified.
- **Demonstrated vs. Theoretical:** **Demonstrated**. Universal standard for iOS private servers and modding.

---

#### Approach E: Binary Executable Modification (Patching `client`)

##### Architectural Description
Modifying the ARM64 instructions inside `extracted/Payload/client.app/client`:
1. NOP-ing out the `PUBLIC_KEY_LOOKUP_FAILED` branch at VA `0x1008ac040` to force unencrypted login.
2. OR replacing the string `"entities\\loginapp.pubkey"` with an alternate embedded string.
3. OR replacing the embedded UniSdk public key bytes.

##### Evaluation Parameters
- **Technical Feasibility:** **High**.
- **Required Platform:** Any iOS device (requires re-signing).
- **Does IPA Change on Disk?** **Yes.**
- **Is Re-Signing Required?** **Yes.**
- **Project Charter Conflict:** **TOTAL VIOLATION**. Explicitly forbidden by project rules (*"Do not modify the extracted Mach-O executable"*).
- **Demonstrated vs. Theoretical:** Demonstrated, but prohibited.

---

### 3. Comprehensive Decision Matrix

| Evaluation Criteria | Approach A (Win Sideload) | Approach B (External Res) | Approach C (OS Redirection) | Approach D (Resource Mod) | Approach E (Binary Patch) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Technical Feasibility** | High (Install only) | **Impossible** | Feasible (Jailbreak) | **High** | High |
| **Stock iOS Compatible** | Yes (Sideloaded) | No | **No (Jailbreak only)** | **Yes** | Yes |
| **Original Mach-O Unchanged?** | **YES** | **YES** | **YES** | **YES** | **NO (Violates)** |
| **Original IPA Unchanged?** | No (Signed on install) | Yes | **YES (with TrollStore)** | No (Resource added) | No |
| **Re-Signing Required?** | Yes | Yes | No (TrollStore) / Ad-hoc | Yes | Yes |
| **Resolves Public Key Issue?** | No (Lacks injection) | No | **YES (in RAM)** | **YES (in VFS)** | YES |
| **User Experience (Friends)** | Complex | Non-viable | Restricted to Jailbreak | **Standard Sideload** | Standard Sideload |
| **Project Authorization Status** | Compatible | Incompatible | Charter Compatible | **Requires Decision** | **FORBIDDEN** |

---

### 4. Core Findings & Inescapable Trade-Off

1. **A Windows launcher cannot run an iOS game, nor can it bypass iOS sandboxing to inject files at runtime.**
2. **If the Mach-O binary executable `client` MUST remain 100% bit-for-bit unchanged**, there are only two viable pathways to deliver the private server public key:
   - **Path 1 (Jailbreak / TrollStore Injection — Approach C):** Keeps the IPA and binary 100% unchanged on disk. Requires players to have a jailbroken iOS device or TrollStore-compatible iOS version (iOS 15.0–16.6.1).
   - **Path 2 (Resource Addition + Re-Signing — Approach D):** Preserves the binary `client` 100% untouched, but packages the private server's `loginapp.pubkey` into the `.ipa` bundle and re-signs it for stock iOS devices.
3. On standard, non-jailbroken physical iOS devices, **no method exists in computer science to execute an untouched, unsigned iOS IPA while simultaneously redirecting its file lookups from an external Windows PC.**
