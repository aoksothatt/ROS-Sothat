# Rules of Survival (ROS) — Private Server Foundation (Phase 5)

An independent, modular, high-performance private backend foundation designed with **Python 3.11**, **FastAPI**, **AsyncIO**, and **SQLAlchemy 2.0**.

> [!NOTE]
> This service is an independent backend foundation developed for private servers and testing. It operates completely independently of official NetEase / Rules of Survival production infrastructure. It does **not** connect to official authentication services, does **not** bypass access controls, and does **not** forge official tickets.

---

## 1. Features & Capabilities

- **Account Service**:
  - Standard user registration and authentication with salted **PBKDF2-HMAC-SHA256** password hashing.
  - Guest one-click registration supporting hardware device identifiers.
  - HMAC-SHA256 cryptographically signed bearer tokens with configurable expiration.
- **Player & Character Management**:
  - Global unique character nicknames.
  - Character GID (Game ID) allocation.
  - Appearance and cosmetic customization inventory stored as flexible JSON structures.
  - Control configuration and client settings stored as persistent JSON data.
  - Public player profile lookup.
- **Lobby Service**:
  - Real-time in-memory presence tracking of online players.
  - Client heartbeat mechanism with automatic timeout cleanup.
  - Active online player directory with filtering.
- **Custom Room Management**:
  - Public and private password-protected game rooms.
  - Configurable room capacity (1–100 players), team modes (Solo, Duo, Squad, Fireteam), and map selection.
  - Member readiness state management and validation.
  - Host migration upon host departure and automated room teardown when empty.
  - Match launch authorization that generates secure battle server allocation tokens.
- **Matchmaking Engine**:
  - Region-aware and mode-aware queuing (Solo, Duo, Squad).
  - Configurable player threshold resolution.
  - Asynchronous pairing returning battle server connection credentials and match tokens.
- **Dual Database Compatibility**:
  - Default asynchronous **SQLite** (`aiosqlite`) for zero-configuration local development on Windows.
  - Production-ready **PostgreSQL** (`asyncpg`) support via configurable environment variable.

---

## 2. Directory Architecture

```
ros-private-server/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings & environment variables
│   ├── logging_config.py          # Unified structured logging
│   ├── main.py                   # FastAPI application factory & router registration
│   │
│   ├── database/                 # SQLAlchemy 2.0 Async database layer
│   │   ├── __init__.py
│   │   ├── base.py               # DeclarativeBase model registry
│   │   └── session.py            # Async engine and sessionmaker dependency
│   │
│   ├── account/                  # Account & Authentication module
│   │   ├── __init__.py
│   │   ├── models.py             # Account ORM entity
│   │   ├── schemas.py            # Registration, login, and token Pydantic models
│   │   ├── repository.py         # Account database operations
│   │   ├── service.py            # Password hashing, PBKDF2 verification, JWT tokens
│   │   └── router.py             # /api/v1/account endpoints
│   │
│   ├── player/                   # Player Profile & Customization module
│   │   ├── __init__.py
│   │   ├── models.py             # Character ORM entity (cosmetics, settings, stats)
│   │   ├── schemas.py            # Character creation & profile schemas
│   │   ├── repository.py         # Character database operations
│   │   ├── service.py            # Character business logic & validation
│   │   └── router.py             # /api/v1/player endpoints
│   │
│   ├── lobby/                    # Lobby & Presence module
│   │   ├── __init__.py
│   │   ├── models.py             # PlayerPresence dataclass
│   │   ├── schemas.py            # Lobby status & online listing schemas
│   │   ├── service.py            # Thread-safe in-memory presence & heartbeats
│   │   └── router.py             # /api/v1/lobby endpoints
│   │
│   ├── room/                     # Custom Room management module
│   │   ├── __init__.py
│   │   ├── models.py             # CustomRoom dataclass & room state
│   │   ├── schemas.py            # Room creation, details, and join schemas
│   │   ├── service.py            # Room lifecycle, host migration & match launch
│   │   └── router.py             # /api/v1/room endpoints
│   │
│   └── matchmaking/              # Matchmaking Engine module
│       ├── __init__.py
│       ├── schemas.py            # Match ticket schemas
│       ├── service.py            # Match queue & pairing threshold engine
│       └── router.py             # /api/v1/matchmaking endpoints
│
├── tests/                        # Automated Pytest suite
│   ├── __init__.py
│   ├── conftest.py               # Async test client & isolated in-memory DB fixture
│   ├── test_account.py           # Account & auth tests
│   ├── test_player.py            # Character & profile tests
│   ├── test_lobby.py             # Presence & heartbeat tests
│   ├── test_room.py              # Custom room lifecycle tests
│   └── test_matchmaking.py       # Pairing engine tests
│
├── pytest.ini                    # Pytest AsyncIO test runner configuration
├── requirements.txt              # Production and development dependencies
└── README.md                     # Documentation and operations guide
```

