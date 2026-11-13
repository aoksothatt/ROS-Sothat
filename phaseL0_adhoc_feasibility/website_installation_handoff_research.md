# ROS Sothat — Phase L0 Deliverable 2
## Website Installation Handoff & Manifest Research

**Phase:** Phase L0 (Ad Hoc Distribution Feasibility Research)  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_adhoc_feasibility\`  
**Date:** 2026-11-13  
**Status:** COMPLETE — RESEARCH REPORT  

---

### 1. Executive Summary

This report analyzes the technical requirements and operating system boundary constraints for installing iOS applications via a private HTTPS website using Apple's **Wireless App Distribution** protocol. It specifically investigates the format of the XML distribution manifest (`manifest.plist`), TLS certificate requirements, web server MIME type configurations, and the exact handoff boundaries between in-app code and the iOS installation daemon (`appstored`).

The critical finding is that **an iOS application cannot directly install an `.ipa` package from its own sandbox onto the device**. Instead, all iOS app installations on stock (non-jailbroken) devices must be handed off to the iOS system daemon via the custom URL scheme `itms-services://`.

---

### 2. The Apple Wireless App Distribution Specification

#### 2.1 The `itms-services://` Protocol Link
Apple's wireless app installation is invoked through a custom URI scheme handled by the MobileSafari and SpringBoard subsystems:
```
itms-services://?action=download-manifest&url=https://ros-sothat.example.com/manifest.plist
```
When this URI is evaluated (either when tapped by a user in Safari or triggered programmatically via `UIApplication.shared.open`), iOS executes the following pipeline:
1. Passes the query string to the system daemon (`appstored` on modern iOS; historically `itunesstored`).
2. Issues an HTTPS GET request to retrieve the manifest XML file.
3. Parses the dictionary keys: `bundle-identifier`, `bundle-version`, `title`, and `assets`.
4. Displays a modal system alert:
   > **"ros-sothat.example.com would like to install 'RoS Legacy'"**  
   > `[ Cancel ]` `[ Install ]`
5. If the user taps `[ Install ]`, the system creates a placeholder icon on the SpringBoard home screen with a circular download progress indicator.
6. The system downloads the `.ipa` archive directly from the URL specified inside the manifest.
7. The system extracts the payload, verifies code signatures, validates that the device's UDID is present in `embedded.mobileprovision`, verifies entitlements, and registers the application with LaunchServices.

---

### 3. XML Manifest Structure (`manifest.plist`) Specification

The manifest is an XML Property List adhering to Apple's DTD. Below is the exact production-ready schema required for both the ROS Sothat Launcher and the Rules of Survival Legacy game:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>items</key>
    <array>
        <dict>
            <key>assets</key>
            <array>
                <!-- Mandatory: URL to the signed .ipa package -->
                <dict>
                    <key>kind</key>
                    <string>software-package</string>
                    <key>url</key>
                    <string>https://ros-sothat.example.com/downloads/RoS-Legacy-AdHoc.ipa</string>
                </dict>
                <!-- Optional but Recommended: 57x57 or 60x60 display icon during download -->
                <dict>
                    <key>kind</key>
                    <string>display-image</string>
                    <key>needs-shine</key>
                    <false/>
                    <key>url</key>
                    <string>https://ros-sothat.example.com/assets/icon57.png</string>
                </dict>
                <!-- Optional but Recommended: 512x512 full-size App Store image -->
                <dict>
                    <key>kind</key>
                    <string>full-size-image</string>
                    <key>needs-shine</key>
                    <false/>
                    <key>url</key>
                    <string>https://ros-sothat.example.com/assets/icon512.png</string>
                </dict>
            </array>
            <key>metadata</key>
            <dict>
                <!-- CRITICAL: Must match CFBundleIdentifier in Info.plist -->
                <key>bundle-identifier</key>
                <string>net.roslegacy.ios</string>
                <!-- CRITICAL: Must match CFBundleShortVersionString in Info.plist -->
                <key>bundle-version</key>
                <string>1.0</string>
                <key>kind</key>
                <string>software</string>
                <!-- Display name shown in the system installation alert -->
                <key>title</key>
                <string>RoS Legacy</string>
            </dict>
        </dict>
    </array>
