# ROS Sothat — Phase 6.2B.1: Original iOS Client Compatibility Research Report

**Date:** November 12, 2026  
**Auditor & Research Agent:** Antigravity (Advanced Agentic Coding Assistant)  
**Governing Strategy:** Option A (Independent Private-Server Backend; 100% Unmodified Original ROS Legacy iOS Client IPA)  
**Target Client Binary:** `RoS-Legacy-iOS.ipa` (`Payload/client.app/client`, ARM64, Version 1.610637.617289)  
**Target Backend Codebase:** `C:\Users\MSI\Downloads\Telegram Desktop\ROS-Legacy-Analysis\ros-private-server`  
**Research Mode:** Strict READ-ONLY Investigation (Zero application code modified; zero database records modified; zero IPA patching or re-signing)  

---

## 1. Executive Summary

This Phase 6.2B.1 research report investigates whether the original, unmodified **Rules of Survival (ROS) Legacy iOS client package (`RoS-Legacy-iOS.ipa`)** can realistically communicate with our independent private-server backend (`ros-private-server`).

### Core Conclusion & Verdict
**FINAL VERDICT: CURRENT APPROACH NOT FEASIBLE (For Strictly Unmodified Original IPA under Option A)**  
**SECONDARY VERDICT: FEASIBLE WITH MAJOR BLOCKERS (For Sideloaded Public-Key Swap IPA & Synthetic-Client Development)**

The investigation confirms an absolute mathematical and architectural barrier:
1. **The 1024-Bit RSA Key Exchange Barrier**: The original Mach-O binary (`Payload/client.app/client`) strictly enforces the presence and loading of NetEase's embedded 1024-bit RSA public key (`entities\loginapp.pubkey` in `res/entities.npk`) during `ServerConnection::logOnBegin` (VA `0x1008abe00`). During logon, the client generates an ephemeral symmetric Blowfish key, encrypts it with NetEase's RSA public key, and transmits it via UDP. Immediately upon receiving server acknowledgment, the client activates `neox::bwclient::Mercury::EncryptionFilter` on the BaseApp UDP channel using that Blowfish key. Because only NetEase possesses the matching 1024-bit private key, our private server cannot decrypt the client's Blowfish key. Consequently, all subsequent UDP gameplay packets from the client cannot be deciphered, and any unencrypted server replies are discarded by the client.
2. **Absence of Legitimate Private Server Configuration**: Static analysis of all 3,983 decompiled client Python scripts and native ARM64 Mach-O disassembly reveals **zero configuration options, preference toggles, or sandbox overrides** capable of redirecting the access server hostname (`as-h45na.easebar.com:50010`) or substituting the RSA public key.
3. **Viability of Independent Backend & Synthetic Client**: While direct out-of-the-box connectivity with the unmodified IPA is blocked, our independent private server architecture (`ros-private-server`) remains **100% viable**. All backend REST APIs, account systems, relational inventory, admin RBAC, diamond ledgers, and Mercury UDP transport prototypes have been validated with **133 passing automated tests**. A synthetic client test harness can fully reproduce the client-side Mercury protocol, providing complete verification of backend gameplay logic without violating Option A.

---

## 2. Previous Research Reused

This phase builds directly upon confirmed findings from earlier technical milestones:

1. **Phase 3 (`ros_phase3_mercury_entity_mapping_report.md`)**:
   - Identified BigWorld Technology Mercury networking framework under C++ namespace `neox::bwclient::Mercury`.
   - Recovered entity hierarchy: `Account` (ID `0x3F`), `Athlete` / `PlayerAthlete` (ID `0x48`), and `Avatar` / `PlayerAvatar` (ID `0x4B`).
   - Extracted 632 XML `.def` entity definitions and RPC signatures from `res/entities.npk`.
   - Confirmed client-side `BinaryOStream` / `BinaryIStream` serialization schemes.
2. **Phase 5 (`ros_phase5_3_backend_audit_report.md`)**:
   - Baseline REST backend implementing accounts, characters, appearances, rooms, and matchmaking queues.
3. **Phase 6.1 (`ros_phase6_1_transport_prototype_report.md`)**:
   - Implemented discovery service generating the 11-column `server_list_ios.txt` format.
   - Built asynchronous Mercury UDP listener (`asyncio.DatagramProtocol`) with reverse-order footer decoding (Checksum, SeqNum, ACKs, Channel, Fragment) and 256-packet sliding window overflow protection.
