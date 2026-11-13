# Phase P03 — Authentication & Security Architecture

**Document:** `04_authentication_security.md`  
**Phase:** P03 (Website Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Security Evaluation, Token Lifecycle, Threat Mitigation & Safe Local Practices  
**Security Level:** Read-Only Analysis / Local Isolated Implementation  

---

## 1. Security Overview

The ROS Sothat web platform implements a hardened, passwordless authentication model powered by short-lived email One-Time Passwords (OTP) and signed JSON Web Tokens (JWT). Because the private server serves a closed group of 10–20 invited friends, the security architecture prioritizes simplicity, rapid onboarding, and defense-in-depth against credential stuffing, brute-force attacks, and token leakage.

---

## 2. Token Lifecycle & Storage Architecture

### 2.1 Token Issuance
Upon successful verification of a 6-digit OTP code at `/api/v1/account/otp/verify`, the backend generates an HMAC-SHA256 signed JWT containing:
- `sub`: User ID (UUID)
- `email`: Player or admin email address
- `role`: Role privilege (`player`, `admin`, or `moderator`)
- `exp`: Expiration timestamp (standard 24-hour lifetime)

### 2.2 Storage Rationale: Pinia In-Memory + `sessionStorage`
The client application employs a hybrid storage strategy:
1. **Primary State (In-Memory Pinia Store):** The active token and authenticated user profile reside in reactive memory within [src/stores/auth.ts](file:///D:/ROS-Legacy-Analysis/ros-website/src/stores/auth.ts).
2. **Session Persistence (`sessionStorage`):** The token is mirrored to the browser's `sessionStorage` to allow seamless page refreshes within the same tab without forcing the player to re-authenticate.

#### Security Comparison:
| Storage Mechanism | Persists Across Tabs | Persists on Window Close | Vulnerable to CSRF | XSS Exposure Risk |
| :--- | :--- | :--- | :--- | :--- |
| **`localStorage`** | Yes (Indefinitely) | Yes | No | High (Accessible via XSS) |
| **`sessionStorage` (Used)** | No (Tab-isolated) | **No (Cleared on close)** | **No** | **Low (Ephemeral)** |
| **Plain Cookies** | Yes | Configurable | High (Requires CSRF tokens) | High |
| **HttpOnly Cookies** | Yes | Configurable | Requires CSRF tokens | None |

`sessionStorage` was chosen because:
- It automatically purges credentials as soon as the user closes the browser tab or window.
- It prevents cross-tab leakage on shared or borrowed computers.
- It completely eliminates Cross-Site Request Forgery (CSRF) vectors because browsers do not attach `sessionStorage` values automatically to outgoing requests. Every API call requires explicit header injection via JavaScript (`Authorization: Bearer <token>`).

---

## 3. Defense Against Common Web Vulnerabilities

### 3.1 Cross-Site Scripting (XSS)
- **Automatic Output Escaping:** All dynamic content in Vue 3 templates (`{{ user.email }}`, `{{ profile.nickname }}`) is automatically string-escaped before insertion into the DOM.
- **Zero `v-html` Usage:** The entire codebase prohibits the use of `v-html`. No raw HTML can be injected via email addresses, nicknames, or API error messages.
- **Strict TypeScript Typing:** All inputs and API payloads are bound to rigid TypeScript interfaces (`OTPRequestPayload`, `OTPVerifyPayload`, `UserProfile`), preventing arbitrary property injection.

### 3.2 Cross-Site Request Forgery (CSRF)
- Because the backend does not rely on ambient authentication cookies, malicious third-party websites cannot forge authenticated requests against the ROS Sothat API.
- All requests must include the explicit `Authorization: Bearer <token>` header, which standard cross-origin form submissions and script tags cannot supply.

### 3.3 Brute-Force & Flood Protections
The frontend actively cooperates with backend rate-limiting defenses implemented in Phases P02 and P02.1:
1. **60-Second Request Cooldown:**
   - Once an OTP is requested, the client locks the "Send Code" button and initiates a reactive 60-second visual countdown.
   - If the user reloads or attempts to bypass the timer, the backend returns HTTP 429 (`Too Many Requests`), which the frontend catches to re-engage the cooldown.
2. **5-Attempt Lockout Defense:**
   - Each OTP challenge allows a maximum of 5 verification attempts.
   - The backend increments the failure counter on each incorrect guess and includes remaining attempts in the error response (`"Invalid OTP code. 3 attempts remaining."`).
   - The frontend displays this warning prominently to prevent accidental lockout.
   - Upon the 5th failed attempt, the challenge is permanently destroyed (status set to `locked`). The frontend informs the user that a new code must be requested.
3. **Challenge Isolation:**
   - Locking an OTP challenge does **not** lock the underlying player account. Attackers cannot induce a permanent denial-of-service on legitimate users by flooding bad OTP guesses.

---

## 4. Client-Side Routing & Navigation Guards

The Vue Router configuration in [src/router/index.ts](file:///D:/ROS-Legacy-Analysis/ros-website/src/router/index.ts) enforces route-level authentication barriers before any page component is rendered.

```typescript
router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore();
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // Preserve intended destination in redirect query parameter
    next({ name: 'login', query: { redirect: to.fullPath } });
  } else if (to.meta.guestOnly && authStore.isAuthenticated) {
    // Prevent logged-in users from seeing login/register forms
    next({ name: 'dashboard' });
  } else {
    next();
  }
});
```

### Route Protection Matrix:
| Route Path | Component | Guard Policy | Behavior When Unauthorized | Behavior When Authorized |
| :--- | :--- | :--- | :--- | :--- |
| `/` | `HomePage` | Public | Allowed | Allowed |
| `/register` | `RegisterPage` | `guestOnly` | Allowed | Redirects to `/dashboard` |
| `/login` | `LoginPage` | `guestOnly` | Allowed | Redirects to `/dashboard` |
| `/dashboard` | `DashboardPage` | `requiresAuth` | Redirects to `/login?redirect=/dashboard` | Allowed |
| `/:pathMatch(.*)*` | `NotFoundPage` | Public | Allowed | Allowed |

---

## 5. Development Security & Mock Email Safety

In local development and automated testing environments:
1. **Console Email Provider:** The backend utilizes `ConsoleEmailProvider` or `MockEmailProvider` (`app/email/provider.py`). OTP codes are output directly to the backend terminal log:
   ```text
   [MOCK EMAIL] To: friend@example.com | Subject: Your ROS Sothat Verification Code | Code: 492815
   ```
2. **Zero External SMTP Sockets:** No outgoing TCP connections are made to third-party mail relays (SendGrid, Mailgun, Amazon SES). This eliminates API key leakage risks and prevents inadvertent email spam.
3. **Zero Plaintext Secrets:** No passwords or secret keys are hardcoded in frontend source files or checked into repository version control.
