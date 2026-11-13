# ROS Sothat — Phase L0 Deliverable 1
## Apple Ad Hoc iOS Distribution Feasibility Research

**Phase:** Phase L0 (Ad Hoc Distribution Feasibility Research)  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_adhoc_feasibility\`  
**Date:** 2026-11-13  
**Status:** COMPLETE — RESEARCH REPORT  

---

### 1. Executive Summary

This report establishes the technical and policy foundations for distributing the **ROS Sothat Launcher** and **Rules of Survival Legacy** game to 10–20 invited friends using Apple's official **Ad Hoc Distribution** framework.

Apple provides Ad Hoc distribution as a sanctioned mechanism for testing and distributing pre-release iOS applications to up to 100 registered devices per device family without submitting the software to the public App Store or passing Apple App Review. This research proves that a private HTTPS distribution website using Over-The-Air (OTA) wireless distribution (`itms-services://`) can successfully deploy signed iOS applications to registered devices.

---

### 2. Apple Ad Hoc Distribution Architecture

#### 2.1 The Over-The-Air (OTA) Distribution Protocol
Apple officially supports distributing Ad Hoc builds wirelessly without connecting devices to a Mac or PC. This mechanism is commonly termed **Over-The-Air (OTA) Wireless Distribution**.

```
+-----------------------------------------------------------------------------------+
|                        APPLE OTA AD HOC WIRELESS DISTRIBUTION                     |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ Player's iPhone (Safari) ]                                                     |
|             |                                                                     |
|             | 1. Taps link: itms-services://?action=download-manifest&url=...     |
|             v                                                                     |
|  [ iOS System Daemon (appstored / itunesstored) ]                                 |
|             |                                                                     |
|             | 2. Fetches HTTPS XML manifest (manifest.plist)                      |
|             v                                                                     |
|  [ ROS Sothat Private HTTPS Server ]                                              |
|             |                                                                     |
|             | 3. Returns manifest.plist containing IPA URL, BundleID, Version     |
|             v                                                                     |
|  [ iOS System Prompt ]                                                            |
|             |                                                                     |
|             | 4. Displays: "example.com would like to install 'RoS Legacy'"       |
|             |    User confirms: [Install]                                         |
|             v                                                                     |
|  [ iOS System Daemon (appstored) ]                                                |
|             |                                                                     |
|             | 5. Downloads signed .ipa over HTTPS                                 |
|             | 6. Unpacks bundle to /var/mobile/Containers/Bundle/Application/    |
|             | 7. Verifies CodeSignature against Apple Worldwide Developer CA      |
|             | 8. Verifies Device UDID is listed in embedded.mobileprovision       |
|             | 9. Verifies Entitlements match provisioning profile                 |
|             v                                                                     |
|  [ SpringBoard Home Screen ]                                                      |
|             |                                                                     |
|             | 10. App icon appears; installs; ready to launch.                    |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

#### 2.2 Core Answer to Question 1: Private Web Distribution
> **Can an Ad Hoc signed iOS application be distributed from a private HTTPS website without publishing it on the public App Store?**

**YES.**  
Under Apple's developer guidelines, an Ad Hoc provisioned application can be hosted on any private web server reachable over HTTPS. It does not require:
- Publishing to the public App Store.
- Undergoing Apple App Review.
- Using Apple TestFlight.
- Sideloading via USB cables on a Mac or PC.

The sole technical requirements imposed by Apple are:
1. The distribution website must serve the manifest and IPA over **valid, trusted HTTPS** (TLS 1.2+ with a trusted certificate; self-signed certificates fail unless explicitly trusted in iOS Settings).
2. The installing device's **UDID must be compiled into the `embedded.mobileprovision` file** included within the app bundle.
3. The app bundle must be signed with the **Apple Distribution Certificate** corresponding to the provisioning profile.

---

### 3. Device UDID Collection & Registration Mechanics

#### 3.1 What is a UDID?
The **Unique Device Identifier (UDID)** is a permanent, hardware-derived 40-character hexadecimal string (older devices) or a 25-character formatted identifier (`XXXXXXXX-XXXXXXXXXXXXXXXX`, iPhone XS / XR and newer) uniquely identifying an Apple device.

#### 3.2 Collection Methods (Answering Question 9)
For 10–20 invited friends, three methods exist for collecting UDIDs:

```
+-----------------------------------------------------------------------------------+
|                            UDID COLLECTION COMPARISON                             |
+-------------------------+--------------------+----------------+-------------------+
| Method                  | Player Friction    | Technical Tool | Recommended For   |
+-------------------------+--------------------+----------------+-------------------+
| A. Web Enrollment       | VERY LOW           | iOS Settings   | **RECOMMENDED**   |
|    (.mobileconfig OTA)  | (2 taps in Safari) | Profile API    | (Friends Group)   |
+-------------------------+--------------------+----------------+-------------------+
| B. Computer USB Cable   | MEDIUM             | iTunes/Finder/ | Fallback for      |
|    (Finder / iTunes)    | (Requires PC/Mac)  | Apple Config.  | desktop users     |
+-------------------------+--------------------+----------------+-------------------+
| C. Third-Party Web Tool | LOW                | udid.io / etc. | Alternative       |
|    (External Service)   | (Privacy risk)     | External host  | quick test        |
+-------------------------+--------------------+----------------+-------------------+
```

##### Recommended Method: Automated `.mobileconfig` Enrollment Profile
Apple provides a sanctioned Over-The-Air device enrollment mechanism using an Apple Configuration Profile (`.mobileconfig`):
1. Friend visits `https://ros-sothat.example.com/enroll`.
2. Friend taps **"Register My iPhone"**.
3. Website serves an XML profile with `PayloadType = Configuration` and a secure callback URL:
   ```xml
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>PayloadDisplayName</key>
       <string>ROS Sothat Device Registration</string>
       <key>PayloadIdentifier</key>
       <string>net.rossothat.enrollment</string>
       <key>PayloadType</key>
       <string>Profile Service</string>
       <key>PayloadUUID</key>
       <string>E2C8465B-9A82-4115-998A-E9D846513A11</string>
       <key>PayloadVersion</key>
       <integer>1</integer>
       <key>URL</key>
       <string>https://ros-sothat.example.com/api/v1/devices/enroll</string>
       <key>DeviceAttributes</key>
       <array>
           <string>UDID</string>
           <string>PRODUCT</string>
           <string>VERSION</string>
           <string>DEVICE_NAME</string>
       </array>
   </dict>
   </plist>
   ```