4. **Phase 6.1.1 & 6.1.2 (`ros_phase6_1_1_compatibility_validation_report.md`, `ros_phase6_1_2_original_client_compatibility_decision.md`)**:
   - Confirmed disassembly of `LoginInterface` (VA `0x1008cde0c`), `BaseAppExtInterface` (VA `0x1008cde84`), and `ClientInterface` (VA `0x1008ce144`).
   - Identified the cryptographic RSA public key check in `ServerConnection::logOnBegin` (VA `0x1008abe00`).
5. **Phase 6.2A.1 through 6.2A.3.2**:
   - Built admin RBAC, secure CLI first-admin bootstrap, relational diamond transaction ledger with concurrency control, relational item catalog, player inventory management, and audit remediation with 133 passing tests.

---

## 3. Original IPA Inspection Findings

Inspection of `RoS-Legacy-iOS.ipa` (`846,004,086 bytes`) confirms the physical structure of the shipping iOS client:

```
RoS-Legacy-iOS.ipa (ZIP Archive)
├── Payload/client.app/
│   ├── client                                (Mach-O 64-bit executable ARM64, 63,028,880 bytes)
│   ├── Info.plist                            (Application configuration & permissions)
│   ├── script.npk                            (Virtual archive: 3,983 obfuscated Python 2.7 bytecode scripts)
│   ├── assets.npk                            (Core UI and shader assets)
│   ├── res/
│   │   ├── entities.npk                      (632 BigWorld XML defs + entities\loginapp.pubkey)
│   │   ├── common.npk, textures.npk, ui.npk  (3D game models, UI atlases, and world data)
│   │   └── scenario.npk, weather.npk         (Battle royale map terrain and environment)
```

### 3.1 `Info.plist` Configuration Evidence
- **Bundle Identifier**: `net.roslegacy.ios`
- **Short Version String**: `1.610637.617289`
- **Bundle Version**: `1.610637.617289`
- **Display Name**: `RoS Legacy`
- **App Transport Security (`NSAppTransportSecurity`)**:
  ```xml
  <key>NSAppTransportSecurity</key>
  <dict>
      <key>NSAllowsArbitraryLoads</key>
      <true/>
  </dict>
  ```
  *Significance*: Apple's OS-level ATS is configured to permit plaintext HTTP traffic (`NSAllowsArbitraryLoads = True`), meaning iOS will not enforce HTTPS at the operating system level. However, application-level Python scripts explicitly enforce `https://` URLs.
- **Custom URL Schemes (`CFBundleURLTypes`)**:
  - `rosmobile`: Deep-linking and web launch callbacks.
  - `com.netease.mpay.w8js77wd9v53j9rv`: NetEase mpay account SDK integration.
  - `unisdk`: NetEase UniSDK authentication redirect scheme.
  - `fb165387204058528`, `twitterkit-...`, `twitch-...`: Social platform SDK bindings.

---

## 4. Detailed Investigation of Original Client Subsystems

Every discovery is categorized with file name, relevant symbol/resource, address or line, and confirmation status:

