# ROS Sothat — Phase L0.1 Audit Deliverable 8
## Open Questions, Technical Risks & Mitigation Strategies

**Phase:** Phase L0.1 (Corrective Audit & Master Architecture)  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_1_corrective_audit\`  
**Date:** 2026-11-13  
**Status:** COMPLETE — RISK MANAGEMENT MATRIX  

---

### 1. Executive Summary

This report catalogues all open technical questions, unverified runtime behaviors, and architectural risks identified across Phases L0 and L0.1. By cataloging and categorizing these factors prior to development, the project establishes defensive boundaries, mitigates failure modes early, and prevents ungrounded assumptions from derailing implementation.

---

### 2. Inventory of Open Technical Questions

```
+-----------------------------------------------------------------------------------------------+
|                                  OPEN TECHNICAL QUESTIONS MATRIX                              |
+----+-------------------------------+----------+-----------------------------------------------+
| #  | Question Description          | Severity | Current Status & Planned Resolution           |
+----+-------------------------------+----------+-----------------------------------------------+
| 1  | Bare `rosmobile://` Launch    | HIGH     | UNVERIFIED ON REAL HARDWARE. Info.plist       |
|    | Behavior on Physical iPhone   |          | confirms registration; physical test in Ph L1 |
|    |                               |          | will confirm if bare URL boots to main menu.  |
+----+-------------------------------+----------+-----------------------------------------------+
| 2  | Client Script Entity Property | MEDIUM   | REVERSE ENGINEERING IN PROGRESS. Exact Python |
|    | Name for In-Game Diamonds     |          | attribute name in avatar entity to be confirmed|
|    |                               |          | prior to BaseApp entity sync (Phase 09).      |
+----+-------------------------------+----------+-----------------------------------------------+
| 3  | iOS Local Network Permission  | MEDIUM   | KNOWN IOS 14+ REQUIREMENT. When connecting to |
|    | Prompt (`NSLocalNetwork...`)  |          | LAN servers, iOS displays local network alert;|
|    |                               |          | must verify client Info.plist has description.|
+----+-------------------------------+----------+-----------------------------------------------+
| 4  | Mercury Bundle Fragmentation  | MEDIUM   | DEFERRED FOR SMALL PACKETS; REQUIRED FOR MAP. |
|    | (`FLAG_IS_FRAGMENT`)          |          | Handshakes fit in 1 MTU; room/map packets will|
|    |                               |          | require multi-packet reassembly in Phase 10.  |
+----+-------------------------------+----------+-----------------------------------------------+
| 5  | Physical Wi-Fi Packet Loss &  | LOW      | UNTESTED ON PHYSICAL LAN. Localhost tests     |
|    | Out-of-Order Datagrams        |          | assume zero loss; sequence ACKs needed in LAN.|
+----+-------------------------------+----------+-----------------------------------------------+
| 6  | Annual Ad Hoc Profile Expiry  | LOW      | CONFIRMED APPLE POLICY. 365-day expiration    |
|    | Friction for Friends          |          | managed by annual automated re-signing script.|
+----+-------------------------------+----------+-----------------------------------------------+
```

---

### 3. Detailed Risk Analysis & Mitigation Strategies

#### Risk 1: URL Scheme Launch Fails on Real Hardware
- **Risk Scenario:** When the launcher calls `UIApplication.shared.open(URL(string: "rosmobile://")!)`, the game process crashes on cold boot because UniSDK expects specific deep-link arguments (e.g. `rosmobile://action=start`).
- **Likelihood:** Low to Medium.
- **Impact:** Medium.
- **Defensive Mitigation:**
  1. The launcher companion UI treats the URL launch as a convenience helper, not a single point of failure.
  2. If the URL launch fails, the launcher displays a clear instruction: *"Game is installed! You can also tap the RoS Legacy icon directly on your Home Screen."*
  3. Once on the home screen, tapping the native app icon executes standard `application:didFinishLaunchingWithOptions:`, which is guaranteed to boot cleanly.

#### Risk 2: iOS Local Network Permission Prompt (iOS 14+)
- **Risk Scenario:** Starting in iOS 14, Apple requires apps communicating over local LAN IP addresses (e.g. `192.168.1.x`) to obtain user permission via a system dialog: *"RoS Legacy would like to find and connect to devices on your local network"*. If the user taps "Don't Allow", UDP sockets to the LAN private server fail silently.
- **Likelihood:** High if connecting via LAN IP.
- **Impact:** High.
- **Defensive Mitigation:**
  1. Inform friends during onboarding to tap **"Allow"** if prompted for Local Network access.
  2. Alternatively, route private server traffic through an external domain name (e.g. `gateway.ros-sothat.net`) resolving to the server's public IP or Cloudflare tunnel, bypassing the local network permission dialog entirely.

#### Risk 3: BigWorld Bundle Fragmentation on Large Payloads
- **Risk Scenario:** When a player enters a room with 20 players, or loads a large cosmetic inventory, the server's serialized Mercury bundle exceeds the Ethernet MTU (1500 bytes). If the server does not fragment packets using BigWorld's `FLAG_IS_FRAGMENT` and sequence tracking, UDP datagrams are dropped by network routers.
- **Likelihood:** High during Phase 10 (Multiplayer).
- **Impact:** High.
- **Defensive Mitigation:**
  1. For Phases 01 through 08, all LoginApp and auth packets are strictly under 400 bytes, well below the 1500-byte MTU threshold.
  2. Implement Mercury packet fragmentation and sequence defragmentation as a formal requirement in Phase 09 (BaseApp) and Phase 10 (CellApp).

#### Risk 4: Developer Certificate Expiration or Revocation
- **Risk Scenario:** The Apple Distribution Certificate expires or the developer account credentials are lost, breaking existing installations.
- **Likelihood:** Low.
- **Impact:** High (requires re-signing and re-installing).
- **Defensive Mitigation:**
  1. Store the `.p12` signing key and Apple Developer credentials securely in encrypted offline backups.
  2. Track certificate and provisioning profile expiration dates programmatically via automated reminder alerts.

---

### 4. Summary

All identified risks have clear, viable engineering mitigations that do not compromise the integrity of the original game binaries or violate project preservation constraints.
