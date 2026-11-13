# Phase P03.1 — Authentication Security Audit & Token Transmission Analysis

**Document:** `01_authentication_security_audit.md`  
**Phase:** P03.1 (Final Website Verification)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Audit Target:** Frontend Authentication State & Backend Auth Boundary  
**Security Level:** Read-Only Audit & Verified Hardening  

---

## 1. Executive Summary

As part of Phase P03.1, a rigorous line-by-line security audit of the authentication and token transmission mechanisms was conducted across both `ros-website` and `ros-private-server`. 

The findings confirm:
1. **Token Storage:** JWT tokens are maintained in-memory within Pinia (`src/stores/auth.ts`) and mirrored in browser `sessionStorage`.
2. **Token Transmission:** Tokens are transmitted strictly via the HTTP `Authorization: Bearer <token>` header. Tokens are never exposed in URL query parameters, paths, or browser logs.
3. **Session Purging:** Logout, token expiration, or backend verification failure immediately purges the token from both Pinia state and `sessionStorage`.
4. **Storage Vulnerability Posture:** `sessionStorage` is accessible to JavaScript and is inherently vulnerable to Cross-Site Scripting (XSS). It does **not** provide HttpOnly protection.
5. **DOM Injection Defenses:** The entire frontend codebase contains **zero** instances of `v-html` or `innerHTML`. All dynamic user data is safely escaped via Vue 3 template interpolation.
6. **Backend Compatibility:** The backend currently expects RFC 6750 Bearer authentication. Cookie authentication was neither introduced nor simulated, preserving total compatibility with backend services and existing test suites.

---

## 2. In-Depth Component & Service Inspection

### 2.1 Pinia Auth Store (`ros-website/src/stores/auth.ts`)
- **Key Definition:** `STORAGE_KEY = 'ros_sothat_token'`
- **State Initialization:**
  ```typescript
  const token = ref<string | null>(sessionStorage.getItem(STORAGE_KEY));
  const user = ref<AccountProfile | null>(null);
  ```
- **Token Mirroring (`setSession`):**
  ```typescript
  function setSession(newToken: string): void {
    token.value = newToken;
    sessionStorage.setItem(STORAGE_KEY, newToken);
  }
  ```
- **Session Purge (`logout`):**
  ```typescript
  function logout(): void {
    token.value = null;
    user.value = null;
    error.value = null;
    sessionStorage.removeItem(STORAGE_KEY);
  }
  ```
- **Validation on Rehydration (`initSession`):**
  When restoring an existing session on page load or route transition, `initSession()` issues a live verification call to `GET /api/v1/account/me`. If the token has expired, been invalidated, or is malformed, the catch block immediately triggers `logout()`, removing the stale token from `sessionStorage` and returning `false`.

### 2.2 API Fetch Abstraction (`ros-website/src/services/api.ts`)
- **Header Injection:**
  ```typescript
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  ```
- **URL Sanitization:** The token is never appended to URL query parameters or route fragments.
- **Error Propagation & Log Hygiene:**
  - Zero `console.log`, `console.warn`, or `console.error` calls exist within `src/services/api.ts` or any service file.
  - Raw tokens, internal stack traces, and database connection details are never logged to the browser developer console.
  - Connection failures generate a structured `ApiError` with a friendly, sanitized message: `"Unable to connect to ROS Sothat server. Please ensure the local backend is running."`

### 2.3 Vue Router Guards (`ros-website/src/router/index.ts`)
- **Destination Preservation:** When an unauthenticated visitor navigates to a protected route (e.g. `/dashboard`), the router issues a redirect:
  ```typescript
  next({ name: 'login', query: { redirect: to.fullPath } });
  ```
- **Safety Verification:** The redirect query parameter preserves only the intended route path (`/dashboard`). Under no circumstances is a sensitive credential or token embedded in query parameters.