```
+------------------------------------------------------------------------------------------------------------------------------------------+
| Subsystem                | Confirmed Binary / Script Fact                          | Evidence Reference                    | Type         |
+--------------------------+---------------------------------------------------------+---------------------------------------+--------------+
| 1. Discovery HTTPS       | Requests https://as-h45na.easebar.com:50010/server_list | extconfigs.py (line 12)               | Confirmed    |
| 2. Server List Parsing   | 11 space-delimited columns parsed by parseSAServerInfo  | common/serverlist_utils.py (line 28)  | Confirmed    |
| 3. RSA Public Key Asset  | 1024-bit RSA key loaded from entities\loginapp.pubkey   | res/entities.npk (Entry 0xd9aee0dd)   | Confirmed    |
| 4. Mandatory Key Check   | Aborts with 0x701 PUBLIC_KEY_LOOKUP_FAILED if missing   | client @ VA 0x1008abe00               | Confirmed    |
| 5. Symmetric Cipher      | Blowfish stream cipher activated on BaseApp channel     | client @ VA 0x1008ac410               | Confirmed    |
| 6. LoginApp UDP RPC      | LoginInterface: probe (ID 0), login (ID 1, uint16 var)  | client @ VA 0x1008cde0c               | Confirmed    |
| 7. BaseApp UDP RPC       | BaseAppExtInterface: baseAppLogin (ID 0), msg (ID 17)   | client @ VA 0x1008cde84               | Confirmed    |
| 8. Client UDP RPC        | ClientInterface: createBasePlayer (ID 5), cell (ID 6)   | client @ VA 0x1008ce144               | Confirmed    |
| 9. Datagram Footers      | Tail unpacked: Checksum -> Seq -> ACKs -> Ch -> Frag    | client @ VA 0x100922894               | Confirmed    |
| 10. Sliding Window Cap   | Overflow disconnect if sendWindUsage > 256              | client @ VA 0x10091bf80               | Confirmed    |
| 11. Initial Entity       | Account entity instantiated first via createBasePlayer  | Entities.xml, Account.py              | Confirmed    |
| 12. Lobby Entity         | Athlete (PlayerAthlete) instantiated for hall/lobby     | Athlete.py, Athlete.def               | Confirmed    |
| 13. Matchmaking RPC      | iRosMatch: rosMatchSignSingle, rosMatchSignMulti        | entities/iRosMatch.py                 | Confirmed    |
| 14. Custom Room RPC      | DtsCustomGameRoom: createDtsCustomGame, join            | common/dts_custom_room/DtsCustomRoom  | Confirmed    |
| 15. Battle Transfer      | Athlete.transferToBattleServer transfers to BattleBase  | entities/Athlete.py                   | Confirmed    |
| 16. Battle In-Game Entity| Avatar (PlayerAvatar) instantiated for match world      | entities/Avatar.py, Avatar.def        | Confirmed    |
| 17. Handshake Bundle     | [Blowfish Key || Username || Token || Version] layout   | BigWorld Standard / Engine Inference  | Inferred     |
| 18. Battle Physics Loop  | NetEase CellApp spatial physics and ballistics engine   | Avatar.py shootHit / Engine Inference | Inferred     |
+------------------------------------------------------------------------------------------------------------------------------------------+
```

### 4.1 Login & Authentication Flow Evidence
1. **Access Server Discovery**:
   - The client fetches cluster metadata via HTTPS from `https://as-h45na.easebar.com:50010/server_list_ios.txt`.
   - `extconfigs.py` selects this URL using `game3d.is_release_version()`. In the release Mach-O binary, `is_release_version()` is hardcoded to return `true`.
2. **UniSDK Channel Authentication**:
   - Handled by `helpers/channel/channel_login.py.raw` and `ui/UILogin.py.raw`.
   - Generates authentication tokens. Client scripts contain fallback routines (`verify_func` returning `True`), allowing dummy tokens to be accepted if server-side UniSDK validation is bypassed.
3. **LoginApp UDP Handshake**:
   - Client resolves `login_ip` and `login_port` (default 20001) from the discovery list.
   - `ServerConnection::logOnBegin` (VA `0x1008abe00`) opens `entities\loginapp.pubkey` from `res/entities.npk`.
   - Initializes `PublicKeyCipher::setKey:` (VA `0x100927a20`). If loading fails, sets error code `0x701` and halts.
   - Generates a 56-byte ephemeral symmetric Blowfish key.
   - Packs credentials, client version, and the Blowfish key into a `MemoryOStream`.
   - Encrypts the payload with NetEase's RSA public key using PKCS#1 v1.5 padding.
   - Transmits datagram to LoginApp using `LoginInterface::login` (Method ID 1).
4. **BaseApp Login & Channel Encryption**:
   - LoginApp responds with `LOGON_STATUS_OK (0)`, BaseApp `ip:port`, and a 32-bit `sessionKey`.
   - Client establishes a reliable Mercury channel to BaseApp.
   - **Crucial Step**: Client activates `neox::bwclient::Mercury::EncryptionFilter` (VA `0x1008ac410`) on the BaseApp channel using the generated Blowfish key.
   - Client sends `BaseAppExtInterface::baseAppLogin` (Method ID 0) containing `sessionKey`.
   - BaseApp replies with `ClientInterface::authenticate` (Method ID 0) and `ClientInterface::createBasePlayer` (Method ID 5), instantiating the `Account` entity.

