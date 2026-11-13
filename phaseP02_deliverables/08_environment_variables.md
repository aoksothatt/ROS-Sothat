# ROS Sothat — Environment Variables Reference & Configuration Guide
**Document ID:** `08_environment_variables.md`  
**System:** ROS Sothat Private Server Platform  
**Phase:** P02 (Backend Foundation & Email OTP Integration)  
**Date:** November 2026  
**Status:** COMPLETE & DOCUMENTED  

---

## 1. Environment Variable Reference

All configuration variables are defined with sensible, safe local defaults in `app/config.py` using Pydantic. In production, variables are loaded from the host environment or a `.env` file.

### 1.1 New Variables (Phase P02: Email & OTP)

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `EMAIL_PROVIDER` | string | `"mock"` | Active email delivery driver: `"mock"`, `"console"`, or `"smtp"`. |
| `SMTP_HOST` | string | `"localhost"` | SMTP server hostname or IP address. |
| `SMTP_PORT` | integer | `587` | SMTP server port (`587` for STARTTLS, `465` for SSL, `25` for unencrypted local relay). |
| `SMTP_USER` | string | `""` | SMTP username or API key (e.g., `apikey` for SendGrid). |
| `SMTP_PASSWORD` | string | `""` | SMTP password, app password, or API token. |
| `SMTP_FROM` | string | `"noreply@ros-sothat.internal"` | Sender email address included in outgoing email headers. |
| `SMTP_TLS` | boolean | `true` | When `true`, initiates STARTTLS encryption over ports 587/25. |
| `OTP_EXPIRE_SECONDS` | integer | `300` | Lifetime in seconds before an issued OTP expires (5 minutes). |
| `OTP_RESEND_COOLDOWN_SECONDS` | integer | `60` | Cooldown in seconds before an email can request a new OTP code. |
| `OTP_MAX_ATTEMPTS` | integer | `5` | Maximum failed verification attempts before permanent code invalidation. |
| `OTP_CODE_LENGTH` | integer | `6` | Length of numeric verification code (defaults to 6 digits). |
| `RATE_LIMIT_OTP_REQUEST_MAX` | integer | `5` | Maximum OTP request calls allowed per IP within the window. |
| `RATE_LIMIT_OTP_REQUEST_WINDOW_SECONDS` | integer | `60` | Sliding-window duration for OTP requests (seconds). |
| `RATE_LIMIT_OTP_VERIFY_MAX` | integer | `10` | Maximum OTP verification calls allowed per IP within the window. |
| `RATE_LIMIT_OTP_VERIFY_WINDOW_SECONDS` | integer | `60` | Sliding-window duration for OTP verifications (seconds). |

---

### 1.2 Baseline Platform Variables (Preserved)

| Variable Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `PROJECT_NAME` | string | `"ROS Private Server Foundation"` | Display name of the backend service. |
| `DATABASE_URL` | string | `"sqlite+aiosqlite:///./ros_private.db"` | Async database connection string (SQLite or PostgreSQL). |
| `SECRET_KEY` | string | `"ros-private-insecure-dev-secret-key-..."` | 32-byte secret key for signing Bearer JWT tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | integer | `1440` | Bearer token lifespan in minutes (24 hours). |
| `HOST` | string | `"0.0.0.0"` | Local interface binding address. |
| `PORT` | integer | `8000` | HTTP port for FastAPI server. |
| `DEBUG` | boolean | `true` | Development mode; controls console banner printing. |
| `WORKER_GUARD_ENABLED` | boolean | `true` | Prevents split-brain by restricting concurrency to 1 worker. |
| `RATE_LIMIT_ENABLED` | boolean | `true` | Enables sliding-window rate limiters. |
| `RATE_LIMIT_LOGIN_MAX_REQUESTS` | integer | `5` | Max password logins per window per IP. |
| `RATE_LIMIT_LOGIN_WINDOW_SECONDS` | integer | `60` | Window for password login rate limiter. |
| `RATE_LIMIT_REGISTER_MAX_REQUESTS`| integer | `3` | Max password registrations per window per IP. |
| `RATE_LIMIT_REGISTER_WINDOW_SECONDS`| integer | `60` | Window for password registration rate limiter. |

---

## 2. Configuration Templates

### 2.1 Local Development (`.env.development`)
```ini
DEBUG=true
EMAIL_PROVIDER=console
DATABASE_URL=sqlite+aiosqlite:///./ros_private.db
SECRET_KEY=ros-sothat-local-dev-secret-key-32bytes-minimum!!
RATE_LIMIT_ENABLED=true
OTP_EXPIRE_SECONDS=300
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_ATTEMPTS=5
```

### 2.2 Automated Testing (`.env.testing`)
```ini
DEBUG=false
EMAIL_PROVIDER=mock
TEST_DATABASE_URL=sqlite+aiosqlite:///:memory:
SECRET_KEY=test-secret-key-for-unit-testing-32bytes-min!
RATE_LIMIT_ENABLED=true
```

### 2.3 Production Private Server (`.env.production`)
```ini
DEBUG=false
HOST=127.0.0.1
PORT=8000
DATABASE_URL=postgresql+asyncpg://ros_user:StrongPasswordHere@localhost:5432/ros_sothat_db
SECRET_KEY=GENERATE_RANDOM_SECURE_KEY_WITH_OPENSSL_HEX_64_CHARS
ACCESS_TOKEN_EXPIRE_MINUTES=1440
WORKER_GUARD_ENABLED=true

# Email SMTP Delivery
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=rossothat.notifications@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM="ROS Sothat <rossothat.notifications@gmail.com>"
SMTP_TLS=true

# Security Controls
RATE_LIMIT_ENABLED=true
OTP_EXPIRE_SECONDS=300
OTP_RESEND_COOLDOWN_SECONDS=60
OTP_MAX_ATTEMPTS=5
RATE_LIMIT_OTP_REQUEST_MAX=5
RATE_LIMIT_OTP_REQUEST_WINDOW_SECONDS=60
RATE_LIMIT_OTP_VERIFY_MAX=10
RATE_LIMIT_OTP_VERIFY_WINDOW_SECONDS=60
```
