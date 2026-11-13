# iOS Installation, Code Signing, and Sandboxing Constraints
## Technical Audit of Apple Security Boundaries for ROS Legacy Deployment

---

### 1. Executive Summary

A critical reality of developing a private server for an original Apple iOS application is that **the client execution environment is governed by Apple Mobile File Integrity (AMFI) and mandatory kernel-level sandboxing**.

Unlike Windows or Android, where arbitrary executable files can be launched by a custom launcher, iOS enforces cryptographic validation on every binary and bundle resource before allowing code execution.

This document details the practical constraints of iOS code signing, provisioning profiles, entitlements, resource seal verification, and app sandboxing as they apply to `RoS-Legacy-iOS.ipa`.

---

### 2. Apple Code Signing & Bundle Integrity Architecture

```
+--------------------------------------------------------------------------------+
|                             APP BUNDLE (client.app)                            |
|                                                                                |
|  +--------------------------------+     +-----------------------------------+  |
|  |       Mach-O Executable        |     |          Bundle Resources         |  |
|  |           (`client`)           |     | (`Info.plist`, `.npk`, PNGs, etc.)|  |
|  |                                |     +-----------------------------------+  |
|  | +----------------------------+ |                       |                    |
|  | |      CodeDirectory         | |                       v                    |
|  | | (Hashes of 4KB code pages) | |     +-----------------------------------+  |
|  | +----------------------------+ |     |   _CodeSignature/CodeResources    |  |
|  | |      Entitlements XML      | |     |   (SHA-256 seal of EVERY file)    |  |
|  | +----------------------------+ |     +-----------------------------------+  |
|  | |      CMS Signature Blob    | |                       |                    |
|  | | (Apple Root CA Trust Chain)| |                       |                    |
|  | +----------------------------+ |                       |                    |
|  +--------------------------------+                       |                    |
|                  |                                        |                    |
|                  +--------------------+-------------------+                    |
|                                       v                                        |
|                     +-----------------------------------+                      |
|                     |     embedded.mobileprovision      |                      |
|                     | (Signed by Apple Developer Portal)|                      |
|                     +-----------------------------------+                      |
+--------------------------------------------------------------------------------+
```

#### 2.1 The Two-Tiered Signature System
On iOS, code signing is not merely a single digital signature on the binary executable. It consists of two interdependent cryptographic seals:

