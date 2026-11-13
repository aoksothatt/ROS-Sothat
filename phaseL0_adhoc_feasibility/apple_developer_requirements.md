# ROS Sothat — Phase L0 Deliverable 4
## Apple Developer Program Requirements & Cost Breakdown

**Phase:** Phase L0 (Ad Hoc Distribution Feasibility Research)  
**Target Directory:** `D:\ROS-Legacy-Analysis\phaseL0_adhoc_feasibility\`  
**Date:** 2026-11-13  
**Status:** COMPLETE — SPECIFICATION REPORT  

---

### 1. Executive Summary

This report defines the exact Apple Developer Program credentials, identity assets, provisioning profiles, and financial expenditures required to support Ad Hoc distribution of the ROS Sothat Launcher and Rules of Survival Legacy game to 10–20 invited friends.

Apple Ad Hoc distribution is an officially supported developer feature explicitly designed to enable deployment of pre-release software to up to 100 registered devices per device family. For a private group of 10–20 friends, this approach operates 100% within Apple's published guidelines.

---

### 2. Apple Developer Account Specifications (Question 11)

#### 2.1 Membership Tier
- **Program:** Apple Developer Program (Annual Membership)
- **Account Type:** **Individual** (or Organization)
  - *Individual:* Registered under a single person's legal name. Requires a personal Apple ID with Two-Factor Authentication enabled. Fast approval (typically 24–48 hours).
  - *Organization:* Requires a legal entity and a D-U-N-S Number (Dun & Bradstreet). Not necessary for a private group of friends.
- **Official Enrollment Portal:** https://developer.apple.com/help/account/membership/program-enrollment

#### 2.2 Certificates
To sign iOS applications for Ad Hoc distribution, the following certificate must be issued:
- **Certificate Type:** **Apple Distribution Certificate** (or legacy *iOS Distribution*)
- **Purpose:** Cryptographically signs iOS application bundles for Ad Hoc deployment or App Store submission.
- **Validity:** 1 year from issuance.
- **Generation:** Created in Apple Developer Portal using a Certificate Signing Request (CSR) generated from macOS Keychain Access or via `openssl req -new -newkey rsa:2048 -nodes -keyout distribution.key -out distribution.csr`.

#### 2.3 App Identifiers (App IDs)
Two App IDs are required in *Certificates, Identifiers & Profiles*:
1. **Launcher App ID:**
   - Name: `ROS Sothat Launcher`
   - Identifier: `net.rossothat.launcher` (Explicit App ID)
   - Capabilities: Standard defaults.
2. **Game App ID:**
   - Name: `RoS Legacy Game`
   - Identifier: `net.roslegacy.ios` (Explicit App ID matching original game `CFBundleIdentifier`)
   - Capabilities: Standard defaults.

#### 2.4 Provisioning Profiles
Two **Ad Hoc Provisioning Profiles** (`embedded.mobileprovision`) must be created:
1. `ROS_Sothat_Launcher_AdHoc`:
   - App ID: `net.rossothat.launcher`
   - Certificate: Active Apple Distribution Certificate
   - Devices: Selected list of 10–20 registered friend UDIDs
2. `ROS_Legacy_Game_AdHoc`:
   - App ID: `net.roslegacy.ios`
   - Certificate: Active Apple Distribution Certificate
   - Devices: Exact same list of 10–20 registered friend UDIDs

---

### 3. Detailed Cost Analysis (Infrastructure & Developer Account)

All financial costs are clearly categorized below:

```
+-----------------------------------------------------------------------------------------------+
|                                    ESTIMATED COST BREAKDOWN                                   |
+---------------------------+-----------------------+---------------+---------------------------+
| Expense Item              | Necessity Level       | Cost (USD)    | Billing Frequency / Notes |
+---------------------------+-----------------------+---------------+---------------------------+
| Apple Developer Program   | **MANDATORY**         | $99.00        | Annual recurring          |
| Membership                |                       |               | (Official Apple fee)      |
+---------------------------+-----------------------+---------------+---------------------------+
| Custom Domain Name        | **MANDATORY**         | ~$10.00–12.00 | Annual recurring          |
| (e.g. ros-sothat.net)     | (Required for HTTPS)  |               | (Namecheap / Cloudflare)  |
+---------------------------+-----------------------+---------------+---------------------------+
| Public TLS/SSL            | **MANDATORY**         | $0.00         | FREE via Let's Encrypt or |
| Certificate               | (Required by iOS OTA) |               | Cloudflare Universal SSL  |
+---------------------------+-----------------------+---------------+---------------------------+
| Web Hosting & Backend     | OPTIONAL              | $0.00         | FREE if hosted on existing|
| Server Infrastructure     |                       |               | Windows PC via Cloudflare |
|                           |                       |               | Tunnel (Zero public ports)|
|                           |                       | (~$5.00/mo)   | (Optional $60/yr if VPS)  |
+---------------------------+-----------------------+---------------+---------------------------+
| Transactional Email OTP   | OPTIONAL / LOW        | $0.00         | FREE tier via Resend or   |
| (Email Verification)      |                       |               | SendGrid (100 emails/day) |
+---------------------------+-----------------------+---------------+---------------------------+
| macOS Build / Signing     | OPTIONAL              | $0.00         | FREE if user owns a Mac;  |
| Environment               |                       |               | or FREE via GitHub Actions|
|                           |                       |               | macOS runners (CI/CD)     |
+---------------------------+-----------------------+---------------+---------------------------+
| **TOTAL INITIAL OUTLAY**  | **MINIMUM REQUIRED**  | **~$110.00**  | **FIRST YEAR TOTAL**      |
+---------------------------+-----------------------+---------------+---------------------------+
```

---

### 4. Risk & Compliance Matrix

```
+-----------------------------------------------------------------------------------------------+
|                                     RISK EVALUATION MATRIX                                    |
+---------------------------+----------+--------------------------------------------------------+
| Risk Factor               | Severity | Mitigation Strategy                                    |
+---------------------------+----------+--------------------------------------------------------+
| Account Termination       | VERY LOW | Ad Hoc distribution for 10–20 devices is an officially |
| (Developer TOS Violation) |          | sanctioned Apple workflow. Distribution is private and |
|                           |          | invite-only; well under the 100-device quota.          |
+---------------------------+----------+--------------------------------------------------------+
| Profile Expiration        | MEDIUM   | Apple Ad Hoc profiles expire after 365 days. Admin must|
| (1-Year Hard Stop)        |          | schedule annual re-signing and OTA update handoff.     |
+---------------------------+----------+--------------------------------------------------------+
| Device Limit Exhaustion   | VERY LOW | Group size is 10–20 friends. Even with device upgrades,|
| (100 Devices Maximum)     |          | total devices will not exceed 25–30 within a year.     |
+---------------------------+----------+--------------------------------------------------------+
| Certificate Revocation    | LOW      | Store private keys securely; never commit signing keys |
|                           |          | or `.p12` certificates to public git repositories.     |
+---------------------------+----------+--------------------------------------------------------+
```

---

### 5. Summary Conclusion

Ad Hoc distribution for 10–20 friends requires:
1. One $99/year Apple Developer account.
2. One custom domain name (~$10–12/year).
3. Zero additional paid infrastructure (Windows host + Cloudflare Tunnel + Let's Encrypt + GitHub Actions CI).
Total out-of-pocket commitment: **~$110 USD / year**.
