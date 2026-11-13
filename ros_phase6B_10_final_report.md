# ROS Sothat — Phase 6.2B.10 Final Report
# Launcher Architecture and Public-Key Resource Feasibility Audit

**Author:** Antigravity (Google DeepMind Team)  
**Project:** ROS Sothat — Original Rules of Survival Legacy iOS Private Server  
**Mode:** Strict Read-Only Technical Feasibility Investigation  
**Date:** November 13, 2026  
**Status:** COMPLETED — STRICT READ-ONLY AUDIT

---

## 1. Executive Summary

Phase 6.2B.10 conducted an exhaustive, read-only technical feasibility audit of the proposed ROS Sothat launcher architecture and the mechanisms governing how the original Rules of Survival Legacy client ingests its login public key (`entities\loginapp.pubkey`).

The primary objective was to determine **whether the proposed private server deployment model is technically possible without modifying the original IPA or executable**, and to establish an honest, evidence-based engineering assessment separating confirmed facts from technical assumptions.

### Key Audit Conclusions:
1. **The Game Client is iOS-Only:** The original executable `client` is an **ARM64 Apple iOS Mach-O binary** compiled for `iphoneos` (iOS 16.0+). It **cannot be executed natively on Windows PCs**, nor can it run inside an Intel or standard Apple iOS simulator without re-compilation. Players must play on physical iPhones, iPads, or Apple Silicon Macs.
2. **The Original IPA is Unsigned:** `RoS-Legacy-iOS.ipa` lacks `embedded.mobileprovision` and `_CodeSignature/CodeResources`. It **cannot be installed on any physical iOS device without signing**.
3. **The Public Key is Missing from the IPA:** `entities\loginapp.pubkey` does not exist inside any `.npk` archive or directory in the provided IPA. An untouched client will immediately fail at launch with `PUBLIC_KEY_LOOKUP_FAILED` unless the key is supplied.
4. **Windows Cannot Control iOS Sandboxes:** A Windows desktop launcher running on a PC cannot intercept file lookups or inject cryptographic keys into an app running inside an iOS sandbox on a connected device.
5. **The Realistic Path Forward:** The original ARM64 binary executable `client` **can remain 100% bit-for-bit untouched**. However, enabling friends to install and play on standard iOS devices requires **packaging the private server's public key as a bundle resource and signing the resulting IPA container**.

---

## 2. Confirmed Facts vs. Unverified Assumptions

| Subject | Project Concept / Assumption | Verified Ground Truth (Evidence-Based) | Impact on Project |
| :--- | :--- | :--- | :--- |
| **Client Platform** | "Launcher runs original game on Windows" | **False.** `client` is an ARM64 iOS Mach-O binary (`MH_MAGIC_64`, `CPU_TYPE_ARM64`). Windows cannot execute iOS binaries. | Game must run on an iOS device. Windows tool can only be a companion/sideloading tool. |
| **Simulator Compatibility** | "Game can be tested in standard iOS Simulator" | **False.** Binary contains no `x86_64` or `arm64-simulator` slices; compiled strictly for physical `iphoneos` devices. | Requires physical iOS device or Apple Silicon Mac. |
| **IPA Installability** | "Original IPA can be installed as-is on iPhone" | **False.** IPA contains no `embedded.mobileprovision` or `CodeResources`. iOS kernel (`amfi`) will reject installation. | IPA must be signed with a provisioning profile. |
| **Public Key Availability** | "`entities\loginapp.pubkey` exists in the IPA" | **False.** An exhaustive scan of all 1,208 entries in `RoS-Legacy-iOS.ipa` confirmed the file is absent. | Client will abort at launch with `PUBLIC_KEY_LOOKUP_FAILED` unless provided. |
| **Windows Sandbox Control** | "Windows launcher can redirect iOS file lookups" | **False.** iOS sandboxing strictly isolates app containers. Windows PC has zero runtime visibility into iOS sandbox memory or filesystem. | Redirection from Windows PC is impossible on stock iOS. |
| **Engine Code Preservation** | "Original game executable `client` can be kept 100% untouched" | **TRUE.** The compiled Mach-O binary `client` does not need to be patched or modified. All engine routines, physics, and rendering remain original. | Preserves the project charter of using the genuine original game. |
| **VFS Discrete Search** | "NeoX VFS checks discrete filesystem before NPK" | **TRUE.** Disassembly of `BWResource::openSection` proves it checks `%APP_DIR%/entities/loginapp.pubkey` before searching NPK archives. | Adding key as a resource cleanly satisfies lookup. |

