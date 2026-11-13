# ROS Sothat — Phase L0 Deliverable 5
## Original IPA Preservation & Archival Master Report

**Phase:** Phase L0 (Ad Hoc Distribution Feasibility Research)  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_adhoc_feasibility\`  
**Date:** 2026-11-13  
**Status:** COMPLETE — INTEGRITY & PRESERVATION REPORT  

---

### 1. Executive Summary

This report establishes the forensic status of the original game assets (`RoS-Legacy-iOS.ipa` and `client`), details why the original archive cannot be installed directly on physical iOS hardware in its current state, proves why a **separate signed distribution copy** is physically unavoidable, and defines a zero-risk protocol to ensure the original files remain completely immutable for all time.

---

### 2. Cryptographic Integrity Baseline Verification

At the initiation of Phase L0, cryptographic hashes of the protected original files were verified against project baselines using Windows PowerShell `Get-FileHash`:

```
Target File: D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa
Expected SHA-256: D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55
Actual SHA-256:   D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55
Verification Status: 100% BYTE-FOR-BYTE IDENTICAL — ZERO MODIFICATIONS

Target File: D:\ROS-Legacy-Analysis\extracted\Payload\client.app\client
Expected SHA-256: 51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6
Actual SHA-256:   51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6
Verification Status: 100% BYTE-FOR-BYTE IDENTICAL — ZERO MODIFICATIONS
```

---

### 3. Forensic Analysis: Why the Original IPA Cannot Be Installed Directly (Question 3 & 13)

#### 3.1 Structural Deficiencies in `RoS-Legacy-iOS.ipa`
Inspection of the archive entries confirms:
1. `embedded.mobileprovision`: **MISSING** (0 matches in archive).
2. `_CodeSignature/CodeResources`: **MISSING** (0 matches in archive).
3. The embedded Mach-O binary `client` retains an expired/stripped CMS signature from its original NetEase release (`application-identifier`: `QKNZB3E3BF.com.netease.chiji`), while `Info.plist` declares `CFBundleIdentifier = net.roslegacy.ios`.

#### 3.2 Operating System Enforcement (Apple AMFI)
When a non-jailbroken physical iOS device attempts to install an `.ipa` via OTA or USB:
1. The iOS installation service (`appstored`) unpacks the archive into a temporary staging area.
2. It inspects the bundle root for `embedded.mobileprovision`.
   - **Result on original IPA:** Fails immediately with `0xe8008015` (`ApplicationVerificationFailed: No provisioning profile found`).
3. If a profile were injected without re-signing the binary:
   - Kernel extension `AppleMobileFileIntegrity` (AMFI) computes page hashes of `client` and compares them to `LC_CODE_SIGNATURE`.
   - Because the provisioning profile's App ID and developer team do not match the old NetEase CMS signature, the kernel halts execution with `SIGKILL (CODESIGNING)`.

**Inescapable Technical Reality:**  
It is physically and mathematically impossible for any stock iOS device to install or boot `RoS-Legacy-iOS.ipa` as it exists today.

---

### 4. The Separation of Master Archive vs Signed Distribution Copy

To satisfy both the strict project preservation charter (*"The original IPA must remain completely unchanged"*) and the physical requirement of iOS execution:

A **two-artifact separation model** must be adopted:

```
+---------------------------------------------------------------------------------------+
|                         TWO-ARTIFACT PRESERVATION ARCHITECTURE                        |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  [ MASTER ARCHIVAL COPY (UNTOUCHED FOREVER) ]                                         |
|  File: D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa                                      |
|  SHA-256: D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55          |
|  Access: READ-ONLY (Strictly immutable archival master)                               |
|  Role: Historical forensic reference; never signed, never modified, never deployed.   |
|                                                                                       |
|                                  | (Read-only copy operation)                         |
|                                  v                                                    |
|                                                                                       |
|  [ WORKING BUILD STAGING (EPHEMERAL) ]                                                |
|  Directory: build/stage/Payload/client.app/                                           |
|  Action: Adds private server public key, embeds Ad Hoc profile, signs with cert.      |
|                                                                                       |
|                                  | (Packaged by build pipeline)                       |
|                                  v                                                    |
|                                                                                       |
|  [ SIGNED DISTRIBUTION ARTIFACT (DEPLOYED TO FRIENDS) ]                               |
|  File: distribution/RoS-Legacy-AdHoc-Distribution.ipa                                 |
|  SHA-256: <Unique hash generated per signing cycle>                                   |
|  Role: Hosted on HTTPS server for itms-services:// OTA distribution to registered     |
|        player devices. Regenerated annually when provisioning profile renews.         |
|                                                                                       |
+---------------------------------------------------------------------------------------+
```

---

### 5. Archival Preservation Protocols (Question 14)

To ensure the master archive is never corrupted, altered, or overwritten:

1. **Operating System File System Locks:**
   Apply read-only attributes to the original files:
   ```powershell
   Set-ItemProperty -Path 'D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa' -Name IsReadOnly -Value $true
   Set-ItemProperty -Path 'D:\ROS-Legacy-Analysis\extracted\Payload\client.app\client' -Name IsReadOnly -Value $true
   ```
2. **Dedicated Archival Vault Directory:**
   In Phase L1, move the master copies into a dedicated directory:
   `D:\ROS-Legacy-Analysis\archive\master_original\`
3. **Automated Hash Verification Gate in Build Scripts:**
   Every build or packaging script must execute an automated pre-flight integrity check:
   ```python
   EXPECTED_IPA_HASH = "D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55"
   actual_hash = hashlib.sha256(open("RoS-Legacy-iOS.ipa", "rb").read()).hexdigest().upper()
   assert actual_hash == EXPECTED_IPA_HASH, "FATAL: Original IPA hash mismatch! Build aborted."
   ```
4. **Copy-On-Write Staging:**
   Build scripts must only ever read the original IPA as an input stream to extract files into an isolated temporary directory. The original file path must never be opened in write mode (`"w"`, `"wb"`, `"a"`, or `"r+"`).

---

### 6. Summary Conclusion

1. The original IPA `RoS-Legacy-iOS.ipa` is an unsigned archival master and cannot be installed directly on physical iOS devices.
2. Generating a separately signed distribution IPA (`RoS-Legacy-AdHoc-Distribution.ipa`) is mandatory for physical installation.
3. The original master remains 100% untouched and preserved under strict cryptographic validation.
