# ROS Sothat — Phase L0.1 Audit Deliverable 4
## Corrected Master Project Scope & System Architecture

**Phase:** Phase L0.1 (Corrective Audit & Master Architecture)  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_1_corrective_audit\`  
**Date:** 2026-11-13  
**Status:** COMPLETE — MASTER ARCHITECTURAL BLUEPRINT  

---

### 1. Fundamental Scope Clarification

> **THE PROJECT IS NOT TO REBUILD RULES OF SURVIVAL.**

The original Rules of Survival Legacy game client already exists in complete, production-ready form inside:  
`D:\ROS-Legacy-Analysis\RoS-Legacy-iOS.ipa`

All rendering, 3D graphics, physics, character animations, vehicle controllers, weapons, UI screens, sound effects, NetEase NeoX engine routines, and BigWorld network codecs are compiled directly into the original Mach-O executable `client` (`51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6`). We do not write, design, or substitute a replacement game client.

Our engineering objective is to build the **supporting private infrastructure ecosystem** required to allow 10–20 invited friends to connect their genuine iOS game clients to our private server and play together.

---

### 2. The Five Master Architectural Components

```
+---------------------------------------------------------------------------------------------------------------+
|                                      ROS SOTHAT MASTER ECOSYSTEM ARCHITECTURE                                 |
+---------------------------------------------------------------------------------------------------------------+
|                                                                                                               |
|  +---------------------------+  +---------------------------+  +-------------------------------------------+  |
|  |       [A] WEBSITE         |  |     [B] iOS LAUNCHER      |  |         [C] PLAYER DASHBOARD              |  |
|  | - Private Landing Page    |  | - Email OTP Login         |  | - Profile & Account Information           |  |
|  | - Launcher OTA Download   |  | - Player Account Sync     |  | - Diamond Balance Display                 |  |
|  | - Account Registration    |  | - Game Library View       |  | - Inventory & Item Management             |  |
|  | - Game Download Info      |  | - OTA Install Handoff     |  | - Player Stats & Match Records            |  |
|  | - News & Announcements    |  | - Installation Detection  |  | - Account Standing (Active / Suspended)   |  |
|  |                           |  | - Play Button (rosmobile) |  |                                           |  |
|  +---------------------------+  +---------------------------+  +-------------------------------------------+  |
|               |                               |                                      |                        |
|               +-------------------------------+--------------------------------------+                        |
|                                               v                                                               |
|  +---------------------------------------------------------------------------------------------------------+  |
|  |                                  SHARED BACKEND API & DATA PLATFORM                                     |  |
|  |  FastAPI Framework (ros-private-server) | SQLAlchemy ORM | SQLite / PostgreSQL Relational Database      |  |
|  |  ACID Diamond Ledger | Relational Inventory Catalog | Session & Auth Repositories | Admin RBAC          |  |
|  +---------------------------------------------------------------------------------------------------------+  |
|                                               ^                                      ^                        |
|               +-------------------------------+                                      |                        |
|               |                                                                      |                        |
|  +---------------------------+                                 +-------------------------------------------+  |
|  |   [D] ADMIN DASHBOARD     |                                 |         [E] PRIVATE GAME SERVER           |  |
|  | - Player Search & Inspect |                                 | - LoginApp Daemon (UDP 127.0.0.1:20013)   |  |
|  | - Grant / Deduct Diamonds | <============================== | - BaseApp Service (UDP :20014)            |  |
|  | - Grant / Remove Items    |         Internal RPC /          | - CellApp World Simulation Engine         |  |
|  | - Ban / Unban Accounts    |       Database Sync Gate        | - Player Session Manager                  |  |
|  | - View Online Presences   |                                 | - Lobby & Room Management                 |  |
|  | - Room & Match History    |                                 | - Matchmaking Coordinator                 |  |
|  | - Economy Audit Ledger    |                                 | - BigWorld Mercury UDP Protocol Engine    |  |
|  | - Admin Roles & Audit Log |                                 |                                           |  |
|  +---------------------------+                                 +-------------------------------------------+  |
|                                                                                      ^                        |
|                                                                                      | (Mercury UDP Transport)|
|                                                                                      v                        |
|                                                                +-------------------------------------------+  |
|                                                                |          EXISTING ORIGINAL CLIENT         |  |
|                                                                |    Genuine NetEase Rules of Survival      |  |
|                                                                |    Installed on Friends' Physical iPhones |  |
|                                                                +-------------------------------------------+  |
|                                                                                                               |
+---------------------------------------------------------------------------------------------------------------+
```

---

### 3. Detailed Component Specifications

#### Component A: The Website (Web Portal)
- **Role:** The public-facing (or invite-gated) web presence for the private community.
- **Key Modules:**
  1. *Landing Page:* Cinematic game art, project introduction, and onboarding instructions.
  2. *Launcher Download:* Direct link triggering the OTA manifest for the ROS Sothat Launcher (`itms-services://?action=download-manifest&url=https://.../launcher-manifest.plist`).
  3. *Account Registration & Login:* Web interface for registering user accounts with email OTP validation.
  4. *Game Download Information:* Detailed instructions for friends on how to install and open the game.
  5. *Support & Announcements:* Changelogs, server maintenance notices, and private community Discord/forum links.
