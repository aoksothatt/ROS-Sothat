# ROS Sothat — Phase L0.1 Audit Deliverable 7
## Corrected Implementation Roadmap & Gated Phase Specifications

**Phase:** Phase L0.1 (Corrective Audit & Master Architecture)  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_1_corrective_audit\`  
**Date:** 2026-11-13  
**Status:** COMPLETE — 11-PHASE GATED MASTER ROADMAP  

---

### 1. Executive Summary

This roadmap establishes the corrected, prioritized 11-phase development sequence for the ROS Sothat project. Each phase is defined with strict entry dependencies, reusable assets, explicit deliverables, risk mitigations, test criteria, formal approval gates, and rollback procedures.

---

### 2. Master Prioritization Overview

```
+-----------------------------------------------------------------------------------------------+
|                               11-PHASE MASTER EXECUTION ROADMAP                               |
+-------+---------------------------------------+-----------------------+-----------------------+
| Phase | Phase Name                            | Core Domain           | Primary Dependency    |
+-------+---------------------------------------+-----------------------+-----------------------+
| P01   | Master Architecture & Corrective Audit| Research & Governance | None (CURRENT PHASE)  |
| P02   | Backend Foundation & Email OTP        | Backend / Auth Engine | Phase P01             |
| P03   | Private Website & Public Landing Page | Web Frontend          | Phase P02             |
| P04   | Player Self-Service Dashboard         | Web Frontend          | Phase P02, P03        |
| P05   | Admin Dashboard & Economy Console     | Web Management        | Phase P02, P04        |
| P06   | iOS Companion Launcher Prototype      | Native iOS (SwiftUI)  | Phase P02, P03        |
| P07   | Ad Hoc Distribution Packaging Pipeline| DevOps / Code Signing | Phase P03, P06        |
| P08   | Original-Client LoginApp Compatibility| Game Network Daemon   | Phase P02, P07        |
| P09   | BaseApp Service & Lobby Session Sync  | Game Server Core      | Phase P08             |
| P10   | CellApp World Simulation Engine       | Multiplayer Real-Time | Phase P09             |
| P11   | Full End-to-End Friend Integration    | Alpha Testing (10–20) | All Previous Phases   |
+-------+---------------------------------------+-----------------------+-----------------------+
```

---

### 3. Detailed Specifications for All 11 Phases

---

#### Phase P01: Master Architecture & Corrective Audit (Current Phase)
- **Objective:** Re-align project scope on supporting the existing game, resolve Phase L0 oversimplifications, audit URL scheme findings, and establish immutable preservation rules.
- **Dependencies:** None.
- **Existing Reusable Assets:** `RoS-Legacy-iOS.ipa`, Phase 10 through 13.4 reports.
- **New Work Required:** Independent static inspection of `Info.plist`, analysis of `.mobileconfig` friction, drafting corrected master architecture and roadmap.
- **Risks:** Unresolved assumptions about client launch behavior.
- **Tests:** SHA-256 hash assertions of original IPA and Mach-O binaries.
- **Acceptance Criteria:** All 9 Phase L0.1 deliverables completed; original assets 100% untouched.
- **Approval Gate:** Explicit user review and sign-off before Phase P02.
- **Rollback Plan:** Discard draft audit directory; revert to Phase 6.2B.13.4 baseline.

---

#### Phase P02: Backend Foundation & Email OTP Integration
- **Objective:** Upgrade existing FastAPI backend (`ros-private-server`) to support email OTP verification during registration and login, and ensure unified SQLite/PostgreSQL configuration.
- **Dependencies:** Phase P01.
- **Existing Reusable Assets:** `app/account/`, `app/player/`, `app/economy/`, `app/inventory/`, `app/admin/`.
- **New Work Required:** Add OTP generation/verification service (`EmailVerificationService`), transactional email provider integration (SMTP / Resend), and OTP schemas.
- **Risks:** Email delivery latency or spam filtering.
- **Tests:** Pytest test suite for OTP creation, rate limiting, expiry, and successful verification.
- **Acceptance Criteria:** Players can register and verify accounts via email OTP in under 30 seconds; 100% test pass rate.
- **Approval Gate:** User sign-off on email dispatch integration.
- **Rollback Plan:** Revert `app/account/` changes to password-only baseline.

---

#### Phase P03: Private Website & Public Landing Page
- **Objective:** Create a responsive web portal providing private community onboarding, launcher OTA download links, account registration, and server announcements.
- **Dependencies:** Phase P02.
- **Existing Reusable Assets:** Static game assets, FastAPI static file mounts.
- **New Work Required:** HTML5/CSS3/JS responsive frontend (or React/Vue), HTTPS manifest hosting route (`/manifests/launcher.plist`), Cloudflare Tunnel configuration.
- **Risks:** Browser rendering inconsistencies across mobile Safari and desktop browsers.
- **Tests:** Mobile Safari rendering test, HTTPS certificate trust validation, OTA manifest MIME type validation.
- **Acceptance Criteria:** Website loads cleanly on iPhone Safari; manifest link triggers iOS installation prompt.
- **Approval Gate:** User review of website visual design and mobile functionality.
- **Rollback Plan:** Static site files archived; API routes untouched.

---

#### Phase P04: Player Self-Service Dashboard
- **Objective:** Implement a web-based self-service player dashboard allowing players to inspect their account profile, real-time diamond balance, inventory loadouts, and statistics.
- **Dependencies:** Phase P02, Phase P03.
- **Existing Reusable Assets:** `app/player/router.py`, `app/economy/router.py`, `app/inventory/router.py`.
- **New Work Required:** Player dashboard web UI components (wallet card, inventory grid, match history table, password manager).
- **Risks:** XSS or unauthorized access to other players' profile details.
- **Tests:** JWT authentication guards, profile retrieval unit tests, UI responsive layout checks.
- **Acceptance Criteria:** Authenticated players view their exact diamond balance and inventory items.
- **Approval Gate:** User approval of player dashboard UI.
- **Rollback Plan:** Revert dashboard templates.

---

#### Phase P05: Admin Dashboard & Economy Console
- **Objective:** Implement the web-based administrative console enabling authorized admins to search players, grant/deduct diamonds, manage item catalog, and moderate accounts.
- **Dependencies:** Phase P02, Phase P04.
- **Existing Reusable Assets:** `app/admin/router.py` (12 endpoints, RBAC, self-ban protection).
- **New Work Required:** Admin web frontend: Player management table, Diamond grant/deduct modal with mandatory reason logging, Item catalog manager, Live server stats monitor.
- **Risks:** Admin privilege escalation or accidental diamond grants.
- **Tests:** Full RBAC permission suite, atomic transaction ledger validation, self-demotion prevention tests.
- **Acceptance Criteria:** Admins can grant diamonds and items with instantaneous ACID ledger updates and full audit trail.
- **Approval Gate:** Security audit and user sign-off on admin controls.
- **Rollback Plan:** Admin dashboard routes disabled; existing API remains intact.

---

#### Phase P06: iOS Companion Launcher Prototype
- **Objective:** Build a native Swift/SwiftUI companion application for iPhone managing authentication, game library display, installation detection, and launch triggers.
- **Dependencies:** Phase P02, Phase P03.
- **Existing Reusable Assets:** Backend REST authentication endpoints, `rosmobile://` scheme findings.
- **New Work Required:** Xcode project (SwiftUI), Email OTP login view, Game library view with RoS Legacy card, `canOpenURL("rosmobile://")` detection, `itms-services://` OTA handoff trigger.
- **Risks:** Apple rejection of private URL scheme queries if not declared in `LSApplicationQueriesSchemes`.
- **Tests:** Simulator testing, Unit tests for API client, URL scheme query assertion.
- **Acceptance Criteria:** Launcher compiles cleanly, authenticates via OTP, detects game installation state, and presents handoff.
- **Approval Gate:** Xcode build review and user sign-off.
- **Rollback Plan:** Xcode project isolated in separate repository/folder.