### 2.4 Login & Registration Flows (`LoginPage.vue` & `RegisterPage.vue`)
- **Dual-Mode Login:** `LoginPage.vue` supports Email OTP login for players and username/password login for administrators.
- **Masked Destination Display:** Both pages display masked email addresses (`p***@example.com`) returned from the backend `/otp/request` response rather than re-displaying raw query values.
- **Cooldown Isolation:** A reactive 60-second cooldown is enforced locally and coordinated with backend HTTP 429 `Retry-After` headers.

---

## 3. Storage Security & XSS Threat Model

### 3.1 Transparent Architectural Disclosure: `sessionStorage` vs. `HttpOnly` Cookies

> [!WARNING]
> **`sessionStorage` is NOT HttpOnly:**  
> By definition, `sessionStorage` is a client-side Web Storage API that is fully readable and writable by any JavaScript executing within the same origin. It **does not** provide HttpOnly protection. If an attacker successfully executes malicious JavaScript (via an XSS vulnerability or compromised third-party dependency), the token stored in `sessionStorage` can be exfiltrated.

### 3.2 Mitigation Layers Implemented
To mitigate this inherent limitation of JavaScript-accessible storage:
1. **Zero Raw HTML Injection:** A full AST search across `ros-website/src` confirms that neither `v-html` nor `element.innerHTML` is used anywhere. All user inputs (email addresses, callsigns/nicknames, error messages) are rendered strictly via Vue template text interpolation (`{{ }}`), which executes automatic character escaping for `<`, `>`, `&`, `"`, and `'`.
2. **Ephemeral Lifetime:** `sessionStorage` does not persist across browser tabs or after window closure, reducing the window of opportunity for local token compromise on shared workstations.
3. **Strict Content Boundaries:** No third-party analytics, tracking scripts, ad pixels, or external CDN scripts are imported. All JavaScript and CSS assets are bundled locally by Vite.

### 3.3 Backend Support Analysis: Why Cookies Were NOT Introduced
The backend `ros-private-server` currently implements RFC 6750 Bearer authentication using FastAPI's standard `OAuth2PasswordBearer(tokenUrl=...)`. It does not include:
- `Set-Cookie` header generation with `HttpOnly`, `Secure`, and `SameSite` flags.
- CSRF middleware or double-submit cookie validation.
- Cookie-based authentication dependencies for Mercury gateway or iOS companion handshakes.

Introducing cookie authentication at this stage would require breaking changes to backend dependencies, adding CSRF validation layers, and modifying the mobile client integration contract. Therefore, per the explicit instruction:
> *"Do not introduce cookie authentication unless the backend is verified to support it and the change can be safely implemented without breaking existing authentication."*

The current Bearer token model over `sessionStorage` is retained as the correct, non-breaking architecture for Phase P03.

---

## 4. OTP Cryptographic Security & Lockout Verification

The backend OTP implementation in `ros-private-server/app/account/service.py` was inspected and verified against the remediation standards established in Phase P02.1:
1. **Server-Side Keyed Hashing:** OTP codes are never stored in plaintext. They are hashed using HMAC-SHA256 keyed with `settings.OTP_HMAC_SECRET`:
   ```python
   expected_hash = hmac.new(
       settings.OTP_HMAC_SECRET.encode("utf-8"),
       req.code.strip().encode("utf-8"),
       hashlib.sha256
   ).hexdigest()
   ```
2. **Constant-Time Comparison:** Hashed digests are verified using `secrets.compare_digest(record.otp_hash, expected_hash)` to eliminate timing side-channel attacks.
3. **Sliding-Window Cooldown:** Consecutive OTP requests to the same email within 60 seconds are rejected with HTTP 429 (`"Please wait X seconds before requesting another code."`).
4. **5-Attempt Challenge Lockout:** Each challenge record tracks failed attempts. On the 5th failed attempt:
   - Challenge status is immediately set to `locked`.
   - The challenge is rendered permanently invalid.
   - The user account itself remains unlocked, preventing Denial-of-Service attacks against legitimate players.
