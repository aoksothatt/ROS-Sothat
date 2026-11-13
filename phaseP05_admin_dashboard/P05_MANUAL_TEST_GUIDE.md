# ROS Sothat — Phase P05: Secure Admin Dashboard
## Local Manual Verification & Operator Guide

**Target Environment:** Local Development Only (`127.0.0.1`)  
**Backend:** `http://127.0.0.1:8000`  
**Frontend Website:** `http://127.0.0.1:5173`  
**Date:** 2026-11-13  

---

## 1. Local Environment Startup

### Step 1: Start Backend Server
In a terminal window:
```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
*Expected log:*
```text
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### Step 2: Start Frontend Website
In a second terminal window:
```powershell
cd D:\ROS-Legacy-Analysis\ros-website
npm.cmd run dev -- --host 127.0.0.1
```
*Expected log:*
```text
VITE v5.4.9 ready in 350 ms
➜  Local:   http://127.0.0.1:5173/
```

---

## 2. Bootstrapping an Administrator Account

To access the admin portal, promote a registered account to `admin` using the CLI bootstrap utility:

1. Register an account on the website (e.g. `admin_commander`) via email OTP at `http://127.0.0.1:5173/register`.
2. In terminal:
```powershell
cd D:\ROS-Legacy-Analysis\ros-private-server
python -m app.cli.admin promote admin_commander -y
```
3. Output confirms:
```text
[SUCCESS] Account 'admin_commander' (ID: 1) successfully promoted to 'admin'.
```

---

## 3. Step-by-Step Verification Procedures

### Procedure 1: Admin Authentication & Portal Access
1. Open browser to `http://127.0.0.1:5173/login`.
2. Authenticate using `admin_commander` with email OTP.
3. Observe the top navigation bar: A gold **Admin Portal** button is now visible between Home and Dashboard.
4. Click **Admin Portal** or navigate directly to `http://127.0.0.1:5173/admin`.
5. Observe the Administrative Overview:
   * Total registered accounts, active accounts, and suspended counts match the database.
   * Total player characters and total diamonds in player balances are displayed.
   * Server status indicators show loopback binding (`127.0.0.1`).
   * Recent administrative audit log feed displays recent actions.

### Procedure 2: Player Isolation & Access Boundary Check
1. Open an incognito/private browser window.
2. Register a second account as a regular player (e.g. `regular_soldier`).
3. Observe the top navbar: The **Admin Portal** button is **NOT** visible.
4. Attempt to navigate directly to `http://127.0.0.1:5173/admin`.
5. Observe frontend route guard: The player is immediately redirected back to `/dashboard`.
6. Open browser DevTools console and execute a raw fetch to `/api/v1/admin/dashboard/summary` using the player's token:
   * Backend returns `403 Forbidden` (`{"detail": "Admin privileges required."}`).

### Procedure 3: Player Management & Moderation
1. In the admin session, click **Players & Accounts** in the sidebar (`/admin/players`).
2. In the search input, type `regular_soldier`. Observe the table dynamically filters to this player.
3. Click the red **Suspend** button next to `regular_soldier`.
4. Enter reason: `Test suspension for verification` and confirm.
5. In the player's incognito window, attempt to click any player dashboard link or refresh.
   * The player's token is rejected with `403 Forbidden` (`{"detail": "Account is banned."}`).
6. In the admin session, click **Reactivate** and confirm with reason `Verification completed`.
7. Refresh the player's incognito window: Access to the player dashboard is immediately restored.

### Procedure 4: Atomic Diamond Grant & Deduction
1. In the admin directory (`/admin/players`), click **Inspect** on any player with a character.
2. In the **Diamond Management** tab:
   * Observe current diamond balance (e.g. `100`).
   * Enter Grant amount `500` with reason `Bug report reward`.
   * Observe the live balance calculation preview: `100 ➔ +500 ➔ 600`.
   * Click **Confirm & Grant Diamonds**.
3. Observe:
   * Success alert appears: `Successfully granted 500 diamonds.`
   * Current balance immediately refreshes to `600`.
4. Switch to **Deduct Diamonds**:
   * Enter Deduct amount `200` with reason `Fee adjustment`.
   * Observe live preview: `600 ➔ -200 ➔ 400`.
   * Confirm deduction: Balance updates to `400`.
5. Switch to the **Diamond Ledger History** tab:
   * Both the Grant and Deduct transactions appear in chronological order with balance before and after details.
6. Attempt an overdraft: Enter Deduct amount `99999`.
   * Confirm error alert: `Insufficient diamond balance: current balance is 400, requested deduction is 99999.`

### Procedure 5: Inventory Item Grant & Equipped Clothing Safeguard
1. In the player inspector, click the **Player Inventory** tab.
2. Select an active catalog clothing item (e.g. `Dragon Parachute`).
3. Set Quantity `1` and enter reason `Event distribution`, then click **Grant Item to Player**.
4. Observe the item appears in the Current Player Inventory Slots table.
5. Click **Remove Item**, enter reason `Revocation test`, and confirm.
6. If the item was equipped, observe that the character appearance loadout is safely cleansed with zero broken references.

### Procedure 6: Audit Log Inspection
1. Click **Audit Logs** in the admin sidebar (`/admin/audit-logs`).
2. Observe all operations performed during the test session:
   * Account suspension and reactivation events.
   * Diamond grants and deductions.
   * Item grants and removals.
3. Click filter pills (e.g. `Diamond Grants`, `Suspensions`) to verify instant filtering.
4. Observe that each entry displays the exact administrator actor, target entity, reason, and structured metadata.

---

## 4. Verification Sign-Off Checklist

- [x] Backend runs strictly on `127.0.0.1:8000`.
- [x] Frontend runs strictly on `127.0.0.1:5173`.
- [x] Non-admin players cannot access `/admin` or admin APIs.
- [x] Admin self-suspension is blocked.
- [x] Diamond balance updates are atomic and overdraft-proof.
- [x] Audit logs record all actions accurately.
- [x] Zero changes made to production databases or game binaries.
