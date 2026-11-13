# ROS SOTHAT — PHASE L0 FINAL REPORT
## Ad Hoc iOS Distribution Feasibility Research

**Phase:** Phase L0 (Ad Hoc Distribution Feasibility Research)  
**Project Root:** `D:\ROS-Legacy-Analysis\`  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_adhoc_feasibility\`  
**Date of Audit & Report:** 2026-11-13  
**Status:** COMPLETE — RESEARCH FEASIBILITY APPROVED  

---

## 1. Executive Summary

Phase L0 investigated the technical, architectural, cryptographic, and operational feasibility of distributing the **ROS Sothat iOS Launcher** and the original **Rules of Survival Legacy** game to 10–20 invited friends using Apple's official **Ad Hoc Distribution** framework.

### Primary Feasibility Verdict:
**THE INTENDED PLAYER EXPERIENCE IS TECHNICALLY ACHIEVABLE** through a hybrid architecture combining an iOS companion launcher with official Apple Over-The-Air (OTA) system installation handoffs.

Crucially, reverse engineering of `RoS-Legacy-iOS.ipa` established that the original game **already contains the registered URL scheme `rosmobile://` in its compiled `Info.plist`**. This enables the companion launcher to detect whether the game is installed and boot the game on physical iOS hardware **without patching or modifying the original game binary**.

---

## 2. Technical Feasibility of the 9-Step Player Experience

```
+---------------------------------------------------------------------------------------------------------------+
|                                    FEASIBILITY BREAKDOWN OF PLAYER JOURNEY                                    |
+------+-----------------------------+-----------------------+--------------------------------------------------+
| Step | Intended Player Step        | Implementation Domain | Technical Mechanism & Feasibility Status         |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  1   | Player visits private       | Web (Safari)          | **ACHIEVABLE:** Standard responsive website on    |
|      | ROS Sothat website.         |                       | private domain (e.g. https://ros-sothat.net).    |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  2   | Player downloads and        | iOS System Handoff    | **ACHIEVABLE:** Safari triggers official Apple    |
|      | installs the launcher.      | (itms-services://)    | OTA manifest; installs launcher on home screen.  |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  3   | Player opens the launcher.  | Native Launcher UI    | **ACHIEVABLE:** Native Swift/SwiftUI companion   |
|      |                             | (SpringBoard Boot)    | app boots from home screen.                      |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  4   | Player registers or logs in | Native Launcher UI    | **ACHIEVABLE:** REST API calls to Windows        |
|      | using email verification.   | & Windows Backend     | backend (`ros-private-server`); OTP verified.    |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  5   | Player sees RoS Legacy      | Native Launcher UI    | **ACHIEVABLE:** Dynamic SwiftUI card showing     |
|      | in the game library.        |                       | game art, status, and installation state.        |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  6   | Player taps Download.       | Native Launcher UI    | **ACHIEVABLE (ADAPTED):** Tapping button requests|
|      |                             |                       | signed OTA installation manifest from server.    |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  7   | Launcher verifies integrity | Native Launcher UI    | **ACHIEVABLE (ADAPTED):** Server validates device|
|      | of the game package.        | & Windows Backend     | enrollment & package hash prior to handoff.      |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  8   | Player follows Apple-       | iOS System Handoff    | **ACHIEVABLE:** Launcher invokes itms-services   |
|      | supported install handoff.  | (itms-services://)    | URL; system modal confirms & installs game.      |
+------+-----------------------------+-----------------------+--------------------------------------------------+
|  9   | Player opens installed game | Native Launcher UI    | **ACHIEVABLE:** Launcher detects rosmobile://,   |
|      | and connects to ROS Sothat. | & Game Executable     | boots game, connects to private Mercury gateway. |
+------+-----------------------------+-----------------------+--------------------------------------------------+
```

---

## 3. Clear Division: Launcher In-App vs iOS System Handoff

Apple Mobile File Integrity (AMFI) and mandatory kernel sandboxing create a strict boundary regarding what an iOS app can do:

### What CAN be implemented inside the Launcher:
1. User registration, login, and email OTP verification.
2. Device UDID registration verification with the server backend.
3. Viewing game metadata, status, patch notes, and news.
4. Detecting whether Rules of Survival Legacy is currently installed (`canOpenURL("rosmobile://")`).
5. Launching the game into the foreground (`open("rosmobile://")`).
6. Account diamond balance display and character profile synchronization.
7. Triggering the iOS system installation dialog (`open("itms-services://?action=download-manifest&url=...")`).

