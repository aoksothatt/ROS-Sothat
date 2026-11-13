# Phase P04 — Local Setup & Execution Guide

**Document:** `09_local_setup_guide.md`  
**Phase:** P04 (Player Dashboard Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Developer Manual for Local Execution, Dashboard Walkthrough & Verification  
**Security Level:** Read-Only Analysis & Isolated Development  

---

## 1. System Requirements & Environment

- **Operating System:** Windows 10/11 (or Linux/macOS)
- **Node.js:** v18.0.0+ (Tested on Node `v22.17.1` with npm `10.9.2`)
- **Python:** v3.10+ (Tested on Python `3.11.9`)
- **Shell:** Windows PowerShell

> [!IMPORTANT]
> **Windows PowerShell Execution Policy:**  
> When running PowerShell on Windows systems with restricted execution policies, standard `npm` and `npx` may be blocked by `.ps1` wrapper policies. Always execute `npm.cmd` and `npx.cmd` directly.

---

## 2. Starting the Backend Service (`ros-private-server`)

Open a PowerShell terminal window:

```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server

# Verify or launch local FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- API Server listening at: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

---

## 3. Starting the Website Frontend (`ros-website`)

Open a **second** PowerShell terminal window:

```powershell
cd D:\ROS-Legacy-Analysis\ros-website

# Launch Vite development server bound to loopback
npm.cmd run dev
```

- Web Application listening at: `http://127.0.0.1:5173`

---

## 4. End-to-End Walkthrough: Exploring the Player Dashboard

1. Open your browser and navigate to:
   [http://127.0.0.1:5173/login](http://127.0.0.1:5173/login)
2. Enter your test player email (e.g. `operator@ros-sothat.internal`) and click **"SEND LOGIN CODE"**.
3. Inspect Terminal 1 (Uvicorn console) for the logged OTP:
   ```text
   INFO: [CONSOLE EMAIL] To: operator@ros-sothat.internal | Subject: Your ROS Sothat Verification Code | Code: 592814
   ```
4. Enter the 6-digit code in the browser and click **"VERIFY & LOG IN"**.
5. The application redirects immediately to **[http://127.0.0.1:5173/dashboard](http://127.0.0.1:5173/dashboard)**:
   - **Tactical Overview:** View operative welcome banner, live authoritative diamond balance (`100 💎`), gold balance, item counter, and account GID.
6. Click **"My Profile"** (`/dashboard/profile`):
   - If no character has been created, fill out the callsign field (e.g. `ViperSniper`) and tap **"INITIALIZE CHARACTER DOSSIER"**.
   - View character level, EXP progress bar, and equipped loadout.
7. Click **"Diamond Wallet"** (`/dashboard/wallet`):
   - Inspect the authoritative diamond vault and view the append-only ledger transaction history.
8. Click **"Inventory"** (`/dashboard/inventory`):
   - Browse personal supply locker items and test category filters (`Weapons & Skins`, `Clothing & Gear`, `Consumables`).
9. Click **"Statistics"** (`/dashboard/statistics`):
   - Inspect verified match telemetry and read the honest match-server development status notice.
10. Click **"Settings"** (`/dashboard/settings`):
    - Inspect account metadata and session posture.
    - Click **"Logout Active Session"** to purge `sessionStorage` and return to the login screen.

---

## 5. Running Automated Verification Suites

### 5.1 Run Frontend Unit Tests (34 Tests)
```powershell
cd D:\ROS-Legacy-Analysis\ros-website
npx.cmd vitest run tests/unit
```
*Expected: 5 files passed, 34 tests passed, 0 failed.*

### 5.2 Run Browser Viewport Tests (19 Tests)
```powershell
cd D:\ROS-Legacy-Analysis\ros-website
npx.cmd vitest run tests/browser
```
*Expected: 1 file passed, 19 tests passed, 0 failed.*

### 5.3 Run Frontend Production Build
```powershell
cd D:\ROS-Legacy-Analysis\ros-website
npm.cmd run build
```
*Expected: Built in ~1.5s with 0 errors.*

### 5.4 Run Backend Dashboard API & Integration Tests
```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server
python -m pytest tests/test_player_dashboard_api.py tests/test_website_integration.py -v
```
*Expected: 8 passed in ~1s.*

### 5.5 Run Full Backend Regression Suite (163 Tests)
```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server
python -m pytest -v
```
*Expected: 162 passed, 1 skipped, 0 failed in ~28s.*
