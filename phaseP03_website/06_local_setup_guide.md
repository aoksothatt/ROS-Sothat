# Phase P03 — Local Setup & Execution Guide

**Document:** `06_local_setup_guide.md`  
**Phase:** P03 (Website Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Developer Walkthrough for Running and Testing the Platform Locally  
**Security Level:** Read-Only Analysis / Local Isolated Implementation  

---

## 1. System Requirements & Prerequisites

To run the ROS Sothat backend and website locally, ensure the following are installed:
- **Operating System:** Windows 10/11 (or Linux/macOS)
- **Node.js:** v18.0.0+ (Tested on Node `v22.17.1` with npm `10.9.2`)
- **Python:** v3.10+ (Tested on Python `3.10.11`)
- **Shell:** Windows PowerShell

> [!IMPORTANT]
> **Windows PowerShell Script Execution Policy:**  
> On systems where PowerShell script execution is restricted (`Restricted` execution policy), standard `npm` and `npx` commands may fail on `.ps1` wrapper files. Always invoke `npm.cmd` and `npx.cmd` directly in PowerShell.

---

## 2. Setting Up the Backend Service (`ros-private-server`)

### Step 2.1 — Navigate and Activate Virtual Environment
Open a PowerShell terminal window:
```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2.2 — Install Python Dependencies
```powershell
pip install -r requirements.txt
```

### Step 2.3 — Configure Local Environment Variables
Create or verify `.env` inside `D:\ROS-Legacy-Analysis\ros-private-server\.env`:
```ini
# Core Configuration
DATABASE_URL=sqlite:///./ros_dev.db
SECRET_KEY=ros_sothat_dev_super_secret_jwt_key_2026_test
OTP_HMAC_SECRET=ros_sothat_dev_hmac_secret_key_32bytes_min

# Email Configuration (Console Provider for Local Testing)
EMAIL_PROVIDER=console
SMTP_HOST=127.0.0.1
SMTP_PORT=25
```

### Step 2.4 — Initialize Database Tables
For local development, initialize SQLite tables using the migration scripts or Alembic:
```powershell
alembic upgrade head
```

### Step 2.5 — Start the Backend Server
Launch the FastAPI server bound exclusively to loopback:
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API is now listening at: `http://127.0.0.1:8000`  
Interactive Swagger docs: `http://127.0.0.1:8000/docs`

---

## 3. Setting Up the Website Frontend (`ros-website`)

### Step 3.1 — Navigate and Install Dependencies
Open a **second** PowerShell terminal window:
```powershell
cd D:\ROS-Legacy-Analysis\ros-website
npm.cmd install
```

### Step 3.2 — Configure Frontend Environment Variables
Verify that `ros-website/.env` specifies the backend API endpoint:
```ini
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### Step 3.3 — Start the Vite Development Server
```powershell
npm.cmd run dev
```
The website will boot instantly and display:
```text
  VITE v5.4.9  ready in 410 ms

  ➜  Local:   http://127.0.0.1:5173/
  ➜  Network: use --host to expose
```

---

## 4. End-to-End Walkthrough: Registering and Logging In

1. Open your browser and navigate to:
   [http://127.0.0.1:5173](http://127.0.0.1:5173)
2. Tap **"Operator Registration"** or click **"Join Sothat"** in the top navigation bar to go to `/register`.
3. Enter your test email address (e.g. `test_pilot@example.com`).
4. Click **"Request Verification Code"**.
5. Switch to the **Backend Terminal window** where Uvicorn is running. Observe the mock email console output:
   ```text
   INFO: [CONSOLE EMAIL] To: test_pilot@example.com | Subject: Your ROS Sothat Verification Code | Code: 839201
   ```
6. Return to the browser. The OTP input fields will be focused.
7. Type or paste the 6-digit code (`839201`).
8. Enter a player callsign/nickname (e.g. `ViperSquadron`).
9. Click **"Verify & Complete Registration"**.
10. The browser immediately transitions to [http://127.0.0.1:5173/dashboard](http://127.0.0.1:5173/dashboard):
    - Operator Nickname: `ViperSquadron`
    - Email: `test_pilot@example.com`
    - Role: `player`
    - Diamond Ledger Balance: `1000 Diamonds` (starter package)
    - Identity Status: `ACTIVE`
11. Click **"Log Out"** in the top navbar. You will be cleanly redirected back to the Home page, and session storage will be purged.

---

## 5. Running Automated Verification Suites

### 5.1 Run Frontend Unit Tests (Vitest)
```powershell
cd D:\ROS-Legacy-Analysis\ros-website
npm.cmd test
```
*Expected: 18 tests passing across 4 files.*

### 5.2 Build Frontend for Production
```powershell
cd D:\ROS-Legacy-Analysis\ros-website
npm.cmd run build
```
*Expected: Clean bundle generated in `ros-website/dist/` without errors.*

### 5.3 Run Backend Website Integration Tests
```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server
python -m pytest tests/test_website_integration.py -v
```
*Expected: 5 tests passing (registration, login, bad token, admin fallback, CORS).*

### 5.4 Run Full Backend Regression Suite
```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server
python -m pytest -v
```
*Expected: 159 tests passing, 1 skipped.*