### 4.2 Character Selection & Character Data
- **Lifecycle**: Handled by `Account` and `Athlete` entities (`Account.def`, `Athlete.def`).
- **Flow**:
  1. Client sends `Account.handshake(hotfixMd5, deviceInfo, channelInfo, engineInfo, sauthReply)` via `BaseAppExtInterface::entityMessage` (Method ID 17).
  2. Server responds with `Account.onChannelLogin(retCode, sauthInfo)`.
  3. Server destroys `Account` entity and calls `ClientInterface::createBasePlayer` with entity type `Athlete` (ID `0x48`).
  4. If character already exists, server syncs role properties (`nickname`, `level`, `diamonds`, `gold`).
  5. If character does not exist, server calls `Athlete.showSelectCharacter(usedNames)`. Client prompts UI, user picks nickname and gender, client calls `Athlete.createCharacter(charType, nickname, initialItems)`. Server acknowledges with `Athlete.onCreateCharacter(True, "")` and `Athlete.onRoleCreateSuc(timestamp)`.

### 4.3 Custom Room Creation & Joining
- **Scripts**: `common/dts_custom_room/DtsCustomRoom.py.raw`, `ui/UIDtsCustomRoomEntrance.py.raw`.
- **Entity**: `DtsCustomGameRoom` defined in `DtsCustomGameRoom.def`.
- **Method Signatures**:
  - `createDtsCustomGame(params, name, mapID, pwd, capacity, fpp, teamMode, isPublic, allowOB, cfg1, cfg2, cfg3)` (Client -> BaseApp).
  - `joinDtsCustomGame(roomGID, password)` (Client -> BaseApp).
  - Server confirms with `onCreateDtsCustomGame(DTS_CUSTOM_ROOM_INFO_FOR_CLIENT)` and `onJoinDtsCustomGame(roomState)`.

### 4.4 Matchmaking Communication
- **Scripts**: `entities/iRosMatch.py.raw`, `common/ros_match_utils.py.raw`.
- **Entity**: `iRosMatch` interface component on `Athlete`.
- **Method Signatures**:
  - Solo Queue: `rosMatchSignSingle(matchMode, ruleSet, region)` (Client -> BaseApp).
  - Squad Queue: `rosMatchSignMulti(matchMode, teamSize, teamToken, ruleSet, region)` (Client -> BaseApp).
  - Cancel Queue: `rosMatchCancelSignByMember(matchMode, cancelReason)` (Client -> BaseApp).
  - Server Response: `onRosMatchSignCallback(matchMode, isSuccess, matchData)` (BaseApp -> Client).

### 4.5 Battle-Server Connection Details
- **Transition**: When matchmaking completes or a custom room launches, Lobby BaseApp executes:
  `PlayerAthlete.transferToBattleServer(battleIP, battlePort, playerName, password, backPort)`.
- **Socket Transition**: Client `ConnectMonitor` closes the Lobby BaseApp connection (`BigWorld.logOff()`), switches internal `HostType` to `HostType::BATTLE = 2`, and connects via UDP to `battleIP:battlePort`.
- **World Instantiation**: Battle BaseApp receives `baseAppLogin(token)`, instantiates `PlayerAvatar` (`entities/Avatar.py.raw`), and dispatches:
  - `ClientInterface::spaceViewportInfo(spaceID)`
  - `ClientInterface::createCellPlayer(AvatarEntityID)`
  - `Avatar.loadMap(mapID, preloads, sceneElements)`
- **Real-Time Gameplay**: Combat ballistics (`Avatar.shootHit`, `chargeShootHit`), player movement, and vehicle interaction stream directly over UDP to Battle CellApp.

---

## 5. Compatibility Matrix: Original Client vs Our Private Server

The following matrix compares the requirements of the original iOS client against the implementation in `ros-private-server`:

