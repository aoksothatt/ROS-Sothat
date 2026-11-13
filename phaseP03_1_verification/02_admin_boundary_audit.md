# Phase P03.1 — Admin Authentication & RBAC Boundary Audit

**Document:** `02_admin_boundary_audit.md`  
**Phase:** P03.1 (Final Website Verification)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Audit Target:** Role-Based Access Control (RBAC), Privilege Escalation Defense & Admin Boundaries  
**Security Level:** Read-Only Audit & Verified Hardening  

---

## 1. Executive Summary

An audit of administrative authentication boundaries was performed to verify that:
1. Administrative staff authenticate exclusively through the established backend endpoint (`POST /api/v1/account/login`).
2. Administrative privileges are strictly governed and verified server-side by database records and cryptographically signed JWT claims.
3. The frontend application cannot elevate privileges, grant admin status, or bypass role checks.
4. Player-facing views and routes do not expose administrative functions or controls.
5. Backend administrative RBAC infrastructure remains completely intact and unaltered.
6. In accordance with scope boundaries, no administrative dashboard was constructed in this phase (reserved for Phase P05).

---

## 2. Admin Authentication Flow & Backend Verification

### 2.1 Preserved Backend Endpoint (`POST /api/v1/account/login`)
The website's admin login option (`LoginPage.vue`) connects directly to the existing backend endpoint in `ros-private-server/app/account/router.py`:

```python
@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_login)])
async def login(
    req: AccountLogin,
    service: AccountService = Depends(get_account_service)
):
    """Authenticate account credentials and issue a Bearer token."""
    return await service.authenticate(req)
```

### 2.2 Server-Side Role Resolution
During authentication, the backend retrieves the account record directly from the database and embeds the persistent database role into the signed JWT:
```python
# app/account/service.py
token = self.create_token(account.id, account.username, account.role)
```
When `GET /api/v1/account/me` is called, the current account is fetched from the database session and the true role is returned:
```python
return AccountOut(
    id=current_account.id,
    username=current_account.username,
    email=current_account.email,
    role=current_account.role,
    ...
)
```

---

## 3. Frontend Role Governance & Immutability

### 3.1 Read-Only State in Pinia Store
In `ros-website/src/stores/auth.ts`:
```typescript
const isPlayer = computed(() => user.value?.role === 'player');
const isAdmin = computed(() => user.value?.role === 'admin');
```
- The frontend has **no** state setter or action allowing modification of `user.value.role`.
- The `user` object can only be populated by the response of `authService.getProfile(token)`, which queries the authenticated `/api/v1/account/me` endpoint.
- Manually altering local storage or in-memory variables in browser dev tools has zero effect on backend operations, as all administrative endpoints perform independent database role validation.

### 3.2 Impossibility of Client-Side Privilege Escalation
1. **Registration Immunity:** New registrations via email OTP always create accounts with `role="player"` hardcoded server-side (`app/account/service.py` line 501). The registration payload schema (`OTPVerifyRequest`) rejects arbitrary role parameters via Pydantic `extra="forbid"`.
2. **Promotion Mechanism:** Promoting an account to `admin` can only occur through:
   - Authenticated administrative API: `POST /api/v1/admin/accounts/{id}/role` (requires existing `get_current_admin` token).
   - Dedicated local CLI tool: `python -m app.cli.admin promote <username>` (executed directly on the host console with operator confirmation).

---

## 4. Player Route Isolation & Non-Exposure

### 4.1 Route Analysis (`ros-website/src/router/index.ts`)
The routes configured in the web client comprise:
- `/` (`HomePage`) — Public
- `/register` (`RegisterPage`) — Guest-only
- `/login` (`LoginPage`) — Guest-only
- `/dashboard` (`DashboardPage`) — Protected (`meta.requiresAuth`)
- `/404` (`NotFoundPage`) — Catch-all

There are **zero** administrative routes, pages, or components registered in `src/router/index.ts`.

### 4.2 Dashboard Page Isolation (`DashboardPage.vue`)
- The `DashboardPage.vue` component renders standard player telemetry (`username`, `id`, `created_at`, `last_login`, `character status`).
- If an administrator logs into the website, the banner simply displays the gold badge `"ADMIN"` instead of `"PLAYER"`. No admin panels, ban buttons, diamond grant controls, or user tables are rendered.
- All advanced capabilities are presented as passive, un-clickable informational cards badged `"IN DEVELOPMENT"` targeting subsequent phases.

---

## 5. Backend RBAC Enforcement Verification

Backend administrative routes are isolated under `/api/v1/admin` in `ros-private-server/app/admin/router.py`. Every route is guarded by FastAPI dependency injection:

```python
async def get_current_admin(
    account: Account = Depends(get_current_account)
) -> Account:
    if account.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required."
        )
    return account
```

### Automated Verification Test:
Backend regression suite `tests/test_admin_rbac.py` executes 11 distinct tests:
- `test_player_attempting_admin_access_rejected`: Asserts HTTP 403 Forbidden when a player token calls `/api/v1/admin/*`.
- `test_registration_cannot_create_admin`: Asserts registration produces strictly `role="player"`.
- `test_player_apis_cannot_change_own_role`: Asserts players cannot edit their own roles.
- `test_server_side_role_verification_dynamically_enforced`: Asserts demoted admins immediately lose admin route access.

All 11 tests continue to pass with 100% success.
