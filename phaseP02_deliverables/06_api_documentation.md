# ROS Sothat — API Documentation (Phase P02)
**Document ID:** `06_api_documentation.md`  
**System:** ROS Sothat Private Server Platform  
**Prefix:** `/api/v1/account`  
**Date:** November 2026  
**Status:** IMPLEMENTED & AUDITED  

---

## 1. Overview

Phase P02 extends the ROS Sothat backend API with two dedicated email OTP endpoints:
1. `POST /api/v1/account/otp/request` — Generates and delivers a 6-digit verification code.
2. `POST /api/v1/account/otp/verify` — Validates the code, authenticates or registers the account, and issues a Bearer JWT.

All existing username/password and guest endpoints remain fully operational.

---

## 2. Endpoint Specifications

### 2.1 Request OTP Code
- **Method:** `POST`
- **Path:** `/api/v1/account/otp/request`
- **Authentication:** None (Public)
- **Rate Limit:** 5 requests per 60 seconds per IP; 60-second cooldown per email.

#### Request Headers
| Header | Value | Required |
| :--- | :--- | :--- |
| `Content-Type` | `application/json` | Yes |

#### Request Body
```json
{
  "email": "player_one@example.com",
  "purpose": "registration"
}
```

| Field | Type | Required | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `email` | string | Yes | 5–128 chars, valid email format | Target email address |
| `purpose` | string | Yes | `"registration"` or `"login"` | Purpose of the verification code |

#### Response: HTTP 200 OK
```json
{
  "status": "ok",
  "message": "If this email is valid, a verification code has been sent.",
  "cooldown_seconds": 60,
  "masked_email": "p***e@example.com"
}
```

#### Error Responses
- **HTTP 403 Forbidden:** The requested account is banned.
  ```json
  {"detail": "Account is banned. Reason: Cheating violation"}
  ```
- **HTTP 422 Unprocessable Entity:** Malformed email syntax or unsupported purpose.
- **HTTP 429 Too Many Requests:** Resend cooldown active or IP rate limit reached.
  - Header: `Retry-After: 48`
  ```json
  {"detail": "Please wait 48s before requesting a new verification code."}
  ```

---

### 2.2 Verify OTP Code & Authenticate
- **Method:** `POST`
- **Path:** `/api/v1/account/otp/verify`
- **Authentication:** None (Public)
- **Rate Limit:** 10 requests per 60 seconds per IP; maximum 5 attempts per issued code.

#### Request Body
```json
{
  "email": "player_one@example.com",
  "code": "481920",
  "purpose": "registration",
  "username": "sniper_elite"
}
```

| Field | Type | Required | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `email` | string | Yes | 5–128 chars, valid email format | Recipient email address |
| `code` | string | Yes | Exactly 6 numeric digits (`^[0-9]{6}$`) | Received verification code |
| `purpose` | string | Yes | `"registration"` or `"login"` | Verification purpose |
| `username` | string | No | 3–32 chars, `^[a-zA-Z0-9_-]+$` | Optional custom username on registration |

#### Response: HTTP 200 OK
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOjEwNCwidXNlcm5hbWUiOiJzbmlwZXJfZWxpdGUiLCJyb2xlIjoicGxheWVyIiwiZXhwIjoxNzMxNjg2NDAwfQ.xxxx",
  "token_type": "bearer",
  "account_id": 104,
  "username": "sniper_elite"
}
```

#### Error Responses
- **HTTP 400 Bad Request:**
  - Invalid code (reports remaining attempts):
    ```json
    {"detail": "Invalid verification code. 4 attempt(s) remaining."}
    ```
  - Lockout reached:
    ```json
    {"detail": "Verification code has been invalidated due to too many failed attempts."}
    ```
  - Code expired or already used:
    ```json
    {"detail": "Invalid, expired, or previously used verification code."}
    ```
- **HTTP 403 Forbidden:** Account is banned.
- **HTTP 404 Not Found:** `purpose="login"` but no account exists with this email.
- **HTTP 409 Conflict:**
  - `purpose="registration"` but email is already registered.
  - Specified custom `username` is already taken.
- **HTTP 422 Unprocessable Entity:** Non-numeric or wrong-length OTP code.

---

### 2.3 Get Current Account Profile (Updated)
- **Method:** `GET`
- **Path:** `/api/v1/account/me`
- **Authentication:** `Bearer <token>`

#### Response: HTTP 200 OK
```json
{
  "id": 104,
  "username": "sniper_elite",
  "email": "player_one@example.com",
  "role": "player",
  "is_banned": false,
  "created_at": "2026-11-13T13:25:00.000000",
  "last_login": "2026-11-13T13:25:00.000000",
  "has_character": false
}
```

---

## 3. Preserved Authentication Endpoints

| Method | Path | Request Body | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/account/register` | `{"username": "...", "password": "..."}` | Traditional admin/player password registration |
| `POST` | `/api/v1/account/login` | `{"username": "...", "password": "..."}` | Password authentication (returns Bearer token) |
| `POST` | `/api/v1/account/guest` | `{"device_id": "optional-uuid"}` | Fast guest device login |