---

## 3. Quickstart Guide (Windows Development)

### Prerequisites
- Python 3.11 installed (add to PATH).
- Git (optional).

### Setup Steps
1. Navigate into the `ros-private-server` directory:
   ```powershell
   cd ros-private-server
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install required dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Run the automated test suite:
   ```powershell
   pytest tests -v
   ```
5. Start the development server with live reload:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
6. Access interactive API documentation:
   - **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
   - **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
   - **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 4. Production Deployment Guide (Linux)

### 1. System Requirements & Setup
```bash
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib nginx

# Clone or transfer project files to /opt/ros-server
sudo mkdir -p /opt/ros-server
sudo chown $USER:$USER /opt/ros-server
cd /opt/ros-server

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install asyncpg
```

### 2. PostgreSQL Configuration
```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE ros_private_db;
CREATE USER ros_admin WITH PASSWORD 'StrongDatabasePassword123!';
GRANT ALL PRIVILEGES ON DATABASE ros_private_db TO ros_admin;
\q
```

### 3. Environment Configuration
Create `/opt/ros-server/.env`:
```ini
ENVIRONMENT=production
DEBUG=false
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SECRET_KEY=ReplaceWith64HexCharactersGeneratedByOpenSSL
DATABASE_URL=postgresql+asyncpg://ros_admin:StrongDatabasePassword123!@localhost:5432/ros_private_db
BATTLE_SERVER_HOST=203.0.113.50
BATTLE_SERVER_PORT=20013
```

### 4. Systemd Service Setup
Create `/etc/systemd/system/ros-backend.service`:
```ini
[Unit]
Description=ROS Private Server Backend Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/ros-server
EnvironmentFile=/opt/ros-server/.env
ExecStart=/opt/ros-server/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=5

# NOTE on Workers: The initial backend foundation uses cooperative async in-memory state
# for lobby presence, custom rooms, and matchmaking queues. Single-worker mode (--workers 1)
# is enforced via startup safeguards to prevent process state desynchronization.
# Before scaling to multi-worker or multi-host deployments, an external state store
# (e.g. Redis / KeyDB) must be configured.

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ros-backend
sudo systemctl start ros-backend
sudo systemctl status ros-backend
```

### 5. Nginx Reverse Proxy Configuration
Create `/etc/nginx/sites-available/ros-backend`:
```nginx
server {
    listen 80;
    server_name api.ros-private.local;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/ros-backend /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 5. REST API Reference & Usage Examples

### 5.1 Account & Authentication

#### Register Account
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/account/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "Striker01", "password": "Password123!"}'
```
*Response (`201 Created`):*
```json
{
  "id": 1,
  "username": "Striker01",
  "is_banned": false,
  "created_at": "2026-11-09T02:40:00.000000",
  "last_login": null,
  "has_character": false
}
```

#### Login Account
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/account/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "Striker01", "password": "Password123!"}'
```
*Response (`200 OK`):*
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "account_id": 1,
  "username": "Striker01"
}
```

#### Guest Fast-Login
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/account/guest" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "ios-idfv-a1b2c3d4"}'
```

#### Get Current Account Info
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/account/me" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 5.2 Player & Character

#### Create Character
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/player/character" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"nickname": "GhostSniper", "char_type": 0}'
```
*Response (`201 Created`):*
```json
{
  "gid": 1,
  "account_id": 1,
  "nickname": "GhostSniper",
  "char_type": 0,
  "level": 1,
  "exp": 0,
  "gold": 1000,
  "diamonds": 100,
  "appearances": {
    "equipped_clothing": [10001, 10002],
    "unlocked_items": [10001, 10002],
    "active_weapon_skin": 0
  },
  "settings": {
    "control_mode": 1,
    "fov": 75,
    "gyroscope": false,
    "sensitivity": {"general": 100, "aim": 80, "scope2x": 60}
  },
  "stats": {
    "total_matches": 0,
    "total_wins": 0,
    "total_kills": 0,
    "damage_dealt": 0.0
  },
  "created_at": "2026-11-09T02:41:00.000000",
  "updated_at": "2026-11-09T02:41:00.000000"
}
```

#### Get Current Character Profile
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/player/character" \
  -H "Authorization: Bearer <TOKEN>"
```