---

#### Phase P07: Ad Hoc Distribution Packaging Pipeline
- **Objective:** Establish the clean-room, immutable packaging pipeline that generates signed distribution IPAs for registered friend devices while keeping original files untouched.
- **Dependencies:** Phase P03, Phase P06.
- **Existing Reusable Assets:** `RoS-Legacy-iOS.ipa` (Master), Apple Distribution Certificate.
- **New Work Required:** Staging build script (`package_adhoc.py`), inserting `entities/loginapp.pubkey`, embedding Ad Hoc profile, code signing with `codesign` / `zsign` / `fastlane`.
- **Risks:** Incomplete bundle resource sealing (`CodeResources` invalidation).
- **Tests:** Pre-build and post-build SHA-256 assertions on master IPA; `codesign --verify --deep` on output IPA.
- **Acceptance Criteria:** Signed distribution IPA installs via OTA on enrolled physical test iPhone; master IPA hash 100% unchanged.
- **Approval Gate:** Verification of physical test device installation.
- **Rollback Plan:** Delete ephemeral staging directory; master archive remains untouched.

---

#### Phase P08: Original-Client LoginApp Compatibility
- **Objective:** Bridge the standalone UDP `LoginAppDaemon` (`phase6B_13_3_udp_daemon`) with the `ros-private-server` relational database and test against incoming client handshakes.
- **Dependencies:** Phase P02, Phase P07.
- **Existing Reusable Assets:** `LoginAppDaemon`, `RsaOaepEngine`, `BlowfishAddressFilter`, `InMemoryAccountRepository`.
- **New Work Required:** Database adapter replacing `InMemoryAccountRepository` with async SQLAlchemy query to `accounts` table; LAN IP configuration.
- **Risks:** Database latency impacting UDP datagram response windows.
- **Tests:** Master 51-test suite executed against live database adapter.
- **Acceptance Criteria:** Live database credentials authenticate successfully through UDP LoginApp; returns valid Blowfish-encrypted BaseApp pointer.
- **Approval Gate:** Zero-regression sign-off on 51 automated tests.
- **Rollback Plan:** Revert to in-memory repository adapter.