| Feature | Original Client Requirement | Our Backend Support (`ros-private-server`) | Status | Detailed Assessment |
|---|---|---|---|---|
| **Server Discovery** | HTTPS GET `/server_list_ios.txt` on port 50010; 11 space-separated columns | `DiscoveryService` generates compliant 11-column table verified against recovered parser | **Confirmed Compatible** | Format & parser 100% compatible. Live connection requires DNS redirection and local Root CA profile on iOS device. |
| **Login (Handshake)** | UDP Mercury bundle to LoginApp; encrypted with embedded 1024-bit RSA key (`loginapp.pubkey`) | Mercury UDP socket on port 20001; `LocalRSATestHarness` with synthetic 2048-bit keys | **Blocked by Unavailable Information** | NetEase 1024-bit RSA private key is proprietary and unknown. Server cannot decrypt client Blowfish key from unmodified IPA. |
| **Channel Cipher** | `neox::bwclient::Mercury::EncryptionFilter` using symmetric Blowfish key on BaseApp | Mercury UDP transport processes plaintext datagrams; Blowfish cipher not yet bound to channel | **Not Implemented** | Blowfish stream cipher must be added to `mercury/channel.py`. |
| **Character Management** | BigWorld Entity RPCs on `Account` & `Athlete` (`handshake`, `createCharacter`) | REST API (`/api/v1/player/character`), SQLite/PostgreSQL relational database schema | **Partially Compatible** | Business logic, character records, and settings fully exist in database. BigWorld entity wire serialization over Mercury is not yet implemented. |
| **Inventory & Items** | Entity property sync on `Athlete` (`appearances`, item slots) via `updateEntity` | Relational item catalog, player inventory slots, stack checks, and audit ledger in `app/inventory/` | **Partially Compatible** | Relational catalog, stack safety, and admin management 100% complete. BigWorld entity replication over Mercury is not yet implemented. |
| **Room Creation** | `DtsCustomGameRoom.createDtsCustomGame` & `joinDtsCustomGame` RPCs to BaseApp | In-memory `RoomService`, custom room rules, password protection, and host controls via REST | **Partially Compatible** | Room lifecycle, slot assignment, and state machines exist. BigWorld Mercury RPC dispatcher is not yet implemented. |
| **Matchmaking** | `iRosMatch.rosMatchSignSingle` & `rosMatchSignMulti` RPCs to BaseApp | In-memory `MatchmakingService`, ticket queues, TTL cleanup, and pairing logic via REST | **Partially Compatible** | Ticket pairing logic exists in backend. BigWorld Mercury RPC wire handler is not yet implemented. |
| **Battle Connection** | `Athlete.transferToBattleServer` to Battle BaseApp/CellApp; 3D space, physics, combat | UDP port configuration present in discovery entries (`battle_port`), but no CellApp exists | **Not Implemented** | Dedicated spatial game server, physics simulation, and hit registration (`shootHit`) are not yet implemented. |

---

## 6. Synthetic Client Testing Plan

Because the original client cannot connect out-of-the-box due to the RSA cryptographic lock, an automated **Synthetic Client Test Harness** must be used to validate the private server.

### 6.1 Testing Architecture
The synthetic client runs in Python within our test suite, communicating directly over UDP sockets with `ros-private-server`:

```
+-----------------------------------------------------------------------------------------+
|                                Synthetic Client Harness                                 |
+-----------------------------------------------------------------------------------------+
| 1. Discovery Client:                                                                    |
|    - HTTP GET http://localhost:8000/server_list_ios.txt                                 |
|    - Verifies 11-column parsing using recovered parseSAServerInfo                       |
|                                                                                         |
| 2. Mercury UDP Client Nub:                                                              |
|    - Connects to UDP localhost:20001 (LoginApp)                                         |
|    - Serializes datagrams with reverse-order footers (Checksum, Seq, ACKs)              |
|    - Encrypts login bundle using synthetic RSA key pair matching backend test harness   |
|                                                                                         |
| 3. Handshake & Session Engine:                                                          |
|    - Receives LOGON_STATUS_OK, extracts BaseApp port and sessionKey                     |
|    - Reconnects to BaseApp UDP socket                                                   |
|    - Activates local Blowfish EncryptionFilter on virtual channel                       |
|    - Transmits BaseAppExtInterface::baseAppLogin                                        |
|                                                                                         |
| 4. Entity RPC Test Suite:                                                               |
|    - Simulates Account.handshake -> receives Athlete createBasePlayer                   |
|    - Simulates Athlete.createCharacter -> receives onCreateCharacter                   |
|    - Simulates DtsCustomGameRoom.createDtsCustomGame -> verifies room created in backend|
|    - Simulates iRosMatch.rosMatchSignSingle -> verifies queue ticket in backend         |
+-----------------------------------------------------------------------------------------+
```

