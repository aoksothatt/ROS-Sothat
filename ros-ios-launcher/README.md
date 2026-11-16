# ROS-Sothat Native iOS Launcher (SwiftUI)

The official native mobile companion and game launcher for the **ROS-Sothat Rules of Survival Legacy** private server ecosystem.

---

## 1. Architecture & Technology Stack

- **UI Framework:** Apple SwiftUI (Declarative UI, responsive, ProMotion 120Hz support)
- **Language:** Swift 5.9+ / 5.0 compatible
- **Target OS:** iOS 15.0+, iPadOS 15.0+, macOS 12.0+ (Catalyst / Native Mac)
- **Device Family:** iPhone (Target 1) & iPad (Target 2)
- **Theme:** Tactical Dark Gaming UI (Dark charcoal `#080B10`, `#101720`, `#151E29`, and Antique Gold `#D7A84B` accents)

---

## 2. Directory Structure

```
ros-ios-launcher/
├── Package.swift                                      # SPM package definition
├── ROSSothatLauncher.xcodeproj/
│   └── project.pbxproj                               # Standard Xcode project file
├── Sources/
│   └── ROSSothatLauncher/
│       ├── ROSSothatLauncherApp.swift                # Main App Entry Point (@main)
│       ├── Theme/
│       │   └── ThemeColors.swift                     # Tactical color palette & hex decoder
│       ├── Models/
│       │   ├── Player.swift                          # PlayerProfile model
│       │   ├── GameVersion.swift                     # Version & server metadata
│       │   ├── Announcement.swift                    # News & changelog model
│       │   └── MockData.swift                        # Initial offline state & mock fixtures
│       ├── ViewModels/
│       │   ├── AuthViewModel.swift                   # Mock email OTP authentication
│       │   ├── LauncherViewModel.swift               # Screen navigation & server ping
│       │   └── DownloadViewModel.swift               # Download progress & checksum verifier
│       ├── Views/
│       │   ├── RootView.swift                        # Screen router & bottom tactical navigation bar
│       │   ├── Components/
│       │   │   ├── BrandHeader.swift                 # Header bar with live server status
│       │   │   ├── PrimaryButton.swift               # Gradient gold button with loading state
│       │   │   ├── SecondaryButton.swift             # Tactical dark button with border
│       │   │   ├── TacticalCard.swift                # Dark container card with subtle glow
│       │   │   ├── CustomTextField.swift             # Input field with icon support
│       │   │   └── StatusBadge.swift                 # Status pill (Gold, Beta, Online, Warning)
│       │   └── Screens/
│       │       ├── SplashScreen.swift                # Animated emblem splash screen
│       │       ├── WelcomeScreen.swift               # Hero landing screen & guest mode
│       │       ├── SignInScreen.swift                # Operator email OTP login
│       │       ├── CreateAccountScreen.swift         # New operator registration
│       │       ├── HomeDashboardScreen.swift         # Player stats, diamond ledger & announcements
│       │       ├── PlayerProfileScreen.swift         # Detailed combat telemetry (K/D, Win rate)
│       │       ├── GameDownloadScreen.swift          # Download simulation & SHA-256 verifier
│       │       ├── InstallationGuideScreen.swift     # AltStore, Sideloadly, Xcode instructions
│       │       └── PlayScreen.swift                  # War room dispatch & Mercury handshake simulation
│       └── Resources/
│           └── Info.plist                            # Bundle configuration & permissions
└── README.md
```

---

## 3. How to Open and Compile on macOS

### Prerequisites
- Mac running macOS 14 (Sonoma) or macOS 15 (Sequoia)
- Xcode 15.0 or later installed from the Mac App Store
- Apple Developer ID (free personal account or paid developer program)

### Opening in Xcode
1. Double-click `ROSSothatLauncher.xcodeproj` to open the project in Xcode.
2. Alternatively, in Terminal:
   ```bash
   cd ros-ios-launcher
   open ROSSothatLauncher.xcodeproj
   ```
3. In the project navigator, select the root **ROSSothatLauncher** project.
4. Under **Signing & Capabilities**:
   - Check **Automatically manage signing**.
   - Select your personal team in the **Team** dropdown.
   - Change the **Bundle Identifier** suffix if needed for your personal signing identity (e.g. `com.<yourname>.rossothat.launcher`).
5. In the top toolbar, select your connected iPhone/iPad or an iOS Simulator (e.g. *iPhone 15 Pro*).
6. Press **Cmd + R** or click the **Play** button to build and launch the application.

---

## 4. Ad Hoc Provisioning & Sideloading (Without Xcode)

To distribute the built `.ipa` to friends without putting it on the public Apple App Store:

### Method A: AltStore (Wireless Auto-Refresh)
1. Install AltServer on Mac/Windows.
2. Install AltStore onto the target iPhone/iPad.
3. Transfer `ROSSothatLauncher.ipa` to the iPhone (via AirDrop, iCloud Drive, or the website Download page).
4. In AltStore, navigate to **My Apps > '+' > Select IPA**. AltStore signs and installs the app directly.

### Method B: Sideloadly (Direct USB Sideload)
1. Open Sideloadly on Mac or Windows.
2. Connect your iPhone via USB.
3. Drag `ROSSothatLauncher.ipa` into Sideloadly.
4. Enter your personal Apple ID and click **Start**.

### Mandatory First-Launch Device Settings
- **Trust Certificate:** `Settings > General > VPN & Device Management > Tap Apple ID > Trust`.
- **Developer Mode (iOS 16+):** `Settings > Privacy & Security > Developer Mode > ON > Restart device`.

---

## 5. Development Environment Matrix

| Capability | Windows (Current Host) | macOS with Xcode |
| :--- | :--- | :--- |
| **Website & Download Portal** | Fully buildable & testable (`npm run build`, `npm test` 72/72 PASS) | Fully buildable & testable |
| **Swift Source Architecture** | Fully authored & structured | Fully authored & structured |
| **Swift Package / Xcode Project** | Fully authored (`Package.swift`, `project.pbxproj`) | Fully openable & editable |
| **Native iOS Binary Compilation** | **Unavailable** (Requires Apple LLVM / clang / SDKs on Darwin) | **Available** (`xcodebuild` / Xcode GUI) |
| **iOS Simulator Execution** | **Unavailable** (Darwin hypervisor required) | **Available** (iOS Simulator) |
| **Physical iPhone Deployment** | Sideloading via Sideloadly possible once IPA is built | Direct USB debugging & deployment |
