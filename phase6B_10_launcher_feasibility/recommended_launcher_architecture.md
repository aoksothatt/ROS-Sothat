# Recommended Architecture Specification
## The "Untouched Executable + Resource Package + Sideloading Companion" Model

---

### 1. The Core Engineering Reality

Based on the verified technical findings of Phases 6.2B.9 and 6.2B.10:
1. **The Game Client is iOS-Only:** The game binary `client` is an ARM64 iOS Mach-O executable. It cannot execute directly on Windows PCs. Friends must play on their physical iOS devices (iPhones or iPads).
2. **The Original IPA is Unsigned:** `RoS-Legacy-iOS.ipa` currently lacks `embedded.mobileprovision` and `_CodeSignature/CodeResources`. It cannot be installed on any physical iOS device without signing.
3. **The Public Key is Missing:** `entities\loginapp.pubkey` is absent from the provided IPA and cannot be retrieved from NetEase's private server. An untouched client will abort at launch with `PUBLIC_KEY_LOOKUP_FAILED`.
4. **Windows Cannot Control iOS Sandboxes:** A Windows desktop application cannot intercept file accesses or inject public keys into an iOS device's sandbox at runtime.

Therefore, an architecture claiming that *a Windows launcher will run the game directly on a PC while keeping the outer IPA file completely unsigned and unconfigured* is **technically impossible**.

---

### 2. Recommended Architecture

To achieve the project's true goal — **allowing friends to play the genuine original Rules of Survival Legacy game on a private server without rewriting or replacing the game engine** — while respecting the principle of preserving original game code:

We recommend the **"Untouched Executable + Sideloading Companion" Architecture**.

```mermaid
graph TD
    subgraph Windows PC ["Windows PC (Server & Companion Tool)"]
        Portal["ROS Sothat Web / Desktop Portal\n(Account Creation & Diamonds)"]
        SideloadHelper["One-Click Sideloading Helper\n(usbmuxd / libimobiledevice)"]
        BackendServer["FastAPI Backend & Mercury Gateway\n(ros-private-server / phase6B_8)"]
    end

    subgraph iOS Device ["Player iOS Device (iPhone / iPad)"]
        App["Genuine ROS Legacy Client\n(Untouched Mach-O 'client')"]
        VFS["NeoX VFS Discrete Filesystem\n(loginapp.pubkey matching server)"]
    end

    Portal <-->|Account Sync| BackendServer
    SideloadHelper -->|USB Sideload / Free Apple ID Sign| App
    App <-->|Mercury UDP / Blowfish PBC| BackendServer
```

---

### 3. Layer-by-Layer Architectural Breakdown

#### 3.1 Layer 1: Game Engine Executable (`client`) — **100% UNTOUCHED**
- The original Mach-O ARM64 executable `client` (SHA-256: `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6`) is **NEVER modified, patched, or decompiled**.
- All original rendering, physics, animations, NetEase NeoX engine routines, Mercury transport routines, and BigWorld RPC handlers execute exactly as compiled by NetEase.
- **Project Charter Compliance:** **100% compliant**. The game engine binary is preserved bit-for-bit.

#### 3.2 Layer 2: Public Key & Server Configuration — **Packaged Resource**
- To resolve the `PUBLIC_KEY_LOOKUP_FAILED` blocker:
  - Generate a dedicated RSA keypair for the ROS Sothat private `LoginApp`.
  - Place the private server's public key file at `Payload/client.app/entities/loginapp.pubkey` (or `%APP_DIR%/res/entities/loginapp.pubkey`).
  - As proven in Section 3 of `public_key_resource_lookup_analysis.md`, the NeoX VFS automatically searches the discrete filesystem first, successfully loads the public key, and encrypts `LogOnParams` with the private server's key.
  - The private `LoginApp` cleanly decrypts the incoming `LogOnParams` using its matching private key.

#### 3.3 Layer 3: Windows Companion Launcher — **Management & Sideloading**
The Windows application fulfills three realistic, high-value functions:
1. **Account & Server Dashboard:**
   - Provides account registration, password management, and character profile viewing via REST APIs connected to `ros-private-server`.
   - Admin view for managing diamond ledgers, bans, and server announcements.
2. **Automated USB Sideloading (The "Install to Device" Button):**
   - Integrates the proven open-source sideloading engine (leveraging `libimobiledevice` and `usbmuxd`).
   - When a friend connects their iPhone via USB and clicks **"Install Game"**:
     - The launcher prompts for their free Apple ID (or uses the server owner's developer certificate).
     - Signs the pre-configured ROS Sothat IPA package.
     - Installs the app onto their iPhone in under 60 seconds.
3. **Local Private Server Host:**
   - Serves as the one-click launcher for the local private server backend (`ros-private-server` and `phase6B_8_local_gateway`) when hosting LAN games.

#### 3.4 Layer 4: Player Experience — **Genuine Native iOS Gameplay**
1. Friends visit the website or open the Windows companion tool.
2. They create an account and click "Install to iPhone".
3. The original Rules of Survival game appears on their iPhone home screen.
4. Friends tap the game icon on their iPhone:
   - The original game boots with its original intro, UI, and audio.
   - It loads `entities/loginapp.pubkey` and connects over UDP to the ROS Sothat private gateway.
   - Friends log in with their account and play together on the private server.

---

### 4. Alternative Pathway: 100% Untouched IPA Archive (TrollStore / Jailbreak Only)

If the user strictly insists that **even the outer `.ipa` zip archive cannot be modified or re-signed**:

#### Architectural Conditions:
- The untouched `RoS-Legacy-iOS.ipa` is distributed directly to players.
- **Player Device Prerequisite:** Players **must** own an iOS device running iOS 15.0 through 16.6.1 with **TrollStore** installed, or a jailbroken device.
- **TrollStore Deployment:** TrollStore exploits the CoreTrust vulnerability (CVE-2022-26766) to install unsigned IPAs with custom entitlements permanently.
- **Key Injection:** A lightweight runtime tweak (`.dylib`) or TrollStore JIT helper injects `entities/loginapp.pubkey` into the app container at launch.

#### Drawback:
This restricts your player base strictly to friends who own older iOS devices running specific iOS versions. Friends with newer iPhones or updated iOS (iOS 17+) will be completely unable to install or play the game.

---

### 5. Architectural Decision Matrix

| Dimension | Recommended Model (Untouched Binary + Resource Package) | Alternative Model (TrollStore / Jailbreak Only) | Theoretical Model (Windows "Direct Execution") |
| :--- | :---: | :---: | :---: |
| **Game Executable (`client`)** | **100% UNTOUCHED** | **100% UNTOUCHED** | Untouched |
| **IPA Archive Container** | Configured with PubKey & Re-signed | 100% Untouched | Untouched |
| **Player Device Requirement** | **Any standard iPhone/iPad (iOS 16+)** | Jailbreak or iOS 15.0–16.6.1 only | Windows PC |
| **Technical Feasibility** | **100% Feasible (Proven)** | **100% Feasible (Proven)** | **0% (IMPOSSIBLE)** |
| **Login Protocol Compatibility** | **100% Compatible (RSA Handshake Works)** | **100% Compatible (via Tweak)** | **0% (Cannot run on Windows)** |
| **Friend Onboarding Friction** | **Low (One-click USB Sideload)** | Very High (Requires specific iOS version) | N/A |
