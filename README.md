# ROS Sothat — Private Server Foundation & Web Dashboard

An independent, modular, high-performance private server foundation and modern web dashboard for Rules of Survival (ROS) research, development, and community hosting.

---

## Architecture Overview

This project consists of two core subsystems alongside extensive protocol research and phase audits:

```
ROS-Sothat/
├── ros-private-server/            # Asynchronous Python backend (FastAPI, SQLAlchemy 2.0)
│   ├── app/                       # Core service modules (Account, Economy, Inventory, Admin, Lobby, Room)
│   ├── migrations/                # Dual-syntax SQL migrations (SQLite & PostgreSQL)
│   └── tests/                     # 174 automated tests (unit, concurrency, RBAC, DDL compilation)
│
├── ros-website/                   # Modern Vue 3 + TypeScript single-page application
│   ├── src/                       # Frontend views, components, pinia stores, router guards
│   ├── tests/                     # Vitest test suites (unit, components, responsive viewports)
│   └── index.html                 # Main web portal entry point
│
├── phaseP02_deliverables/         # Phase P02 Email OTP registration & authentication
├── phaseP03_website/              # Phase P03 Web portal implementation & integration
├── phaseP04_player_dashboard/     # Phase P04 Player self-service dashboard
└── phaseP05_admin_dashboard/      # Phase P05 Secure administrator dashboard & audit trails
```

---

## 1. Backend (`ros-private-server`)

Built with **Python 3.11**, **FastAPI**, **AsyncIO**, and **SQLAlchemy 2.0**.

### Features
- **Account & Authentication**: PBKDF2-HMAC-SHA256 password hashing, device ID guest registration, 6-digit email OTPs, JWT bearer authentication with role-based access control (`player`, `admin`).
- **Player & Character Management**: Global nickname allocation, character customization, and cosmetic equipment management.
- **Economy & Inventory**: Append-only transactional ledgers for diamonds and catalog inventory items with atomic concurrency safety and strict non-negative check constraints.
- **Admin Dashboard APIs**: Player moderation (suspend/reactivate), currency adjustments, catalog management, and relational audit logging with `ON DELETE RESTRICT` integrity.
- **Lobby & Matchmaking**: In-memory player presence, room management, and regional matchmaking queues.
- **Dual Database Support**: Asynchronous SQLite (`aiosqlite`) for local zero-config development; PostgreSQL (`asyncpg`) for production.

### Quick Start (Backend)
```bash
cd ros-private-server
pip install -r requirements.txt
python -m pytest
python -m app.main
```

---

## 2. Frontend (`ros-website`)

Built with **Vue 3**, **Vite**, **TypeScript**, and **Tailwind CSS**.

### Features
- **Public Portal**: Authentication, OTP registration, and login flows.
- **Player Dashboard**: Character overview, currency wallet, inventory inspector, and settings.
- **Admin Dashboard**: System telemetry, player directory search, suspension controls, diamond/item grant/remove interfaces, and paginated audit logs.
- **Responsive Layout**: Designed for mobile (drawer layout), tablet, and desktop viewports.

### Quick Start (Frontend)
```bash
cd ros-website
npm install
npm test
npm run build
npm run dev
```

---

## Testing & Quality Assurance

- **Backend Test Suite:** 174 tests covering protocol framing, concurrency races, RBAC, and database integrity.
- **Frontend Test Suite:** 65 tests covering Pinia stores, auth services, router guards, and viewport responsiveness.
- **All tests pass with 0 failures.**

---

## License & Disclaimer

This project is developed independently for research, preservation, and private server analysis. It does not connect to or alter official game infrastructure. Original game binaries (`.ipa` and extracted binaries) are preserved locally and are excluded from this repository.