- **Technology Stack:** Static HTML5 / CSS3 / JavaScript or lightweight frontend (Vue / React / Jinja2 templates) served by FastAPI / Nginx on the Windows server.

#### Component B: The iOS Companion Launcher
- **Role:** A native companion iOS app installed on players' iPhones serving as the game manager and community hub.
- **Key Modules:**
  1. *Email OTP Login:* Player logs in securely via email verification code sent from the server.
  2. *Player Account View:* Displays username, account ID, registration date, and diamond balance.
  3. *Game Library:* Shows Rules of Survival Legacy in the game list with cover art and status.
  4. *Installation Handoff:* Tapping "Download" triggers the Apple-supported OTA installation prompt for the game (`itms-services://?action=download-manifest&url=https://.../game-manifest.plist`).
  5. *Installation Detection:* Queries `canOpenURL("rosmobile://")` via `LSApplicationQueriesSchemes` to detect whether the game is installed on the home screen.
  6. *Play Button:* Once installed, updates UI to "Play Game" and invokes `open("rosmobile://")` to launch the original game.
- **Technology Stack:** Swift 5.9+ / SwiftUI, targeting iOS 15.0–18+.

#### Component C: The Player Dashboard
- **Role:** Self-service web/mobile interface for authenticated players.
- **Key Modules:**
  1. *Profile & Account Overview:* View character nickname, GID, avatar appearance, and account status.
  2. *Diamond Balance:* Real-time view of current diamond wallet balance and recent transaction history.
  3. *Inventory & Items:* View cosmetic loadout, weapon skins, parachutes, and clothing items stored in the database.
  4. *Player Statistics:* Kills, matches played, victories, win rate, and historical match logs.
  5. *Account Security:* Change password, view active session tokens, and manage email settings.

#### Component D: The Admin Dashboard
- **Role:** Operational management suite for server administrators to moderate the game and economy.
- **Key Modules:**
  1. *Player Management:* Search players by username, account ID, or character GID.
  2. *Economy Control (Diamonds):* Atomically grant or deduct diamonds with mandatory administrative reason logging.
  3. *Inventory Management (Items):* Grant or revoke items from player inventories; create new catalog items.
  4. *Moderation & Enforcement:* Suspend (ban) or reactivate player accounts with reason tracking and self-ban guards.
  5. *Live Operational Monitoring:* Real-time count of active lobby presences, open rooms, and matchmaking queues.
  6. *Match History Inspection:* View room outcomes, participant lists, and match scores.
  7. *Auditing & RBAC:* Complete transaction logs for every diamond grant/deduction and inventory modification; role delegation (`player`, `admin`, `superadmin`).
- **Technology Stack:** Existing backend endpoints (`app/admin/router.py`) connected to a responsive web interface.

#### Component E: The Private Game Server
- **Role:** The core backend infrastructure providing authentication, network routing, session state, and multiplayer simulation for the original game client.
- **Key Modules:**
  1. *LoginApp Daemon:* UDP service listening on port 20013. Receives Mercury `login` packets, decrypts RSA-OAEP credentials, verifies accounts against the database, and returns Blowfish-encrypted BaseApp addresses. (Phase 13.3 prototype).
  2. *BaseApp Service:* UDP service listening on port 20014. Handles client session attachment, entity instantiation, player state, lobby synchronization, and diamond/inventory updates.
  3. *CellApp Simulation Engine:* Coordinates real-time game-world updates, movement physics, player positions, combat hit detection, and zone shrinking.
  4. *Player Session Manager:* Tracks connected player UDP endpoints, sequence numbers, and session timeouts.
  5. *Lobby & Room Manager:* Manages pre-game squads, custom rooms, and match rosters.
  6. *Matchmaking Coordinator:* Automatically pools queued players into balanced match instances.
- **Technology Stack:** Python `asyncio` UDP transport daemons integrated with the shared database and Mercury protocol engine.

---

### 4. Component Scope & Boundary Matrix

| Component | Target Runtime | Primary Technology | Dependency on Game Binary? |
| :--- | :--- | :--- | :---: |
| **A. Website** | Browser (PC / Mobile) | HTML / CSS / FastAPI | **NONE** (Pure web) |
| **B. iOS Launcher** | iPhone (iOS 15–18) | Swift / SwiftUI | Minimal (`rosmobile://` check) |
| **C. Player Dashboard** | Browser / Webview | Web App / REST API | **NONE** (Reads DB) |
| **D. Admin Dashboard** | Browser (Admin) | Web App / REST API | **NONE** (Reads DB) |
| **E. Private Server** | Windows Server | Asyncio UDP / Mercury | **CRITICAL** (Speaks NetEase wire protocol) |
| **Original Game** | iPhone (iOS 15–18) | NetEase NeoX / BigWorld | **EXISTING ASSET** (Untouched) |
