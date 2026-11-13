# ROS Sothat — Phase P02: Backend Audit Report
**Document ID:** `01_backend_audit.md`  
**System:** ROS Sothat Private Server Foundation (`ros-private-server`)  
**Phase:** P02 (Backend Foundation & Email OTP Integration)  
**Date:** November 2026  
**Status:** COMPLETE & VERIFIED  

---

## 1. Executive Summary

This audit assesses the architecture, code structure, database schemas, security posture, and test coverage of the `ros-private-server` repository located at `D:\ROS-Legacy-Analysis\ros-private-server`. 

The objective of Phase P02 is to introduce a secure, passwordless email OTP (One-Time Password) registration and authentication system for 10–20 invited friends, while maintaining 100% backward compatibility with existing admin password authentication, admin RBAC, diamond ledgers, inventory management, and automated test fixtures.

Prior to modifications, the existing baseline test suite was executed:
- **Total Tests Collected:** 134 items
- **Passed:** 133 passed
- **Skipped:** 1 skipped (`test_live_postgresql_execution_if_configured`)
- **Failed / Errors:** 0
- **Duration:** 105.72s

Both original binary assets were verified against their known golden SHA-256 checksums:
- `RoS-Legacy-iOS.ipa`: `D1F638AD49387A0BCA3B5E391799E07FAA12F3DCA7DB32F9FD22F07DB14E8C55` (Match confirmed)
- `Payload/client.app/client`: `51E63BFEA67E62F8ADF32B0664148576725832761C897216CC526F8814123DD6` (Match confirmed)

---

## 2. Framework & Environment Audit

| Component | Detected Specification | Verification Notes |
| :--- | :--- | :--- |
| **Python Runtime** | Python 3.11.9 (64-bit win32) | Windows host environment |
| **Web Framework** | FastAPI 0.162.2 / Starlette 0.46.1 | Async ASGI architecture |
| **ORM / Data Layer** | SQLAlchemy 2.1.8 | Async engine with `aiosqlite` and optional `asyncpg` |
| **Validation** | Pydantic 2.14.3 | Strict model validation with `extra="forbid"` |
| **Test Runner** | Pytest 9.2.0 (`pytest-asyncio` 1.4.1.post1) | In-memory SQLite with `StaticPool` |
| **HTTP Client** | HTTPX 0.28.1 | Async ASGI transport testing |

---

## 3. Architecture & Module Structure

The backend is structured into modular sub-packages within `app/`:
```
ros-private-server/
├── app/
│   ├── account/          # Account model, repository, service, schemas, rate limiter
│   ├── admin/            # Admin RBAC, diamond grants, catalog/inventory management
│   ├── cli/              # CLI tools (e.g., admin bootstrap)
│   ├── database/         # Declarative Base, async session maker, init_db
│   ├── economy/          # Diamond transaction ledger and balance management
│   ├── inventory/        # Player inventory, item catalog, slot management
│   ├── lobby/            # In-memory lobby presence management
│   ├── matchmaking/      # In-memory matchmaking queue and pairing
│   ├── player/           # Character profile, appearance, settings
│   ├── room/             # In-memory game room lifecycle
│   ├── config.py         # Centralized Pydantic application settings
│   ├── logging_config.py # Structured logger setup
│   └── main.py           # FastAPI application root, lifespan, CORS, error handling
├── discovery/            # Server discovery protocol parser and router
├── docs/                 # Architectural specifications
├── gateway/              # Gateway protocol handling
├── mercury/              # Mercury protocol framing, transport, channel logic
├── migrations/           # Versioned SQL migration scripts (001 - 004)
├── tests/                # 134 automated unit and integration tests
├── pytest.ini            # Pytest configuration
├── requirements.txt      # Dependency manifest
└── README.md             # Project documentation
```

---

## 4. Account & Authentication Audit

### 4.1 Current Schema (`app/account/models.py`)
```python
class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    device_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="player", nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    character: Mapped[Optional["Character"]] = relationship(...)
```

### 4.2 Current Authentication Flow
1. **Password Authentication:**
   - PBKDF2-HMAC-SHA256 with 100,000 iterations using a per-account 16-byte random hex salt (`secrets.token_hex(16)`).
   - Verifications use constant-time `hmac.compare_digest`.
