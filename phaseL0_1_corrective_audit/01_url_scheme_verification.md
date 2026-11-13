# ROS Sothat — Phase L0.1 Audit Deliverable 1
## URL Scheme Verification & Static Analysis Report

**Phase:** Phase L0.1 (Corrective Audit & Master Architecture)  
**Audit Target:** `RoS-Legacy-iOS.ipa` (`Payload/client.app/Info.plist` and `Payload/client.app/client`)  
**Audit Date:** 2026-11-13  
**Status:** COMPLETE — STATIC AUDIT WITH THREE-TIER CLASSIFICATION  

---

### 1. Executive Summary

This report performs an independent static inspection of the original game archive `D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa` to verify whether the custom URL scheme `rosmobile://` can be used by an external launcher application to detect installation and launch the game on an iOS device.

The audit confirms from static manifest evidence that `rosmobile` is officially registered under `CFBundleURLTypes` in `Payload/client.app/Info.plist`. In addition, native Objective-C URL-handling dispatchers (`application:openURL:options:` and `handleOpenURL:`) are present in the Mach-O binary. However, **whether opening a bare `rosmobile://` URL without parameters boots cleanly to the main menu without crashing or stalling requires physical device validation and cannot be claimed as proven from static code analysis alone.**

---

### 2. Static Manifest Inspection (`Info.plist`)

Direct inspection of `Payload/client.app/Info.plist` extracted in-memory from `RoS-Legacy-iOS.ipa` confirms the exact registered URL types:

```python
CFBundleURLTypes = [
    {
        'CFBundleTypeRole': 'Editor',
        'CFBundleURLName': 'rosmobile',
        'CFBundleURLSchemes': ['rosmobile']
    },
    {
        'CFBundleTypeRole': 'Editor',
        'CFBundleURLSchemes': ['com.netease.mpay.w8js77wd9v53j9rv']
    },
    {
        'CFBundleTypeRole': 'Editor',
        'CFBundleURLSchemes': ['fb165387204058528']
    },
    {
        'CFBundleTypeRole': 'Editor',
        'CFBundleURLSchemes': ['twitterkit-K9WHSfgBy5bX433ReDvWLGvmc']
    },
    {
        'CFBundleTypeRole': 'Editor',
        'CFBundleURLName': 'twitch',
        'CFBundleURLSchemes': ['twitch-h45naxx1gb']
    },
    {
        'CFBundleTypeRole': 'Editor',
        'CFBundleURLName': 'unisdk',
        'CFBundleURLSchemes': ['unisdk']
    }
]
```

#### Key Observations:
1. `rosmobile` is an explicit custom URL scheme with `CFBundleTypeRole = "Editor"` and `CFBundleURLName = "rosmobile"`.
2. Several third-party callback schemes are also registered: NetEase MPay (`com.netease.mpay...`), Facebook SDK (`fb...`), TwitterKit, Twitch, and NetEase UniSDK (`unisdk`).
3. Under iOS LaunchServices rules, any application that registers a scheme in `CFBundleURLSchemes` causes the operating system to map that scheme to the app's bundle identifier upon installation.

---

### 3. Mach-O Executable Binary Analysis (`client`)

Analysis of string literals and Objective-C symbols in `extracted/Payload/client.app/client` revealed the following URL-handling infrastructure:

#### A. Selector Occurrences
- `application:openURL:options:` — **9 occurrences**
- `application:openURL:sourceApplication:annotation:` — **7 occurrences**
- `handleOpenURL:` — **18 occurrences**
- `openURL:` — **25 occurrences**

#### B. Implementing Classes & Contexts
The binary routes incoming URL dispatches through NetEase SDK layers:
- `NtAdPlatform` (`-[NtAdPlatform application:openURL:options:]`)
- `NtSdkNetEase` (`-[NtSdkNetEase application:openURL:options:]`)
- `NtSdkBase` (`-[NtSdkBase application:openURL:options:]`)
- `NMOInternManager` (`-[NMOInternManager application:openURL:options:]`)
- `NtSdkFacebook` (`+[NtSdkFacebook application:openURL:options:]`)
- `NtAdPlatformAppsFlyer` (`-[NtAdPlatformAppsFlyer application:openURL:options:]`)

