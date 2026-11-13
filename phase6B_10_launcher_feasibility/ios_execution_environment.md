# Target Execution Environment Audit
## Rules of Survival Legacy iOS Client (`RoS-Legacy-iOS.ipa`)

---

### 1. Executive Summary

This document establishes the verified hardware, architecture, operating system, and runtime execution requirements of the client binary provided in `D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa` (`Payload/client.app/client`).

A fundamental technical contradiction exists between the user's stated end-state goal (*"Friends visit our website -> download our launcher -> open launcher -> launcher opens original game on Windows"*) and the binary provided:
- The executable `client` is a **native Apple iOS ARM64 Mach-O binary**.
- It is compiled strictly for Apple mobile hardware (`iphoneos`, minimum iOS 16.0).
- It **cannot execute on Microsoft Windows**. No Windows-based emulator or compatibility layer can run modern 64-bit iOS Metal games on Windows.
- If the game is to run on real player hardware, that hardware must be an **Apple iOS device (iPhone or iPad)** or an **Apple Silicon Mac**.

---

### 2. Confirmed Technical Facts (Binary Analysis)

Static inspection of the Mach-O binary headers and application bundle attributes confirms the following:

#### 2.1 Mach-O Header Structure
- **File Type:** `MH_EXECUTE` (`0x00000002`, independent executable binary).
- **Target Architecture:** `CPU_TYPE_ARM64` (`0x0100000c`), `cpusubtype = 0x00000000`.
- **Address Space:** 64-bit Little-Endian (`MH_MAGIC_64 = 0xfeedfacf`).
- **Binary Slices:** Single-architecture binary.
  - Contains **NO x86_64 slice** (cannot run in standard Intel-based macOS iOS Simulator).
  - Contains **NO `arm64-simulator` slice** (compiled strictly for physical `iphoneos` devices).
- **Load Commands:** 69 load commands spanning `0x1f0` bytes.

#### 2.2 Operating System and Platform Dependencies
- **Platform:** `LC_VERSION_MIN_IPHONEOS` / `iphoneos` SDK:
  - `MinimumOSVersion`: **iOS 16.0** (`version = 9.0.0` in load command, overridden by `MinimumOSVersion: 16.0` in `Info.plist`).
  - `SDK Version`: **iOS 15.0.0** (`DTSDKName: iphoneos15.0`).
- **Device Family (`UIDeviceFamily`):** `[1, 2]`
  - `1`: iPhone / iPod Touch.
  - `2`: iPad.
- **Hardware Requirements (`UIRequiredDeviceCapabilities`):**
  - `gamekit`: Apple GameCenter / GameKit framework.
  - `arm64`: 64-bit ARM CPU.
  - `Metal`: Apple hardware-accelerated graphics API.

#### 2.3 Framework Dependencies (`LC_LOAD_DYLIB`)
The binary links dynamically against Apple-proprietary frameworks available exclusively on iOS:
- `/System/Library/Frameworks/UIKit.framework/UIKit`
- `/System/Library/Frameworks/Foundation.framework/Foundation`
- `/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics`
- `/System/Library/Frameworks/Metal.framework/Metal`
- `/System/Library/Frameworks/AVFoundation.framework/AVFoundation`
- `/System/Library/Frameworks/Security.framework/Security`
- `/System/Library/Frameworks/SystemConfiguration.framework/SystemConfiguration`
- `/usr/lib/libSystem.B.dylib` (Darwin XNU Kernel ABI)

---

### 3. Execution Environment Feasibility Matrix

| Execution Environment | Hardware Required | OS Required | Feasibility Status | Technical Justification |
| :--- | :--- | :--- | :---: | :--- |
| **Native Windows Execution** | Windows PC (x86_64 or ARM64) | Windows 10 / 11 | **IMPOSSIBLE** | Windows cannot execute Mach-O binaries or resolve Apple Darwin frameworks (`UIKit`, `Metal`). |
| **Windows iOS "Emulator"** | Windows PC | Windows 10 / 11 | **IMPOSSIBLE** | No functioning Windows emulator exists for 64-bit ARM64 iOS with Metal 3D graphics. Tools like Smartface or iPadian are skins, not iOS kernel emulators. |
| **Intel macOS Simulator** | Intel Mac | macOS 12+ | **IMPOSSIBLE** | Binary lacks an x86_64 architecture slice. |
| **Apple Silicon Mac (Simulator)** | Apple Silicon Mac (M1–M4) | macOS 13+ | **IMPOSSIBLE without recompile** | The binary is compiled for the `iphoneos` environment, not the `iphonesimulator` environment (different Mach-O ABI and dylib search paths). |
| **Apple Silicon Mac ("Designed for iPad")** | Apple Silicon Mac (M1–M4) | macOS 13+ | **FEASIBLE with valid signature** | macOS on Apple Silicon can run native iOS binaries directly, but strictly requires valid Apple code signing matching the Mac user's account. |
| **Physical iOS Device (iPhone / iPad)** | iPhone 8 or newer (A11+ Bionic) | iOS 16.0 to 17.x / 18.x | **NATIVE TARGET** | The original hardware environment for which `client` was compiled. |

---

### 4. Role of a Windows Launcher in an iOS Project

Given that the original game client **must** run on an iOS device, what can a Windows-based application actually do?

#### Confirmed Fact:
A Windows program **cannot launch, execute, hook, or control an iOS app during runtime**.
When a player plays Rules of Survival Legacy, they are holding an iPhone or iPad, touching an iOS screen, and running an ARM64 app inside an iOS sandbox.

#### Realistic Windows PC Tool Roles:
A Windows application in this project can realistically act only as an **Out-of-Band Management Utility**:
1. **Account Registration / Web Portal:** Allowing players to register an account on the ROS Sothat private server, manage their character, inventory, diamonds, and view rankings.
2. **USB Sideloading Helper (AltServer / Sideloadly model):** Connecting to an iPhone via USB using Apple Mobile Device Support (`usbmuxd` / `libimobiledevice`), signing the IPA with the player's Apple ID, and installing it onto their connected iPhone.
3. **Network Gateway / Proxy Host:** Serving as the local host running the Python FastAPI backend and Mercury gateway on the local network.

---

### 5. Summary of Assumptions vs. Confirmed Facts

| Category | Claim / Concept | Verification Status | Reality |
| :--- | :--- | :---: | :--- |
| **Platform** | Game can run on Windows via launcher | **DISPROVEN** | Binary is an ARM64 iOS Mach-O executable. |
| **Platform** | Windows launcher can open the iOS game | **DISPROVEN** | Windows has no process control over iOS devices. |
| **Platform** | Game can run in standard iOS Simulator | **DISPROVEN** | Binary lacks simulator slices (`x86_64` / `arm64-simulator`). |
| **Platform** | Game can run on physical iOS device | **CONFIRMED** | Compiled for `iphoneos`, iOS 16.0+, ARM64. |
| **Platform** | Windows tool can sideload IPA to iOS | **CONFIRMED** | Feasible via `usbmuxd` / `libimobiledevice` protocols over USB. |