#### Update In-Game Settings
```bash
curl -X PUT "http://127.0.0.1:8000/api/v1/player/character/settings" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"settings": {"fov": 90, "gyroscope": true}}'
```

#### Update Cosmetics & Appearances
```bash
curl -X PUT "http://127.0.0.1:8000/api/v1/player/character/appearances" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"appearances": {"equipped_clothing": [10005, 10010], "active_weapon_skin": 2001}}'
```

#### Query Public Profile by GID
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/player/1"
```

---

### 5.3 Lobby Presence

#### Enter Lobby
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/lobby/enter" \
  -H "Authorization: Bearer <TOKEN>"
```

#### Send Heartbeat Keep-Alive
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/lobby/heartbeat" \
  -H "Authorization: Bearer <TOKEN>"
```

#### List Online Players
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/lobby/online"
```

#### Leave Lobby
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/lobby/leave" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 5.4 Custom Rooms

#### Create Room
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/room/create" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Squad Practice",
    "map_id": 1,
    "capacity": 4,
    "team_mode": 4,
    "is_public": true,
    "password": "roompassword"
  }'
```

#### List Active Rooms
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/room/list"
```

#### Join Room
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/room/10001/join" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"password": "roompassword"}'
```

#### Toggle Ready State
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/room/10001/ready?is_ready=true" \
  -H "Authorization: Bearer <TOKEN>"
```

#### Start Match (Host Only)
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/room/10001/start" \
  -H "Authorization: Bearer <TOKEN>"
```
*Response (`200 OK`):*
```json
{
  "room_id": 10001,
  "status": "playing",
  "match_token": "mt_c2b0e...",
  "battle_server_ip": "127.0.0.1",
  "battle_server_port": 20013,
  "player_count": 2
}
```

#### Leave Room
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/room/10001/leave" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 5.5 Matchmaking Queue

#### Enqueue for Matchmaking
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/matchmaking/queue" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"match_mode": "solo", "region": "asia"}'
```
*Response (`201 Created`):*
```json
{
  "ticket_id": "mm_ticket_e4a3b2...",
  "gid": 1,
  "match_mode": "solo",
  "region": "asia",
  "status": "queued",
  "match_id": null,
  "battle_server_ip": null,
  "battle_server_port": null,
  "match_token": null,
  "assigned_players": []
}
```

#### Check Matchmaking Status
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/matchmaking/ticket/mm_ticket_e4a3b2..." \
  -H "Authorization: Bearer <TOKEN>"
```

#### Cancel Matchmaking Ticket
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/matchmaking/cancel/mm_ticket_e4a3b2..." \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 6. Verification and Testing

The backend includes a comprehensive automated test suite verifying all modules:
- Account registration, PBKDF2 hash verification, duplicate detection, and login flow.
- Character creation, GID allocation, cosmetic defaults, and nickname conflicts.
- In-memory lobby presence, heartbeat tracking, and clean removal on departure.
- Room creation, password security, member ready checks, host migration, and match start tokens.
- Queue matchmaking pairing with multi-player threshold resolution.

To run the test suite:
```powershell
pytest tests -v
```
Output:
```
tests/test_account.py::test_health_check PASSED                          [  8%]
tests/test_account.py::test_account_register_and_login PASSED            [ 16%]
tests/test_account.py::test_guest_login PASSED                           [ 25%]
tests/test_account.py::test_authenticated_me_endpoint PASSED             [ 33%]
tests/test_lobby.py::test_lobby_lifecycle PASSED                         [ 41%]
tests/test_lobby.py::test_lobby_entry_without_character PASSED           [ 50%]
tests/test_matchmaking.py::test_matchmaking_queue_and_cancel PASSED      [ 58%]
tests/test_matchmaking.py::test_matchmaking_pairing PASSED               [ 66%]
tests/test_player.py::test_character_creation_and_profile PASSED         [ 75%]
tests/test_player.py::test_duplicate_nickname_across_accounts PASSED     [ 83%]
tests/test_player.py::test_update_settings_and_appearances PASSED        [ 91%]
tests/test_room.py::test_room_management PASSED                          [100%]

============================= 12 passed in 2.58s ==============================
```

---

## 7. Next Steps & Phase Progression

1. **Phase 6**: Battle Server Protocol Bridge & Session Broker.
2. **Phase 7**: In-Game State & Dedicated Game World Simulation.