#### C. Scheme Dispatch Logic
When iOS invokes `application:openURL:options:` on the application delegate, the URL string is forwarded to NetEase's UniSDK routing subsystem (`[unisdk] handleOpenURL: %@`). 
- Third-party callback schemes (`fb...`, `twitterkit...`, `com.netease.mpay...`) parse tokens and return results to in-game payment or social modules.
- The literal string `rosmobile` does not appear as a hardcoded static string in the compiled Mach-O binary. This indicates that scheme matching is handled either dynamically by UniSDK configuration tables, or the scheme serves as a general application-level deep-link entry point routed into Python scripts.

---

### 4. Three-Tier Evidence Classification

To maintain strict scientific and engineering honesty, findings are separated into three tiers:

```
+-----------------------------------------------------------------------------------------------+
|                               THREE-TIER EVIDENCE CLASSIFICATION                              |
+---------------------------+-----------------------------------+-------------------------------+
| Tier                      | Finding / Claim                   | Evidence Source & Confidence  |
+---------------------------+-----------------------------------+-------------------------------+
| **TIER 1: CONFIRMED FROM  | 1. CFBundleURLSchemes registers   | In-memory extraction of       |
| STATIC EVIDENCE**         |    'rosmobile' in Info.plist.     | Payload/client.app/Info.plist |
|                           | 2. App declares Editor role.      | (100% Verified).              |
|                           | 3. Client binary implements       | Mach-O symbol analysis at     |
|                           |    application:openURL:options:   | VA 0x102c53792+ (Verified).   |
|                           | 4. External apps can query it via | Standard iOS LaunchServices   |
|                           |    canOpenURL("rosmobile://")     | LSApplicationQueriesSchemes.  |
+---------------------------+-----------------------------------+-------------------------------+
| **TIER 2: STRONGLY        | 1. Invoking rosmobile:// via      | Standard iOS SpringBoard      |
| INDICATED**               |    UIApplication.open will bring  | behavior for any registered   |
|                           |    the game process to foreground.| URL scheme on stock iOS.      |
|                           | 2. UniSDK receives the URL object | Symbol references in          |
|                           |    and evaluates path/query.      | NtSdkNetEase & NMOInternMgr.  |
+---------------------------+-----------------------------------+-------------------------------+
| **TIER 3: REQUIRES REAL-  | 1. Whether a BARE rosmobile://    | UNPROVEN UNTIL TESTED ON A    |
| DEVICE TESTING**          |    URL boots to the main menu     | PHYSICAL IPHONE RUNNING A     |
|                           |    or crashes due to missing args.| COMPATIBLE IOS VERSION.       |
|                           | 2. Whether specific query params  | Requires dynamic runtime      |
|                           |    (e.g. rosmobile://login?token=)| tracing during app launch.    |
|                           |    are expected or required.      |                               |
|                           | 3. Behavior when launched cold    | iOS app lifecycle test        |
|                           |    (process terminated) vs warm.  | on physical device.           |
+---------------------------+-----------------------------------+-------------------------------+
```

---

### 5. Architectural Recommendations for Phase L1

1. **Do Not Claim URL Launching is Proven:** Phase L0's claim that `open("rosmobile://")` is a guaranteed one-click launch mechanism must be downgraded to **strongly indicated, pending physical device validation**.
2. **Companion Launcher Implementation Strategy:**
   - In the launcher prototype, implement the query check `canOpenURL("rosmobile://")` for detection (this is fully supported by iOS LaunchServices).
   - Implement the launch trigger `open("rosmobile://")`, but include fallback handling: if the game fails to launch or if the user prefers, provide an on-screen instruction informing the player that the game has been installed and can be opened directly from the iOS Home Screen.
3. **Physical Device Test Protocol:** When physical Ad Hoc testing is authorized in Phase L1, execute dedicated URL scheme invocation tests:
   - Test Case A: Bare `rosmobile://` from cold start.
   - Test Case B: Bare `rosmobile://` from background suspended state.
   - Test Case C: `rosmobile://` with sample query parameters (`rosmobile://action=launch`).
