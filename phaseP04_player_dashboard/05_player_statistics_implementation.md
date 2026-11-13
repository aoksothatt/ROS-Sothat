# Phase P04 — Player Statistics & Match Telemetry Implementation

**Document:** `05_player_statistics_implementation.md`  
**Phase:** P04 (Player Dashboard Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Authentic Match Metrics, Calculated Performance Ratios & Honest Status  
**Security Level:** Read-Only Analysis & Isolated Development  

---

## 1. Overview & Core Philosophy

The Statistics view ([src/pages/dashboard/StatisticsPage.vue](file:///D:/ROS-Legacy-Analysis/ros-website/src/pages/dashboard/StatisticsPage.vue)) provides players with visibility into their battle royale survival records and combat performance telemetry.

In accordance with Phase P04 requirements:
> *"If no real match statistics are available, create a clean development-state page. Display: 'Player statistics will appear here when match tracking is available.' Do not: Generate fake statistics, generate random charts, use sample data in the real player dashboard, claim that matches have been completed, or pretend that the game server is playable."*

The implementation displays genuine database values without fabricating mock curves or fake win rates.

---

## 2. Backend Statistics Architecture

In `ros-private-server/app/player/models.py`, each character record maintains a structured JSON telemetry dictionary initialized upon character deployment:

```python
stats: Mapped[Dict[str, Any]] = mapped_column(
    JSON,
    default=lambda: {
        "total_matches": 0,
        "total_wins": 0,
        "total_kills": 0,
        "damage_dealt": 0.0
    },
    nullable=False
)
```

These fields are transmitted to the frontend via `CharacterOut` over `GET /api/v1/player/character`.

---

## 3. UI Presentation & Honest Status Disclosure

### 3.1 Match Telemetry Status Banner
At the top of the statistics page, a prominent tactical banner states:
- **Title:** `Multiplayer Match Tracking In Development`
- **Badge:** `MATCH TELEMETRY PENDING`
- **Explanation:** Informs the player that multiplayer dedicated server rooms and CellApp match resolution are in active engineering. Initial accounts correctly hold baseline zeroes. Once private island matches go live, telemetry will accumulate automatically.

### 3.2 Primary Verified Metric Cards
Renders 4 distinct cards displaying actual database values:
1. **Total Matches:** `character.stats.total_matches` (0)
2. **Victories / Wins:** `character.stats.total_wins` (0)
3. **Confirmed Kills:** `character.stats.total_kills` (0)
4. **Damage Dealt:** `character.stats.damage_dealt` (0.0 HP)

### 3.3 Derived Performance Ratios
Where mathematical formulas apply, the client derives metrics using documented equations:
- **Win Rate:**
  $$\text{Win Rate} = \begin{cases} \left(\frac{\text{total\_wins}}{\text{total\_matches}} \times 100\right)\% & \text{if } \text{total\_matches} > 0 \\ 0.0\% & \text{otherwise} \end{cases}$$
- **Kill/Match Ratio:**
  $$\text{Kill Ratio} = \begin{cases} \frac{\text{total\_kills}}{\text{total\_matches}} & \text{if } \text{total\_matches} > 0 \\ 0.00 & \text{otherwise} \end{cases}$$
- **Survival Bracket:** `RECRUIT` (initial baseline rating)

### 3.4 Authenticity Commitment
The footer features a verified integrity pledge:
> *"Player statistics will appear here when match tracking is available. ROS Sothat does not fabricate match records, fake kill ratios, or invent imaginary combat charts."*

---

## 4. Downstream Roadmap: CellApp Match Resolution

When multiplayer gameplay on the private server is unlocked in subsequent engine phases:
1. The game coordinator will record player eliminations, survival placements, and match end events.
2. The backend matchmaker/session adapter will atomically increment `total_matches`, `total_wins`, `total_kills`, and `damage_dealt` for each participant's character.
3. The Statistics page will immediately reflect those verified match records without frontend modifications.
