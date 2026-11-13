# Phase P04 — API Security & Authorization Architecture

**Document:** `06_api_security_and_authorization.md`  
**Phase:** P04 (Player Dashboard Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Endpoint Authorization, Cross-Account Isolation & Read-Only Governance  
**Security Level:** Read-Only Analysis & Isolated Development  

---

## 1. Executive Summary

Phase P04 implements strict security boundaries across all player dashboard interactions. Every request to `/api/v1/player/*` must prove authentication via a cryptographically signed Bearer token, derive operator identity exclusively from server-side claims, and execute in read-only mode without exposing administrative functions.

Cross-account isolation, invalid token rejection, and anonymous access denial are validated through automated regression tests in [ros-private-server/tests/test_player_dashboard_api.py](file:///D:/ROS-Legacy-Analysis/ros-private-server/tests/test_player_dashboard_api.py).

---

## 2. Authentication & Identity Derivation

### 2.1 Token Header Transmission
All dashboard API calls transmit the JWT access token via the HTTP header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
Tokens are never transmitted in URLs, query strings, or body payloads.

### 2.2 Server-Side Identity Resolution
FastAPI dependency injection (`Depends(get_current_account)`) decodes the JWT signature using the server secret key (`settings.SECRET_KEY`). If the signature is valid and the token has not expired, the backend retrieves the corresponding `Account` entity from the database.

```python
# app/account/service.py
async def get_current_account(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db)
) -> Account:
    payload = decode_token(token)
    account = await repo.get_by_id(payload["sub"])
    if not account or account.is_banned:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return account
```

### 2.3 Strict Parameter Independence
No dashboard endpoint accepts an `account_id` or `character_gid` query parameter to determine which records to fetch. The character lookup is always scoped internally:
```python
char = await player_service.repository.get_by_account_id(current_account.id)
```
This architectural design completely eliminates Insecure Direct Object Reference (IDOR) vulnerabilities.

---

## 3. Cross-Account Isolation Verification

Automated backend test `test_cross_account_isolation` verifies that:
1. `PlayerOne` (Account 1, Character `One_Hero`) authenticates and calls `GET /api/v1/player/character`. The server returns only `One_Hero`.
2. `PlayerTwo` (Account 2, Character `Two_Hero`) authenticates and calls `GET /api/v1/player/character`. The server returns only `Two_Hero`.
3. Neither player can intercept, view, or mutate the other's profile, inventory, or wallet balance.

```text
tests/test_player_dashboard_api.py::test_cross_account_isolation PASSED [100%]
```

---

## 4. Read-Only Governance & RBAC Shielding

### 4.1 Player Endpoint Restrictions
The player router (`/api/v1/player`) exposes no mutating economy or inventory routes:
- **No Diamond Mutations:** There are no routes to grant, deduct, or purchase diamonds.
- **No Inventory Mutations:** There are no routes to spawn, delete, or trade inventory items.
- **Controlled Settings Updates:** The only allowed mutations are personal gameplay preferences (`PUT /character/settings`) and cosmetic outfit equip selections (`PUT /character/appearances`), which validate payload sizes and key dictionaries against strict regex patterns.

### 4.2 Administrative Route Shielding
All economy management (`grant_diamonds`, `deduct_diamonds`) and catalog management (`create_item`, `grant_inventory_item`) endpoints remain under `/api/v1/admin/*`, protected by:
```python
async def get_current_admin(account: Account = Depends(get_current_account)) -> Account:
    if account.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required.")
    return account
```
Any attempt by a standard player token to access administrative endpoints immediately results in HTTP 403 Forbidden.

---

## 5. Token Storage Posture & Session Expiration

- **Client Storage Mechanism:** `sessionStorage` (`STORAGE_KEY = 'ros_sothat_token'`).
- **Security Limitation Disclosed:** As established in Phase P03.1, `sessionStorage` is accessible to JavaScript and does not provide HttpOnly protection. It was selected because it automatically clears upon tab closure and eliminates cross-tab leakage.
- **Expiration Invalidation:** When an expired or revoked token is used, `authService.getProfile()` throws HTTP 401. The client catches this error, invokes `authStore.logout()`, deletes the stored token from `sessionStorage`, and redirects the browser to `/login`.