2. **Token Format:**
   - Lightweight HMAC-SHA256 compact JWT: `base64url(payload).base64url(sig)` signed with `settings.SECRET_KEY`.
   - Payload contains `sub` (account_id), `username`, `role`, and `exp` (timestamp).
   - TTL configured by `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 1440 min / 24 hours).
3. **Guest Authentication:**
   - Registered using client `device_id`. Generates a username `guest_<hex>`.
4. **Rate Limiting:**
   - Sliding-window in-memory rate limiter per IP:
     - Login: 5 requests / 60 seconds (`RATE_LIMIT_LOGIN_MAX_REQUESTS`).
     - Register: 3 requests / 60 seconds (`RATE_LIMIT_REGISTER_MAX_REQUESTS`).

---

## 5. Existing API Endpoints Inventory

| Method | Endpoint | Description | Auth Required | Rate Limited |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | Server and database health check | No | No |
| `POST` | `/api/v1/account/register` | Username & password account registration | No | Yes (Register) |
| `POST` | `/api/v1/account/login` | Username & password authentication | No | Yes (Login) |
| `POST` | `/api/v1/account/guest` | Hardware device ID guest login | No | Yes (Register) |
| `GET` | `/api/v1/account/me` | Fetch authenticated account details | Yes (Bearer) | No |
| `POST` | `/api/v1/player/character` | Create character profile | Yes (Bearer) | No |
| `GET` | `/api/v1/player/character` | Fetch character profile | Yes (Bearer) | No |
| `PATCH` | `/api/v1/player/character/settings` | Update settings and appearance | Yes (Bearer) | No |
| `POST` | `/api/v1/admin/diamonds/grant` | Admin diamond grant | Yes (Admin) | No |
| `POST` | `/api/v1/admin/diamonds/deduct` | Admin diamond deduction | Yes (Admin) | No |
| `GET` | `/api/v1/admin/diamonds/history` | Audit trail of diamond transactions | Yes (Admin) | No |
| `POST` | `/api/v1/admin/catalog/items` | Create catalog item | Yes (Admin) | No |
| `GET` | `/api/v1/admin/catalog/items` | List catalog items | Yes (Admin) | No |
| `POST` | `/api/v1/admin/inventory/grant` | Grant item to character | Yes (Admin) | No |
| `POST` | `/api/v1/admin/inventory/remove` | Remove item from character | Yes (Admin) | No |
| `GET` | `/api/v1/admin/inventory/{char_id}` | Inspect character inventory | Yes (Admin) | No |
| `GET` | `/api/v1/admin/inventory/history` | Inventory audit trail | Yes (Admin) | No |
| `PATCH` | `/api/v1/admin/accounts/{id}/role` | Promote/demote account role | Yes (Admin) | No |
| `PATCH` | `/api/v1/admin/accounts/{id}/ban` | Ban/unban account | Yes (Admin) | No |
| `GET` | `/api/v1/admin/accounts` | Paginated account list | Yes (Admin) | No |

---

## 6. Integration Requirements & Risks Analysis for Email OTP

### 6.1 Requirements
1. **Passwordless Email Login/Registration:**
   - 10–20 invited friends should be able to register and log in via email verification codes.
   - 6-digit numeric OTP with 5-minute expiration (300 seconds).
   - 60-second cooldown between resend requests.
   - Maximum 5 failed verification attempts before invalidation.
2. **Preservation of Admin Passwords & RBAC:**
   - Existing administrative accounts must continue to use password login with full RBAC protection.
   - Admin bootstrap CLI (`app/cli/admin_bootstrap.py`) must continue operating without regression.
3. **Security & Cryptography:**
   - OTP codes must NEVER be stored in plaintext. Store salted SHA-256 hashes with random salts.
   - Timing-safe comparison via `hmac.compare_digest`.
   - User enumeration protection: Generic response on OTP request regardless of whether email exists.
   - Zero plaintext OTP in logs; email masking in logs (`j***@example.com`).
4. **Email Delivery Flexibility:**
   - Provider abstraction: Mock (for automated testing / memory inspection), Console (for local dev), and SMTP (for production).
5. **Database Safety:**
   - Non-destructive additions only:
     - Nullable `email` column in `accounts` table with unique index.
     - New dedicated table `email_otps`.
     - Raw SQL migration script `migrations/005_add_email_and_otp_tables.sql` providing both SQLite and PostgreSQL syntax.

### 6.2 Identified Risks & Mitigations
| Risk | Potential Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Column NOT NULL constraint on `password_hash`** | Existing `accounts` table has `password_hash NOT NULL`. Inserting an OTP account without password would violate constraint if schema is unchanged. | Assign a cryptographically disabled sentinel hash (e.g. `*OTP_ONLY_PASSWORDLESS*` + random salt) to passwordless accounts. Prevents password login while satisfying DB schema. |
| **Email Enumeration Attack** | Attacker probes `/api/v1/account/otp/request` to learn registered emails. | Endpoint returns identical HTTP 200 generic response: `"If this email is valid, a verification code has been sent."` regardless of user existence. |
| **Brute Force on 6-digit OTP** | $10^6$ combinations could be brute-forced without attempt capping. | Restrict to 5 attempts per OTP code (`attempts_left`). Mark code invalid on 5th failure. Sliding-window IP rate limiting. |
| **OTP Flooding / Email Spam** | Malicious client requests hundreds of emails per minute to flood an inbox. | Enforce 60-second cooldown per email; enforce IP-based rate limiting on request endpoint. |
| **Database Lock / Regression in Tests** | SQLite test concurrency issues. | `StaticPool` and clean session management already implemented in `conftest.py`. |

---

## 7. Approval & Conclusion

The backend architecture is modular, well-tested, and well-suited for non-invasive extension. Implementation of Phase P02 may proceed following the approved minimal-change plan.
