# Phase P03 — API Integration Specification

**Document:** `03_api_integration.md`  
**Phase:** P03 (Website Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Frontend-Backend API Communication & Contract Mapping  
**Security Level:** Read-Only Analysis / Local Isolated Implementation  

---

## 1. Executive Summary

This document specifies the exact API integration between the ROS Sothat frontend web application (`ros-website`) and the FastAPI backend service (`ros-private-server`). The integration adheres strictly to the existing backend endpoints established in Phases P02 and P02.1 without requiring breaking changes, additional schema overhead, or modifications to core database tables.

The communication protocol operates exclusively over HTTP/REST using JSON payloads and standard `Bearer` authentication tokens in compliance with RFC 6750.

---

## 2. Environment Configuration & Base URLs

### 2.1 Configuration Variable
The frontend relies on Vite's environment variable mechanism to resolve the backend API base path:

```env
# ros-website/.env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### 2.2 Client-Side Fallback & Dev Proxy
In `ros-website/src/services/api.ts`, the base URL is loaded dynamically:
```typescript
const BASE_URL: string = import.meta.env.VITE_API_BASE_URL || '/api/v1';
```

When running in local development mode via Vite's dev server (`http://127.0.0.1:5173`), `vite.config.ts` provides an automatic proxy configuration that forwards all requests matching `/api` directly to `http://127.0.0.1:8000`:
```typescript
server: {
  host: '127.0.0.1',
  port: 5173,
  strictPort: true,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
      secure: false
    }
  }
}
```
This dual configuration allows both relative path fetching (`/api/v1/...`) via dev proxy and explicit direct cross-origin fetching (`http://127.0.0.1:8000/api/v1/...`) with CORS headers.

---

## 3. Detailed Endpoint Contracts

### 3.1 Request OTP Challenge
Requests a 6-digit one-time password sent to the specified email address for either account registration or passwordless login.

- **Method:** `POST`
- **Route:** `/api/v1/account/otp/request`
- **Auth Required:** No (Public endpoint)
- **Frontend Caller:** `src/services/auth.ts -> requestOTP(email, purpose)`

#### Request Headers:
```http
Content-Type: application/json
Accept: application/json
```

#### Request Body (`OTPRequestSchema`):
```json
{
  "email": "friend@example.com",
  "purpose": "register"
}
```
*Note: `purpose` must be either `"register"` or `"login"`.*

#### Success Response (HTTP 200 OK):
```json
{
  "status": "sent",
  "email": "friend@example.com",
  "cooldown_seconds": 60,
  "expires_in_seconds": 300
}
```

#### Error Responses:
| HTTP Status | Detail / Reason | Client Handling |
| :--- | :--- | :--- |
| **400 Bad Request** | `"Email is already registered"` (on purpose=`register`) or `"Email not found"` (on purpose=`login`) | Display warning alert; provide navigation link to opposite tab. |
| **422 Unprocessable Entity** | Invalid email format (Pydantic `EmailStr` validation failed) | Display field validation error under email input. |
| **429 Too Many Requests** | Active OTP cooldown in progress (e.g. 60-second flood protection) | Parse `Retry-After` header or response detail; trigger frontend countdown timer. |

---

### 3.2 Verify OTP & Issue Token
Submits the 6-digit OTP code against the active challenge. For new registrations, an optional player `nickname` can be supplied. Upon verification, the backend issues an access token.

- **Method:** `POST`
- **Route:** `/api/v1/account/otp/verify`
- **Auth Required:** No (Public endpoint)
- **Frontend Caller:** `src/services/auth.ts -> verifyOTP(data)`

#### Request Headers:
```http
Content-Type: application/json
Accept: application/json
```

#### Request Body (`OTPVerifySchema`):
```json
{
  "email": "friend@example.com",
  "otp": "492815",
  "purpose": "register",
  "nickname": "DeltaOne"
}
```

#### Success Response (HTTP 200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "usr_9f4c3a2b1e",
  "email": "friend@example.com",
  "nickname": "DeltaOne",
  "role": "player"
}
```

#### Error Responses:
| HTTP Status | Detail / Reason | Client Handling |
| :--- | :--- | :--- |
| **400 Bad Request** | `"Invalid OTP code. 4 attempts remaining."` | Clear OTP input, refocus first box, display remaining attempt count. |
| **400 Bad Request** | `"OTP challenge expired"` | Prompt user to request a fresh OTP code. |
| **422 Unprocessable Entity** | OTP is not 6 numeric digits | Prevent submission via client input validation; show format warning. |
| **429 Too Many Requests** | `"Challenge locked: Maximum attempts exceeded"` | Lock form, inform user challenge is destroyed, require requesting new OTP. |

---

### 3.3 Get Authenticated Profile
Retrieves the full operator profile for the currently authenticated session, including role privileges, account status, and diamond ledger balance.

- **Method:** `GET`
- **Route:** `/api/v1/account/me`
- **Auth Required:** Yes (`Bearer <token>`)
- **Frontend Caller:** `src/services/auth.ts -> getProfile()`

#### Request Headers:
```http
Accept: application/json
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Success Response (HTTP 200 OK):
```json
{
  "id": "usr_9f4c3a2b1e",
  "email": "friend@example.com",
  "username": null,
  "nickname": "DeltaOne",
  "role": "player",
  "is_active": true,
  "created_at": "2026-11-13T12:00:00Z",
  "diamond_balance": 1000
}
```