### 6.2 Key Test Scenarios & Requirements
1. **Required Requests**:
   - `LoginInterface::probe` (Method ID 0, 0 bytes payload).
   - `LoginInterface::login` (Method ID 1, variable-length encrypted bundle).
   - `BaseAppExtInterface::baseAppLogin` (Method ID 0, variable-length sessionKey).
   - `BaseAppExtInterface::entityMessage` (Method ID 17, entity method invocations).
2. **Required Fields**:
   - Client version integer (`1610637`), username string, dummy auth token, ephemeral Blowfish key (56 bytes).
3. **Expected Responses**:
   - `LOGON_STATUS_OK (0)` with BaseApp address and 32-bit `sessionKey`.
   - `ClientInterface::authenticate (Method 0)` followed by `ClientInterface::createBasePlayer (Method 5)`.
4. **Session & Error Handling**:
   - Verify unacknowledged packet overflow disconnects at 256 packets.
   - Verify retransmission on packet loss via sliding window selective ACKs.
   - Verify corrupted datagram checksums are dropped without crash.

> [!IMPORTANT]
> Success of the synthetic client demonstrates that our private server correctly implements the BigWorld Mercury protocol, state machines, and business logic. It does **not** prove that an unmodified physical iOS client can connect, because the physical iOS client remains bound by NetEase's proprietary RSA key.

---

## 7. Analysis of Technical Blockers

Blockers are prioritized by critical importance:

### Blocker 1: The 1024-Bit RSA Key Exchange (CRITICAL HARD BLOCKER)
- **Problem**: Client encrypts login bundle with NetEase's public key (`entities\loginapp.pubkey`). Backend cannot decrypt without NetEase's private key.
- **Feasibility Assessment**: **Unsolvable for strictly unmodified IPA**. Factoring a 1024-bit RSA modulus requires roughly $2^{80}$ operations, requiring nation-state supercomputing clusters for several months.
- **Alternative (Outside Option A)**: Swapping `loginapp.pubkey` in a sideloaded IPA (AltStore/TrollStore) is **100% solvable** and leaves the Mach-O binary completely unpatched.

### Blocker 2: Server Discovery TLS & DNS Redirection (MEDIUM BLOCKER)
- **Problem**: Client requests `https://as-h45na.easebar.com:50010`. Redirecting this on a local Wi-Fi router causes iOS to reject the self-signed TLS certificate.
- **Feasibility Assessment**: **Solvable without IPA modification**. Can be resolved by installing a custom Root Certificate Authority (CA) profile in iOS Settings (`Settings -> General -> Profile -> Certificate Trust Settings`).

### Blocker 3: BigWorld Entity Wire Serialization (MEDIUM BLOCKER)
- **Problem**: Client uses custom `BinaryOStream` little-endian binary serialization and 632 XML `.def` schemas, not JSON REST APIs.
- **Feasibility Assessment**: **100% Solvable**. Requires implementing Python encoders/decoders matching the recovered `.def` schemas and `alias.xml` types.

### Blocker 4: Room & Matchmaking Protocol Integration (MEDIUM BLOCKER)
- **Problem**: The client expects room creation and matchmaking over Mercury entity RPCs (`DtsCustomGameRoom`, `iRosMatch`), while the backend currently exposes them via FastAPI REST endpoints.
- **Feasibility Assessment**: **100% Solvable**. Bridge the existing `RoomService` and `MatchmakingService` to the Mercury UDP transport via adapter dispatchers.

### Blocker 5: Battle Server & Spatial Simulation (HIGH COMPLEXITY BLOCKER)
- **Problem**: A full battle match requires a dedicated 3D physics server simulating player movement, terrain collision, ballistics (`shootHit`), vehicle physics, safe zone shrinking, and loot drops.
- **Feasibility Assessment**: **Solvable, but High Implementation Effort**. Can be staged incrementally: initial lobby/room presence first, followed by a minimal custom room battle instance.

### Blocker 6: Missing Official NetEase Services (SOLVED / LOW RISK)
- **Problem**: NetEase UniSDK, patch servers, and account services are offline.
- **Feasibility Assessment**: **Solvable**. Client scripts contain fallback paths; discovery endpoints are already emulated; UniSDK authentication can be satisfied with dummy responses.