4. iOS prompts the user: *"This website is trying to download a configuration profile. Do you want to allow this?"*
5. Player opens **Settings -> Profile Downloaded -> Install**.
6. The iOS kernel securely queries the hardware UDID and transmits an encrypted/signed cryptographic payload via HTTPS POST to `https://ros-sothat.example.com/api/v1/devices/enroll`.
7. The ROS Sothat backend records the UDID, friend's email, and device model in the server database.
8. The profile automatically uninstalls or can be removed by the user immediately.

#### 3.3 Registering UDIDs in Apple Developer Portal
Once collected, UDIDs must be registered under the developer account:
- **Manual Web Interface:** Log in to `developer.apple.com` -> *Certificates, Identifiers & Profiles* -> *Devices* -> *Register Device* (input Name and UDID).
- **Automated API:** Apple provides the **App Store Connect API** (`POST /v1/devices`). The ROS Sothat server backend can register device UDIDs programmatically using a developer API key (`.p8`), eliminating manual portal entry.

---

### 4. Apple Device Registration Limits & Annual Renewal Rules (Question 10)

Official Apple Developer Account device rules state:

1. **Quota Ceiling:**
   - **100 iPhones** per membership year.
   - **100 iPads** per membership year.
   - **100 iPod touches** per membership year.
   - **100 Apple Watches** per membership year.
   - **100 Apple TVs** per membership year.
   - *For 10–20 friends, the group will consume 10–20% of the available iPhone quota.*