### What CANNOT be done in-app (Requires System Handoff):
1. **Direct Package Extraction:** An iOS app cannot write files into `/var/mobile/Containers/Bundle/Application/`.
2. **Localhost HTTP Proxy Installation:** The system installer daemon (`appstored`) runs outside the app sandbox, strictly requires external HTTPS with trusted root CAs, and will fail if passed a local `127.0.0.1` non-TLS link.
3. **Silent Installation:** Apple requires user confirmation for all app installations; the system modal prompt (*"'ros-sothat.net' would like to install 'RoS Legacy'"*) is mandatory.

---

## 4. Necessity of a Separately Signed Distribution Copy

> **Is a separately signed game copy unavoidable?**

**YES, ABSOLUTELY UNAVOIDABLE.**

1. **Current Master State:** As proven in Phase 6.2B.10 and re-verified in Phase L0, the original archive `RoS-Legacy-iOS.ipa` currently lacks `embedded.mobileprovision` and `_CodeSignature/CodeResources`. It is an unsigned / stripped IPA.
2. **Apple Kernel Enforcement:** Stock physical iOS devices strictly refuse to install or execute unsigned binaries (`ApplicationVerificationFailed: 0xe8008015`).
3. **The Solution:** The original `RoS-Legacy-iOS.ipa` is preserved as an **immutable archival master** (read-only, never modified, SHA-256 locked). A build script creates a working copy, embeds the private server public key, attaches the Ad Hoc provisioning profile containing friends' UDIDs, signs the bundle with the developer certificate, and generates `RoS-Legacy-AdHoc-Distribution.ipa`.

---

## 5. Apple Developer Account & Infrastructure Requirements

### 5.1 Account & Certificate Structure
- **Account Type:** Apple Developer Program (Individual) — **$99.00 USD / year**.
- **Certificate:** Apple Distribution Certificate (valid 1 year).
- **App IDs:**
  - Launcher: `net.rossothat.launcher`
  - Game: `net.roslegacy.ios` (matching original bundle identifier)
- **Provisioning Profiles:** Two Ad Hoc profiles embedding the 10–20 friend UDIDs.

### 5.2 Device Limit Rules
- **Limit:** Exactly 100 iPhones per membership year.
- **Consumption:** 10–20 friends consume 10–20% of the account quota.
- **Annual Reset:** Device slots reset upon paying the annual $99 renewal fee.

### 5.3 Complete Cost Breakdown (Clearly Labeled)

```
+-----------------------------------------------------------------------------------------------+
|                                     INFRASTRUCTURE COST SHEET                                 |
+---------------------------+---------------+-------------------+-------------------------------+
| Item                      | Classification| Annual Cost (USD) | Notes                         |
+---------------------------+---------------+-------------------+-------------------------------+
| Apple Developer Account   | MANDATORY     | $99.00            | Official Apple recurring fee  |
| Custom Domain Name        | MANDATORY     | ~$12.00           | Required for trusted HTTPS    |
| TLS / SSL Certificate     | MANDATORY     | $0.00             | Free via Let's Encrypt / CF   |
| Web & Backend Hosting     | OPTIONAL      | $0.00             | Free on Windows PC (CF Tunnel)|
| Email OTP Dispatch        | OPTIONAL      | $0.00             | Free tier Resend (100/day)    |
| macOS Build Environment   | OPTIONAL      | $0.00             | Free via GitHub Actions macOS |
+---------------------------+---------------+-------------------+-------------------------------+
| **TOTAL INITIAL OUTLAY**  | **ESTIMATED** | **~$111.00 USD**  | **FULL FIRST YEAR COST**      |
+---------------------------+---------------+-------------------+-------------------------------+
```

---

## 6. Comprehensive GO / NO-GO Architectural Decision Matrix