### Blocker 7: iOS Client Networking Restrictions (LOW RISK)
- **Problem**: Apple ATS policies and background socket suspension.
- **Feasibility Assessment**: **Non-Issue**. `Info.plist` already configures `NSAllowsArbitraryLoads = True`. Local Wi-Fi networking functions unimpeded while the app is active in the foreground.

---

## 8. Estimated Implementation Complexity

```
+-----------------------------------------------------------------------------------------+
| Subsystem                     | Current Status        | Complexity  | Estimated Effort  |
+-------------------------------+-----------------------+-------------+-------------------+
| Server Discovery Service      | 100% Implemented      | Low         | Complete (0 days) |
| Relational Backend Core       | 100% Implemented      | Medium      | Complete (0 days) |
| Mercury UDP Framing & Window  | Prototype Implemented | Medium      | 2–3 days          |
| Blowfish Channel Encryption   | Specified in Research | Medium      | 2–3 days          |
| LoginApp RSA Handshake Gateway| Prototype Implemented | Medium      | 2–3 days          |
| BaseApp Entity Dispatcher     | Recovered XML Defs    | High        | 5–7 days          |
| Custom Room Mercury Binding   | In-Memory REST Ready  | Medium      | 3–4 days          |
| Matchmaking Mercury Binding   | In-Memory REST Ready  | Medium      | 3–4 days          |
| Battle Server (CellApp World) | Not Started           | Very High   | 3–4 weeks         |
+-----------------------------------------------------------------------------------------+
```

---

## 9. Recommended Next Technical Milestone

Based on the research findings and strict adherence to Option A:

### Recommended Path: **Phase 6.2A.4: Private-Room Lifecycle & Host Controls**
Continue developing the independent private server backend:
1. Implement full room lifecycle management (creation, configuration, host migration, start match trigger, player slot management).
2. Build host administrative controls (kick player, change map, password toggle, team size limits).
3. Validate room state machines and concurrency using automated multi-session test harnesses.
4. Keep the original iOS IPA 100% untouched.

*Note on Sideloaded IPA Testing*: If in the future the user chooses to test a physical iOS device, the recommended approach is a research sideloading workflow (AltStore / TrollStore) where only `loginapp.pubkey` is swapped with the server's public key, keeping the Mach-O binary completely original.

---

## 10. Evidence References

1. **Mach-O Executable**: `Payload/client.app/client` (SHA256: `63MB ARM64 binary`)
   - `ServerConnection::logOnBegin`: VA `0x1008abe00`
   - `PublicKeyCipher::setKey:`: VA `0x100927a20`
   - `LoginInterface::probe / login`: VA `0x1008cde0c`
   - `BaseAppExtInterface`: VA `0x1008cde84`
   - `ClientInterface`: VA `0x1008ce144`
   - `Nub::processFilteredPacket`: VA `0x100922894`
   - `Bundle::newMessage`: VA `0x100917b18`
2. **Client Script Archives**: `Payload/client.app/script.npk` (3,983 files decompiled in `extracted/scripts/`)
   - `extconfigs.py`: Access server URL definition (`as-h45na.easebar.com:50010`)
   - `common/serverlist_utils.py`: `parseSAServerInfo` (11-column server list specification)
   - `entities/Account.py`: Initial client logon and channel handshake
   - `entities/Athlete.py`: Lobby player avatar, role creation, and battle transfer
   - `entities/Avatar.py`: In-game player physics avatar and combat reporting
   - `common/dts_custom_room/DtsCustomRoom.py`: Custom room creation and joining
   - `entities/iRosMatch.py`: Solo and squad matchmaking queue RPCs
3. **Virtual File System Assets**: `Payload/client.app/res/entities.npk`
   - `entities\loginapp.pubkey`: NetEase 1024-bit RSA public key (Entry ID `0xd9aee0dd`)
   - 632 XML `.def` entity schemas (`Account.def`, `Athlete.def`, `Avatar.def`, `DtsCustomGameRoom.def`)

---

## 11. Safety & Governance Confirmation

- **No IPA Modifications**: The original `RoS-Legacy-iOS.ipa` remains completely unchanged.
- **No Code Modifications**: No backend files or application code were modified during this read-only research phase.
- **No Database Modifications**: No databases, player records, or migrations were executed.
- **Phase 6.2B.2 has not been started**.

**Status**: Research report complete. Awaiting user review and authorization.