</dict>
</plist>
```

#### Detailed Metadata Validation Rules:
1. `bundle-identifier`: **Must match `CFBundleIdentifier` in `Info.plist` byte-for-byte.** If there is a mismatch between the manifest string and the binary bundle, `appstored` will abort the installation at 100% completion with the generic error *"Unable to Install App"*.
2. `bundle-version`: **Must match `CFBundleShortVersionString` or `CFBundleVersion`.**
3. `software-package url`: Must point directly to the binary `.ipa` file. The server hosting the `.ipa` must support HTTP Range requests (`Accept-Ranges: bytes`) for resumable downloads of large assets (RoS Legacy is ~2.0 GB).

---

### 4. HTTPS, TLS, and Web Server Requirements

Apple strictly enforces Transport Layer Security (TLS) on all OTA distribution endpoints.

#### 4.1 SSL/TLS Certificate Constraints
- **Public Certificate Authority Required:** The TLS certificate on `ros-sothat.example.com` must be issued by a root Certificate Authority trusted by default in iOS (e.g. Let's Encrypt, DigiCert, Cloudflare, Google Trust Services).
- **Self-Signed Certificates are Rejected:** If the server uses a self-signed certificate, iOS will silently reject the manifest download with zero user feedback (or log `NSError: The certificate for this server is invalid`).
  *(Note: A self-signed cert can work only if the server owner manually installs a root CA `.crt` into the player's iOS Settings and enables "Full Trust for Root Certificates" under Settings -> General -> About -> Certificate Trust Settings — a high-friction process not recommended for friends).*
- **TLS Version:** Modern iOS (iOS 15–18+) requires **TLS 1.2 or TLS 1.3**.

#### 4.2 Web Server MIME Type Configuration
The HTTP server (whether hosted on Windows via Nginx, Caddy, or Python FastAPI) must transmit the correct `Content-Type` headers:

| File Extension | Target Asset | Required MIME Type |
| :--- | :--- | :--- |
| `.plist` | Installation Manifest | `application/xml` or `text/xml` |
| `.ipa` | iOS Application Archive | `application/octet-stream` or `application/x-itunes-ipa` |
| `.mobileconfig` | Device Enrollment Profile | `application/x-apple-aspen-config` |
| `.png` | App Icons | `image/png` |

---

### 5. In-App Download vs System Handoff (Questions 5 & 6)

#### 5.1 The Sandbox Boundary: Can an App Install an IPA Locally? (Question 5)
> **Is installation possible when the game download begins inside another iOS app?**

**NO, NOT DIRECTLY.**  
On stock (non-jailbroken) iOS, the operating system strictly isolates applications inside unique sandboxes (`/var/mobile/Containers/Data/Application/<UUID>/`):
1. **No PackageInstaller API:** iOS provides **zero public APIs** permitting an application to install software. There is no equivalent to Android's `PackageInstaller` or Windows' `ShellExecute("setup.exe")`.
2. **Private MobileInstallation Framework:** The private framework `MobileInstallation.framework` exposes functions like `MobileInstallationInstall()`. However, calling this framework requires the private entitlement:
   `com.apple.private.mobileinstall.installApp`  
   This entitlement is restricted to Apple's own system daemons (`appstored`, `installd`). If an Ad Hoc provisioned third-party app attempts to invoke `MobileInstallation`, AMFI immediately kills the app or returns an entitlement permission error (`kAMFIErrorNoEntitlement`).
3. **The Localhost HTTPS Trap:** If the launcher downloads a 2 GB `.ipa` file into its sandbox and attempts to start an in-process local HTTP server on `127.0.0.1` to pass `itms-services://?action=download-manifest&url=http://127.0.0.1:8080/manifest.plist`:
   - `appstored` runs outside the app's network sandbox in a system daemon context.
   - Apple's `itms-services://` loader **hard-rejects non-HTTPS URLs**.
   - Generating a valid, trusted TLS certificate for `127.0.0.1` locally inside an iOS app without custom root CA installation is technically impossible.
   - If the launcher is suspended when the user confirms the installation dialog, the local server process terminates, aborting the download.

**Conclusion:** The actual `.ipa` binary download and installation **MUST be performed by the iOS system daemon (`appstored`)** fetching from an external HTTPS server.

#### 5.2 The Supported Installation Handoff (Question 6)
> **Can the launcher open Safari or another supported installation handoff after downloading the game?**

**YES.**  
The launcher can trigger the official Apple installation handoff in two distinct, supported ways:

##### Method A: Direct In-App `itms-services://` Invocation (Cleanest UX)
The launcher does not even need to open Safari. It can invoke the `itms-services` scheme directly from Swift:
```swift
func triggerGameInstallation() {
    let manifestURL = "https://ros-sothat.example.com/manifests/ros-legacy.plist"
    guard let url = URL(string: "itms-services://?action=download-manifest&url=\(manifestURL)") else { return }
    
    DispatchQueue.main.async {
        UIApplication.shared.open(url, options: [:]) { success in
            if success {
                print("[Launcher] Installation handoff delivered to iOS system daemon.")
            } else {
                print("[Launcher] Failed to invoke itms-services scheme.")
            }
        }
    }
}
```
**User Experience:**  
When the user taps "Install Game" inside the launcher, the iOS system prompt (*"ros-sothat.example.com would like to install 'RoS Legacy'"*) pops up **directly on top of the launcher UI**. The user taps "Install". The system begins installing the game in the background on the home screen.

##### Method B: Web Portal Handoff (Safari Fallback)
If desired, the launcher can open Safari to a dedicated web portal page:
```swift
let webURL = URL(string: "https://ros-sothat.example.com/install/game")!
UIApplication.shared.open(webURL)
```
Safari loads the page, where a single prominent button triggers the `itms-services://` link.

---

### 6. Summary of Installation Handoff Feasibility

```
+---------------------------------------------------------------------------------------+
|                               INSTALLATION HANDOFF MATRIX                             |
+-----------------------------------+-----------+---------------------------------------+
| Architectural Concept             | Feasible? | Technical Explanation                 |
+-----------------------------------+-----------+---------------------------------------+
| In-App Direct File Extraction     | NO        | Blocked by sandbox & lack of system   |
| (Launcher writes files to disk)   |           | MobileInstallation entitlements.      |
+-----------------------------------+-----------+---------------------------------------+
| In-App Localhost Proxy Install    | NO        | itms-services strictly rejects        |
| (127.0.0.1 HTTP proxy in launcher)|           | non-HTTPS; daemon background killing. |
+-----------------------------------+-----------+---------------------------------------+
| In-App itms-services Trigger      | **YES**   | Fully supported. Invokes system       |
| (Launcher opens itms URL)         |           | prompt directly on top of launcher.   |
+-----------------------------------+-----------+---------------------------------------+
| Safari itms-services Trigger      | **YES**   | Standard Apple OTA distribution path. |
| (Player installs from web portal) |           | 100% compliant with Apple design.     |
+-----------------------------------+-----------+---------------------------------------+
```