1. **Mach-O Binary Seal (`LC_CODE_SIGNATURE`):**
   - Embedded directly inside the Mach-O binary (located at file offset `0x3a9a130` in `client`, spanning `1,566,777` bytes).
   - Contains a `CodeDirectory` holding cryptographic hashes for every 4096-byte memory page in the `__TEXT` segment.
   - Contains an embedded Entitlements blob (verified in `client` at offset `0x3a9a130 + 0x929e1`).
   - Contains a cryptographic CMS (PKCS #7) signature block.

2. **Resource Seal (`_CodeSignature/CodeResources`):**
   - An XML/plist file residing in the app bundle.
   - Contains SHA-1 and SHA-256 hashes of **every non-executable file in the bundle** (all `.npk` archives, `.plist` files, textures, models, sound files, and icons).
   - The hash of `CodeResources` is itself sealed inside Slot 0 (`CSSLOT_CODEDIRECTORY`) of the Mach-O binary's `LC_CODE_SIGNATURE`.

#### 2.2 The Inescapable Consequence of Resource Modification
> **If ANY file inside the application bundle is added, removed, or modified (for example, adding `entities/loginapp.pubkey` or altering `neox.xml`), the cryptographic hash of that file changes.**

When a file hash changes:
1. `_CodeSignature/CodeResources` is invalidated.
2. If `CodeResources` is updated, its hash no longer matches the sealed hash in the Mach-O binary's `CodeDirectory`.
3. If the Mach-O `CodeDirectory` is modified, the CMS signature block becomes mathematically invalid.
4. When launched on a non-jailbroken iOS device, the iOS kernel (`amfi`) detects the broken trust chain, logs a code signature violation, and **immediately kills the process with `SIGKILL` (Crash Reporter: `EXC_CRASH (SIGKILL: CODESIGNING)`)**.

**Conclusion:** Modifying application resources to inject the private server public key **cannot be done without completely re-signing the entire application bundle**.

---

### 3. Provisioning Profiles and Device Distribution

Even if the IPA is not modified, an iOS application cannot be installed on a physical iOS device without a matching **Provisioning Profile (`embedded.mobileprovision`)**.

#### 3.1 Status of the Provided `RoS-Legacy-iOS.ipa`
Inspection of `RoS-Legacy-iOS.ipa` in Phase 6.2B.10 revealed:
- `embedded.mobileprovision`: **MISSING** (0 matches in archive).
- `_CodeSignature/CodeResources`: **MISSING** (0 matches in archive).
- `CFBundleIdentifier` in `Info.plist`: `net.roslegacy.ios`.
- `application-identifier` in binary entitlements: `QKNZB3E3BF.com.netease.chiji`.

**Confirmed Fact:**
The provided `RoS-Legacy-iOS.ipa` is an **unsigned / stripped IPA**. It has no active provisioning profile. **It cannot be installed on ANY non-jailbroken physical iOS device as-is.** Any attempt to install it via Apple Configurator, iTunes, or Xcode will fail immediately with:
`ApplicationVerificationFailed: Failed to verify code signature (0xe8008015)`.

#### 3.2 Real-World Sideloading Options for Friends

To allow friends to install and play the game on their iOS devices, one of the following signing methods is required:

| Method | Cost | Validity Period | Device Limits | Technical Process | Feasibility for Friends |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Free Apple ID (AltStore / Sideloadly)** | \$0 | **7 days** (Must refresh weekly) | **Max 3 apps** per device | Friends connect iPhone to PC or use AltServer on Wi-Fi; launcher signs IPA with user's personal Apple ID. | **High**, but requires refreshing every 7 days. |
| **Apple Developer Program ($99/yr)** | \$99 / yr | **1 year** | **100 devices** (UDID registration) | Server owner registers friends' device UDIDs on Apple Developer Portal, generates Ad-Hoc profile, and signs IPA once per year. | **High**; seamless experience for up to 100 friends. |
| **TrollStore (CoreTrust Exploit)** | \$0 | **Permanent** (No expiration) | Unlimited | Exploits CVE-2022-26766 / CVE-2023-41991. Permanently installs unsigned/fake-signed IPAs. | **High**, but **STRICTLY LIMITED** to devices on iOS 15.0–16.6.1 (patched on iOS 16.7+). |
| **Jailbreak (AppSync Unified)** | \$0 | **Permanent** | Unlimited | Bypasses AMFI signature checks in kernel. | Restricted to friends with jailbroken devices. |

---

### 4. iOS Sandboxing Constraints

Once an application is successfully signed and installed, the iOS kernel confines its execution to an isolated sandbox container.

#### 4.1 Sandbox Structure
On iOS 16+, each app is assigned two isolated filesystem containers with randomized GUIDs:
- **Bundle Container:**
  `/var/containers/Bundle/Application/<RANDOM-UUID>/client.app/`
  *Permissions: Read-only, execute.* Any runtime write attempt triggers an immediate kernel access violation.
- **Data Container:**
  `/var/mobile/Containers/Data/Application/<RANDOM-UUID>/`
  *Subdirectories: `Documents/`, `Library/`, `tmp/`.*
  *Permissions: Read-write, restricted strictly to the app's own UID.*

#### 4.2 Cross-App and External Isolation
1. **No External Process Inspection:** A Windows PC connected via USB cannot read or write to an app's Data Container unless:
   - The app has `UIFileSharingEnabled = True` in `Info.plist` (which is `False` in `client`).
   - OR the app was signed with a Developer Profile containing `get-task-allow = true` and accessed via Xcode debugger tools.
2. **No Launcher File Injection:** An external launcher running on Windows cannot inject `entities\loginapp.pubkey` into `/var/mobile/Containers/Data/Application/<UUID>/Documents/res/` while the game is running on a stock iOS device.
3. **No Environment Variable / Parameter Passing:** iOS apps launched from the home screen cannot receive custom command-line arguments or environment variables from external launchers.

---

### 5. Architectural Summary of the Signing Boundary

1. **Unsigned IPA Execution is Impossible on Stock iOS:** The original IPA lacks `embedded.mobileprovision` and must be signed before installation.
2. **Signing Requires Packaging:** Code signing binds the Mach-O binary, `Info.plist`, and all resources into a single cryptographic seal.
3. **Resource Modification Requires Re-Signing:** Adding a private server public key into the bundle alters the resource seal, requiring a fresh code signature.
4. **Preserving the Executable vs. Preserving the IPA:**
   - **Preserving `client` Mach-O (Executable):** 100% possible. The binary's ARM64 code, assembly, and hashes can remain completely untouched.
   - **Preserving `RoS-Legacy-iOS.ipa` (Archive):** Impossible if the app is to run on real player iOS devices, because physical devices require a valid provisioning profile and matching code signature.