---

#### Phase P09: BaseApp Service & Lobby Session Sync
- **Objective:** Implement the initial UDP `BaseApp` daemon (`port 20014`) to handle post-login client attachment, entity instantiation, and lobby synchronization.
- **Dependencies:** Phase P08.
- **Existing Reusable Assets:** Phase 6.2B.9 `BaseAppExtInterface` mappings, Blowfish PBC session filter.
- **New Work Required:** `BaseAppDaemon` (asyncio UDP), `baseAppLogin` (0x00) handler, `authenticate` (0x01) handler, entity property sync for player diamonds and cosmetics, Redis IPC bridge.
- **Risks:** Missing undocumented BigWorld bundle message formats.
- **Tests:** Synthetic BaseApp client integration tests, packet round-trip tests.
- **Acceptance Criteria:** Game client successfully transitions from LoginApp to BaseApp and loads main lobby screen.
- **Approval Gate:** Live client connection demo.
- **Rollback Plan:** Isolate BaseApp codebase in modular package.

---

#### Phase P10: CellApp World Simulation Engine
- **Objective:** Implement the `CellApp` service to manage real-time in-match multiplayer coordinates, player movement physics, weapon firing, damage registration, and zone mechanics.
- **Dependencies:** Phase P09.
- **Existing Reusable Assets:** `avatarUpdateImplicit` (0x02) and `avatarUpdateExplicit` (0x03) interface definitions.
- **New Work Required:** Spatial cell grid partition, movement delta broadcast engine, hit registration validator, match lifecycle state machine.
- **Risks:** UDP packet jitter and desynchronization between multiple physical clients.
- **Tests:** Multi-client synthetic bots stress testing spatial updates.
- **Acceptance Criteria:** Multiple players can spawn into the same game world, see each other's avatars move, and receive position updates.
- **Approval Gate:** Gameplay prototype sign-off.
- **Rollback Plan:** CellApp module disabled; server operates in lobby-only mode.

---

#### Phase P11: Full End-to-End Friend Integration & Testing
- **Objective:** Conduct closed alpha deployment to 10–20 invited friends, distributing the launcher and game via the private website and hosting live multiplayer matches.
- **Dependencies:** All previous phases (P01 through P10).
- **Existing Reusable Assets:** Entire completed ecosystem.
- **New Work Required:** Device UDID onboarding for 10–20 friends, deployment of signed IPAs to HTTPS download portal, server monitoring.
- **Risks:** Real-world Wi-Fi packet loss, friend device OS version divergence (iOS 15 vs 18).
- **Tests:** Live 10–20 player match execution, economy grant validation during live game.
- **Acceptance Criteria:** 10–20 friends install launcher, install game, log in, view diamonds, join match, and play together on private server.
- **Approval Gate:** Project completion sign-off.
- **Rollback Plan:** Emergency server shutdown; account data preserved in database backups.