---

## 3. Detailed Technical Blockers Identified

### Blocker 1: Platform Incompatibility (Windows vs. iOS)
- **The Issue:** The end-user roadmap envisioned a Windows launcher opening the game directly on PC.
- **The Reality:** Rules of Survival originally released two completely distinct clients: a Windows PC client (`ros.exe`) and an iOS mobile client (`client`). The provided artifact (`RoS-Legacy-iOS.ipa`) is strictly the iOS mobile client.
- **Resolution:** Clarify project scope: Friends play on their iPhones/iPads; the Windows software functions as the server host and one-click USB sideloading manager.

### Blocker 2: iOS Code Signing and Provisioning Barrier
- **The Issue:** iOS devices enforce cryptographic signing via Apple Mobile File Integrity (AMFI).
- **The Reality:** Any unsigned IPA or any IPA whose resources have been altered without re-signing is blocked from launching by the iOS kernel (`EXC_CRASH (SIGKILL: CODESIGNING)`).
- **Resolution:** Re-sign the IPA container during installation using the player's free Apple ID (via AltStore/Sideloadly protocol) or an Apple Developer certificate.

### Blocker 3: The Missing RSA Public Key
- **The Issue:** NetEase originally distributed public keys via first-launch asset downloads or runtime script injection. The base IPA has no key file.
- **The Reality:** Without `entities\loginapp.pubkey`, `ServerConnection::logOnBegin` halts with `PUBLIC_KEY_LOOKUP_FAILED` at VA `0x1008ac0e0`.
- **Resolution:** Place the ROS Sothat private `LoginApp` public key into the bundle's `entities/` folder before signing.

---

## 4. Evaluation of Potential Architectures

| Architecture | Mach-O Binary Untouched? | Outer IPA Untouched? | Stock iOS Compatible? | Public Key Resolved? | Feasibility |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **A: Windows Sideloading Helper** | **YES** | No (Signed on install) | **YES** | Requires Key Package | **High (Recommended)** |
| **B: Launcher External Directory** | **YES** | YES | **NO (Sandbox Block)** | No | **IMPOSSIBLE** |
| **C: OS-Level Hook / Injection** | **YES** | **YES (with TrollStore)** | **NO (Jailbreak Only)** | **YES (in RAM)** | Feasible for Jailbreak |
| **D: Resource Package + Untouched Binary**| **YES** | No (Resource added) | **YES** | **YES (via VFS)** | **High (Recommended)** |
| **E: Binary Instruction Patching** | **NO (Violates Charter)**| No | YES | YES | **FORBIDDEN** |

---

## 5. Recommended Architecture

We recommend the **"Untouched Executable + Resource Package + Sideloading Companion"** architecture:

1. **Mach-O Binary Executable (`client`):** Kept **100% bit-for-bit identical** (SHA-256: `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6`).
2. **Resource Packaging:** The private server's RSA public key `entities/loginapp.pubkey` is placed into the app bundle. The NeoX VFS automatically resolves it from the discrete filesystem.
3. **Windows Companion Tool:** Handles web/account registration, diamond ledger management, and provides a 1-click **"Install to iPhone"** button (USB sideloading via open-source `usbmuxd` / `libimobiledevice`).
4. **Gameplay:** Friends tap the game on their iPhone/iPad and play together on the original game engine.

---

## 6. Next Decision Gate (Explicit User Choices Required)

Before Phase 6.2B.11 can begin, the project owner must choose between three distinct authorization levels:

### Level 1: Strict Total Archive Preservation (Jailbreak / TrollStore Only)
- **Constraint:** Both the Mach-O binary `client` AND the outer `RoS-Legacy-iOS.ipa` archive must remain 100% bit-for-bit untouched on disk.
- **Consequence:** The game **cannot run on standard iPhones**. It will only be playable by friends who own devices on iOS 15.0–16.6.1 with TrollStore installed, or jailbroken devices using a runtime tweak.
- **Action Required:** Develop TrollStore / jailbreak dylib tweak for public key injection.

### Level 2: Untouched Executable with Resource Packaging (Recommended)
- **Constraint:** The Mach-O binary executable `client` remains **100% bit-for-bit untouched**. However, the outer IPA archive is configured with the private server's public key and signed for player devices.
- **Consequence:** Compatible with **any standard iPhone or iPad running iOS 16+**. Friends can install via free Apple ID or Developer certificate.
- **Action Required:** Package `loginapp.pubkey` into the bundle and build the USB sideloading companion tool.

### Level 3: Binary Patching (Currently Forbidden)
- **Constraint:** Direct modification of ARM64 instructions in `client`.
- **Status:** **REJECTED** under existing project decisions.

---

## 7. Exact List of Files Inspected

During this phase, only read-only inspections were performed on:
- `D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa` (Archive table of contents, Info.plist, NPK headers).
- `D:\ROS-Legacy-Analysis\extracted\Payload\client.app\client` (Mach-O load commands, code signature SuperBlob, disassembly of VFS and login routines).
- `D:\ROS-Legacy-Analysis\extracted\Payload\client.app\neox.xml` (Engine configuration headers).
- `D:\ROS-Legacy-Analysis\phase6B_9_login_rpc_research\` (Previous phase research reports).

---

## 8. Final Asset Hash Verification

| Protected Asset | Reference Hash | Verified Hash | Verification Outcome |
| :--- | :--- | :--- | :---: |
| `extracted/Payload/client.app/client` | `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6` | `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6` | **VERIFIED UNCHANGED** |
| `RoS-Legacy-iOS.ipa` | `D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55` | `D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55` | **VERIFIED UNCHANGED** |
| `phase6B_8_local_gateway/` | Phase 6.2B.8.5 State | Phase 6.2B.8.5 State | **VERIFIED UNTOUCHED** |
| `ros-private-server/` | Phase 6.2B.8.5 State | Phase 6.2B.8.5 State | **VERIFIED UNTOUCHED** |
| Network / Sockets | Inactive | Inactive | **ZERO NETWORK TRAFFIC** |
| Databases | Disconnected | Disconnected | **ZERO DATABASE QUERIES** |

---

## 9. Deliverables Created in this Phase

The following research documents were created in `D:\ROS-Legacy-Analysis\phase6B_10_launcher_feasibility\`:
1. [ios_execution_environment.md](file:///D:/ROS-Legacy-Analysis/phase6B_10_launcher_feasibility/ios_execution_environment.md)
2. [public_key_resource_lookup_analysis.md](file:///D:/ROS-Legacy-Analysis/phase6B_10_launcher_feasibility/public_key_resource_lookup_analysis.md)
3. [launcher_architecture_comparison.md](file:///D:/ROS-Legacy-Analysis/phase6B_10_launcher_feasibility/launcher_architecture_comparison.md)
4. [ios_installation_signing_constraints.md](file:///D:/ROS-Legacy-Analysis/phase6B_10_launcher_feasibility/ios_installation_signing_constraints.md)
5. [recommended_launcher_architecture.md](file:///D:/ROS-Legacy-Analysis/phase6B_10_launcher_feasibility/recommended_launcher_architecture.md)
6. [ros_phase6B_10_final_report.md](file:///D:/ROS-Legacy-Analysis/phase6B_10_launcher_feasibility/ros_phase6B_10_final_report.md)

---

## 10. Stop Condition

Phase 6.2B.10 is strictly complete. In compliance with project instructions, all actions have stopped. Awaiting explicit user direction at the decision gate before taking any further steps.