#### Error Responses:
| HTTP Status | Detail / Reason | Client Handling |
| :--- | :--- | :--- |
| **401 Unauthorized** | `"Could not validate credentials"` or expired token | Purge `authStore`, clear `sessionStorage`, redirect to `/login?redirect=...`. |
| **403 Forbidden** | Account inactive or suspended | Display security suspension banner. |

---

### 3.4 Admin Password Fallback Login
Provides administrative access for platform maintainers using legacy username/password credentials.

- **Method:** `POST`
- **Route:** `/api/v1/account/login`
- **Auth Required:** No (Public endpoint)
- **Frontend Caller:** `src/services/auth.ts -> adminPasswordLogin(username, password)`

#### Request Headers:
```http
Content-Type: application/json
Accept: application/json
```

#### Request Body (`AccountLoginSchema`):
```json
{
  "username": "admin",
  "password": "SecureAdminPassword123!"
}
```

#### Success Response (HTTP 200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "usr_admin_01",
  "role": "admin"
}
```

---

## 4. Client-Side HTTP Abstraction Layer

The HTTP layer is implemented in [src/services/api.ts](file:///D:/ROS-Legacy-Analysis/ros-website/src/services/api.ts) using native `fetch` wrapped in a typed utility function.

### 4.1 Custom `ApiError` Class
The application wraps failed responses in a structured `ApiError` instance:
```typescript
export class ApiError extends Error {
  public status: number;
  public detail: string;
  public retryAfter?: number;

  constructor(status: number, detail: string, retryAfter?: number) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.retryAfter = retryAfter;
  }
}
```

### 4.2 Error Handling & `Retry-After` Header Extraction
When encountering rate limiting (HTTP 429), the client extracts the `Retry-After` response header:
```typescript
let retryAfter: number | undefined;
const retryHeader = res.headers.get('Retry-After');
if (retryHeader) {
  const parsed = parseInt(retryHeader, 10);
  if (!isNaN(parsed)) retryAfter = parsed;
}
```
If an HTTP 401 error is detected during an authenticated request, the client broadcasts a session expiration and forces a clean redirect to `/login`.

---

## 5. CORS Verification & Preflight Handling

The backend FastAPI application defines CORS middleware in `app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Verification Test:
Backend integration test `ros-private-server/tests/test_website_integration.py::test_cors_preflight_for_website` validates that:
1. `OPTIONS` preflight requests sent with `Origin: http://127.0.0.1:5173` receive HTTP 200 OK.
2. `Access-Control-Allow-Origin` contains either `*` or `http://127.0.0.1:5173`.
3. Allowed headers include `Authorization` and `Content-Type`.

All CORS requirements are satisfied for cross-origin browser communication during local testing.
