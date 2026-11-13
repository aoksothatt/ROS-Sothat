# ROS Sothat — Phase P03: Pre-Implementation Website Audit
**Document ID:** `00_pre_implementation_audit.md`  
**System:** ROS Sothat Private Server Platform  
**Target:** Website Frontend Implementation (`ros-website`)  
**Date:** November 2026  
**Status:** AUDIT COMPLETE — APPROVED FOR IMPLEMENTATION  

---

## 1. Executive Summary

This pre-implementation audit inspects the workspace, backend API contracts, security configurations, and tooling environment prior to writing code for the ROS Sothat player website. 

The primary objective of Phase P03 is to design, construct, integrate, and verify a complete, responsive, dark tactical multiplayer gaming website for 10–20 invited friends, supporting passwordless registration, OTP verification, login, protected dashboard viewing, and secure session management.

All baseline protection rules were audited and verified before commencing development:
- **`RoS-Legacy-iOS.ipa` SHA-256:** `D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55` (Match verified)
- **`Payload/client.app/client` SHA-256:** `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6` (Match verified)
- **Production Database:** Preserved untouched. Tests use in-memory SQLite (`StaticPool`).
- **Network Boundaries:** Local loopback bindings (`127.0.0.1`) only. No public exposure or external email transmission.

---

## 2. Tooling & Environment Verification

| Tool / Runtime | Detected Version | Operational Verification |
| :--- | :--- | :--- |
| **Node.js** | `v22.17.1` | 64-bit runtime installed at `C:\Program Files\nodejs\node.exe` |
| **npm** | `10.9.2` | Executable via `npm.cmd` (PowerShell `.ps1` restriction bypassed) |
| **Python** | `3.11.9` | Asynchronous FastAPI / SQLAlchemy / pytest test runner |
| **Web Framework** | FastAPI `0.162.2` | ASGI server running on `http://127.0.0.1:8000` |
| **CORS Policy** | Wildcard Origins | `allow_origins=["*"]`, `allow_credentials=False`, `allow_headers=["*"]` |

---

## 3. Verified Backend API Contracts

A direct source inspection was conducted on `app/account/router.py`, `app/account/service.py`, and `app/account/schemas.py`.

### 3.1 Request Verification Code (`POST /api/v1/account/otp/request`)
- **Request Body:**
  ```json
  {
    "email": "player@example.com",
    "purpose": "registration" | "login"
  }
  ```
- **Validation Rules:**
  - `email`: 5–128 characters, valid email regex pattern (`^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$`).
  - `purpose`: Literal `"registration"` or `"login"`.
- **Response (`200 OK`):**
  ```json
  {
    "status": "ok",
    "message": "If this email is valid, a verification code has been sent.",
    "cooldown_seconds": 60,
    "masked_email": "p***r@example.com"
  }
  ```
- **Status Codes:**
  - `200 OK`: Code issued or generic enumeration response returned.
  - `403 Forbidden`: Account is banned (`detail`: `"Account is banned. Reason: ..."`).
  - `422 Unprocessable Entity`: Malformed email format or purpose.
  - `429 Too Many Requests`: Cooldown active (`detail`: `"Please wait Xs before requesting a new verification code."`, header: `Retry-After`).

### 3.2 Verify Code & Authenticate (`POST /api/v1/account/otp/verify`)
- **Request Body:**
  ```json
  {
    "email": "player@example.com",
    "code": "123456",
    "purpose": "registration" | "login",
    "username": "optional_chosen_username"
  }
  ```
- **Validation Rules:**
  - `code`: Exactly 6 numeric digits (`^[0-9]{6}$`).
  - `username`: Optional, 3–32 chars (`^[a-zA-Z0-9_-]+$`).
- **Response (`200 OK`):**
  ```json
  {
    "access_token": "<compact_jwt_token>",
    "token_type": "bearer",
    "account_id": 104,
    "username": "player_xxxx"
  }
  ```
- **Status Codes:**
  - `200 OK`: Valid verification; returns Bearer JWT.
  - `400 Bad Request`: Invalid code, attempts remaining, expired code, already consumed code, or legacy format upgraded.
  - `404 Not Found`: Login attempted on non-existent account.
  - `409 Conflict`: Registration attempted with existing email or taken username.
  - `403 Forbidden`: Banned account.
  - `422 Unprocessable Entity`: Code not 6 digits or non-numeric.

### 3.3 Get Current Profile (`GET /api/v1/account/me`)
- **Header:** `Authorization: Bearer <access_token>`
- **Response (`200 OK`):**
  ```json
  {
    "id": 104,
    "username": "player_xxxx",
    "email": "player@example.com",
    "role": "player",
    "is_banned": false,
    "created_at": "2026-11-13T13:25:00",
    "last_login": "2026-11-13T13:30:00",
    "has_character": false
  }
  ```
- **Status Codes:**
  - `200 OK`: Active profile returned.
  - `401 Unauthorized`: Missing, expired, or invalid token.
  - `403 Forbidden`: Account is banned.

---

## 4. Frontend Technology Stack & Architecture

- **Project Location:** `D:\ROS-Legacy-Analysis\ros-website` (isolated from binary extraction and protocol research folders).
- **Core Framework:** **Vue 3** (Composition API `<script setup lang="ts">`).
- **Build Tool:** **Vite** (Fast HMR, native ES modules).
- **Language:** **TypeScript** (Strict type safety matching backend Pydantic schemas).
- **Routing:** **Vue Router 4** (HTML5 history mode, navigation guards for protected routes).
- **State Management:** **Pinia** (Centralized reactive auth store).
- **Styling:** Custom scoped CSS with utility variables implementing the dark tactical survival palette (`#080B10`, `#101720`, `#151E29`, `#D7A84B`, `#B94B3C`).
- **Testing:** **Vitest** for fast unit and component tests.

---

## 5. Security & Session Storage Strategy

- **Token Storage:** The JWT access token is stored in memory in the Pinia reactive store for immediate API requests, and mirrored in `sessionStorage` (cleared on browser close/tab close) to allow page refreshes without premature logout.
- **XSS Mitigation:** Tokens are never placed in URL query parameters, never rendered in the DOM, and never passed to `v-html`.
- **Role Verification:** Frontend navigation guards check token presence, but all role authorizations and status checks are derived strictly from the backend via `/api/v1/account/me`.
- **Logout:** Explicitly clears local state, wipes `sessionStorage`, and redirects to `/login`.

---

## 6. Risks & Mitigation Matrix

| Risk | Likelihood | Impact | Mitigation Strategy |
| :--- | :---: | :---: | :--- |
| **PowerShell script execution policy (`npm.ps1`)** | High | Low | Always invoke `npm.cmd` and `npx.cmd` directly in CLI tasks and documentation. |
| **Port Conflicts** | Low | Medium | Backend configured on `127.0.0.1:8000`; Vite configured explicitly on `127.0.0.1:5173`. |
| **Leaking OTP Secrets to Frontend** | Low | Critical | Vite config strictly separates frontend env (`VITE_API_BASE_URL`). No backend secrets (`OTP_SECRET_KEY`, `SECRET_KEY`) are included. |
| **Misleading Game Availability Claims** | Medium | Medium | Clear disclaimers indicating private development status; download section explicitly states game package is in preparation. |
| **Accidental Production DB Overwrite** | Low | Critical | Local frontend talks only to localhost development backend running against SQLite or test fixtures. |

---

## 7. Approval & Next Steps

The audit confirms that the backend is fully prepared and compatible. Implementation begins immediately with Phase P03.1 (Frontend Foundation in `D:\ROS-Legacy-Analysis\ros-website`).
