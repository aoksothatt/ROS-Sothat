# Phase P04 — Player Profile Implementation

**Document:** `02_player_profile_implementation.md`  
**Phase:** P04 (Player Dashboard Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Character Dossier, Identity Telemetry & Equipped Loadout Display  
**Security Level:** Read-Only Analysis & Isolated Development  

---

## 1. Overview & Objectives

The Player Profile view ([src/pages/dashboard/PlayerProfilePage.vue](file:///D:/ROS-Legacy-Analysis/ros-website/src/pages/dashboard/PlayerProfilePage.vue)) serves as the operative's personal military dossier. It displays verified database telemetry for the authenticated user and their linked in-game character profile.

---

## 2. Backend Data Integration & Model Schema

### 2.1 Backend Contract (`GET /api/v1/player/character`)
The profile connects to the existing endpoint in `ros-private-server/app/player/router.py`:
- **Method:** `GET`
- **Route:** `/api/v1/player/character`
- **Auth:** Required (`Bearer <token>`)
- **Isolation:** Scoped server-side via `current_account.id`

#### Response Schema (`CharacterOut`):
```json
{
  "gid": 101,
  "account_id": 1,
  "nickname": "ViperSniper",
  "char_type": 0,
  "level": 5,
  "exp": 450,
  "gold": 2500,
  "diamonds": 350,
  "appearances": {
    "equipped_clothing": [10001, 10002],
    "unlocked_items": [10001, 10002],
    "active_weapon_skin": 201
  },
  "settings": {
    "control_mode": 1,
    "fov": 80,
    "gyroscope": true,
    "sensitivity": { "general": 100, "aim": 85, "scope2x": 65 }
  },
  "stats": {
    "total_matches": 0,
    "total_wins": 0,
    "total_kills": 0,
    "damage_dealt": 0.0
  },
  "created_at": "2026-11-01T12:00:00Z",
  "updated_at": "2026-11-13T12:00:00Z"
}
```

---

## 3. UI Component Structure & User Experience

### 3.1 First-Time Onboarding Flow (Unassigned Character)
If an account has registered via email OTP but has not yet deployed an in-game character, `GET /api/v1/player/character` returns HTTP 404. 

The client handles this gracefully via `EmptyState.vue`:
- Informs the user that no character dossier is provisioned.
- Renders an inline character creation form allowing the operator to submit:
  - Callsign / Nickname (validated 2–24 characters)
  - Operative Model (Male Type 0 or Female Type 1)
- Submits to `POST /api/v1/player/character` and dynamically refreshes the view upon completion.

### 3.2 Full Character Dossier Presentation
Once provisioned, the profile displays 4 structured cards:
1. **Identity & Level Progression Card:**
   - Callsign title with operative avatar glyph.
   - Character GID and gender classification.
   - Dynamic Level badge and visual EXP progress bar (`exp / 1,000`).
   - Quick diamond and gold reserves.
2. **Account Security Telemetry Card:**
   - Account GID (`#1`) and Platform Role (`player` badge).
   - Linked email address.
   - Creation and synchronization timestamps.
   - Enforcement standing (`GOOD STANDING`).
3. **Equipped Loadout Card:**
   - Active weapon skin ID or `"Default Standard Skin"`.
   - Equipped clothing IDs rendered as tactical badges.
4. **Control & Visual Configuration Card:**
   - In-game control mode, Field of View (FOV in degrees), Gyroscope aiming status, and Aim sensitivity percentage.

---

## 4. Security & Read-Only Governance

- **Cross-Account Isolation:** The endpoint strictly resolves identity from decoded JWT claims. A player cannot view another player's profile by changing URL or query parameters.
- **Read-Only Posture:** The profile page does not expose client-side role modification or balance alteration controls.
- **No Internal Leaks:** Internal password hashes, salt strings, and private database connection handles are strictly omitted from the API response and DOM.