2. **Device Slot Consumption:**
   - Once a device UDID is registered, it counts against the 100-device limit for the **entire remainder of the 1-year membership cycle**.
   - Disabling or deleting a device in the web portal does **not** free up the slot for a new device during that active membership year.
3. **Annual Reset Opportunity:**
   - At the beginning of each annual membership renewal window (when paying the $99 annual fee), the account administrator is presented with a one-time prompt to **reset the device list**.
   - Unused or obsolete devices can be permanently removed at this time, resetting the available slot count back to 100.

---

### 5. Multi-App Management Under One Developer Account (Question 12)

> **Can one developer account manage both the launcher and game distribution?**

**YES.**  
A single standard $99/year Apple Developer Program account can support:
- Up to **100 App IDs**.
- Unlimited provisioning profiles.
- Up to 2 active Apple Distribution Certificates per account.

The developer registers the 10–20 friend UDIDs once in the portal. Then, two independent App IDs and Ad Hoc profiles are created:
1. **Launcher App ID:** `net.rossothat.launcher` -> Ad Hoc Profile: `ROS_Sothat_Launcher_AdHoc` (contains all 20 UDIDs).
2. **Game App ID:** `net.roslegacy.ios` (or wildcard `net.roslegacy.*`) -> Ad Hoc Profile: `ROS_Legacy_Game_AdHoc` (contains the exact same 20 UDIDs).

Both application IPAs are signed with the same **Apple Distribution Certificate** and distributed over the private website.

---

### 6. Lifecycle Events & Failure Modes (Question 16)

#### 6.1 What Happens When a Player Changes Devices?
- **Symptom:** A friend purchases a new iPhone or receives a warranty replacement. The new iPhone has a different hardware UDID.
- **System Behavior:** When the friend attempts to install the game or launcher from the website, iOS downloads the manifest, starts the download, but fails during installation verification with:
  *"Unable to Install '<App>' ... The developer has not included this device in the provisioning profile."*
- **Required Resolution Workflow:**
  1. Friend visits `https://ros-sothat.example.com/enroll` to submit the new UDID.
  2. Server backend (or admin) registers the new UDID in Apple Developer Portal.
  3. The provisioning profile is regenerated in Apple Developer Portal (now including 21 devices).
  4. Both application IPAs are re-signed with the updated provisioning profile.
  5. The updated IPAs are placed in the website downloads directory.
  6. Friend taps "Install" again; installation completes successfully.
  7. *Note:* Existing friends on previously registered devices are unaffected and do not need to re-download.

#### 6.2 What Happens When the Provisioning Profile Expires?
- **Lifespan:** Apple enforces a strict **maximum validity of 1 year (365 days)** on all Ad Hoc provisioning profiles.
- **Symptom:** Exactly 1 year after the profile was generated, iOS Mobile File Integrity (AMFI) marks the profile expired.
- **User Experience:** When the player taps the app icon on their home screen, the app displays a white splash screen for 0.1 seconds and **immediately crashes back to the home screen**. The OS crash log records `SIGKILL (COORDINATOR: PROVISIONING_PROFILE_EXPIRED)`.
- **Required Resolution Workflow:**
  1. The server owner renews the Apple Developer membership ($99/year).
  2. Regenerate the Ad Hoc provisioning profiles for both apps.
  3. Re-sign the IPAs with the fresh profiles.
  4. Push the new IPAs to the HTTPS server.
  5. Players visit the private website and tap "Update"; the existing app is upgraded in place without losing local settings or documents.

---

### 7. Official Apple Documentation Citations

1. **Distributing your app to registered devices:**  
   https://developer.apple.com/documentation/xcode/distributing-your-app-to-registered-devices
2. **Apple Developer Account Devices Overview:**  
   https://developer.apple.com/help/account/devices/devices-overview
3. **Create an Ad Hoc provisioning profile:**  
   https://developer.apple.com/help/account/provisioning-profiles/create-an-ad-hoc-provisioning-profile/
4. **Apple Developer Program Enrollment:**  
   https://developer.apple.com/help/account/membership/program-enrollment
5. **OTA Configuration Profile Service:**  
   https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/iPhoneOTAConfiguration/Introduction/Introduction.html