```
+-----------------------------------------------------------------------------------------------+
|                                  GO / NO-GO DECISION MATRIX                                   |
+-----------------------------------+---------+-------------------------------------------------+
| Component / Architectural Path    | Verdict | Core Technical Justification                    |
+-----------------------------------+---------+-------------------------------------------------+
| 1. Apple Ad Hoc Distribution      | **GO**  | Officially supported by Apple for up to 100     |
|    via Private HTTPS Website      |         | registered devices; zero App Review required.   |
+-----------------------------------+---------+-------------------------------------------------+
| 2. Companion Launcher App         | **GO**  | Native Swift companion manages auth, email OTP, |
|    (Swift / SwiftUI on iOS)       |         | game status, and trigger handoffs seamlessly.   |
+-----------------------------------+---------+-------------------------------------------------+
| 3. OTA Installation Handoff       | **GO**  | Supported via itms-services:// protocol scheme. |
|    (itms-services://)             |         | Works from Safari and from inside launcher.     |
+-----------------------------------+---------+-------------------------------------------------+
| 4. Game Detection via URL Scheme  | **GO**  | rosmobile:// is already registered in original  |
|    (canOpenURL("rosmobile://"))   |         | Info.plist; zero game modification needed.     |
+-----------------------------------+---------+-------------------------------------------------+
| 5. Game Launch via URL Scheme     | **GO**  | open("rosmobile://") boots the installed game   |
|    (open("rosmobile://"))         |         | into the foreground natively.                   |
+-----------------------------------+---------+-------------------------------------------------+
| 6. Direct In-App File Extraction  | **NO-GO**| Technically impossible on iOS; apps cannot write|
|    (Installing IPA without system)|         | to OS app container or call MobileInstallation. |
+-----------------------------------+---------+-------------------------------------------------+
| 7. Unsigned Master Direct Install | **NO-GO**| Physical iPhones reject unsigned IPAs. Separate |
|    (Installing raw original IPA)  |         | signed distribution package is mandatory.       |
+-----------------------------------+---------+-------------------------------------------------+
| 8. Automated UDID Web Enrollment  | **GO**  | .mobileconfig profile allows 2-tap UDID capture |
|    (.mobileconfig OTA Profile)    |         | without requiring USB cables or iTunes.         |
+-----------------------------------+---------+-------------------------------------------------+
```

---

## 7. Risks and Unresolved Questions

1. **Annual Re-Signing Friction:** Ad Hoc provisioning profiles have a hard expiration limit of 365 days. Every 12 months, the developer must re-sign the distribution IPAs and have friends update via the website.
2. **Device Replacement Friction:** If a friend upgrades their iPhone, their new device UDID must be enrolled, profiles regenerated, and IPAs re-signed before they can install.
3. **Public Key Injection Boundary (Addressed in Phase 10):** The original game executable expects `entities\loginapp.pubkey`. To connect to the private server without modifying the Mach-O binary, the private server's public key must be placed into the distribution package's resource folder before signing.
4. **Mercury Fragmented Packets:** If game state updates exceed MTU size (1500 bytes), multi-packet fragmentation handling will need to be finalized in Phase 14 / 15.

---

## 8. Recommended Phase L1 Implementation Roadmap

If approved, the recommended steps for **Phase L1 (Distribution Infrastructure & Companion Prototype)** are:

1. **Phase L1.1 — Domain & Secure HTTPS Gateway Setup:**
   - Configure private domain (e.g. `ros-sothat.net`).
   - Establish trusted TLS certificates and Cloudflare Tunnel to Windows host.
   - Deploy `manifest.plist` hosting endpoint with correct MIME types.
2. **Phase L1.2 — Automated UDID Enrollment Service:**
   - Deploy `.mobileconfig` OTA device registration profile on the web server.
   - Implement backend endpoint to capture and store friend UDIDs automatically.
3. **Phase L1.3 — Clean-Room Distribution Packaging Pipeline:**
   - Implement build script that locks `RoS-Legacy-iOS.ipa` as an immutable master.
   - Extracts bundle to staging, inserts `entities/loginapp.pubkey`, packages Ad Hoc signed distribution IPA.
4. **Phase L1.4 — Swift Companion Launcher Prototype:**
   - Implement SwiftUI launcher with Email OTP auth, `canOpenURL("rosmobile://")` detection, and `itms-services://` installation trigger.

---

## 9. Protected Binary Integrity Re-Verification (SHA-256)

At the conclusion of Phase L0, cryptographic checksums of original assets were recomputed:

```
Target File: D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa
Expected SHA-256: D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55
Actual SHA-256:   D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55
Integrity Status: 100% BYTE-FOR-BYTE IDENTICAL — ZERO MODIFICATIONS

Target File: D:\ROS-Legacy-Analysis\extracted\Payload\client.app\client
Expected SHA-256: 51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6
Actual SHA-256:   51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6
Integrity Status: 100% BYTE-FOR-BYTE IDENTICAL — ZERO MODIFICATIONS
```

### Confirmation of Zero Side-Effects:
- Zero backend source files, databases, or gateways were modified.
- No network sockets or listeners were opened.
- No player UDIDs were collected.
- No funds were expended.
- Phase 13, 13.1, 13.2, 13.3, and 13.4 artifacts remain untouched.

---

## 10. Strict Stop Condition Sign-Off

**Phase L0 Feasibility Research is COMPLETE.**  
No code signing, installation, or game modification was implemented.  
Awaiting explicit user authorization before proceeding to Phase L1.
