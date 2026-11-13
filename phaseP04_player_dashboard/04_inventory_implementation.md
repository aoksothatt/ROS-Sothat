# Phase P04 — Tactical Inventory Implementation

**Document:** `04_inventory_implementation.md`  
**Phase:** P04 (Player Dashboard Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Item Catalog, Character Ownership, Inventory Grid & Category Filtering  
**Security Level:** Read-Only Analysis & Isolated Development  

---

## 1. Overview & Objectives

The Tactical Inventory view ([src/pages/dashboard/InventoryPage.vue](file:///D:/ROS-Legacy-Analysis/ros-website/src/pages/dashboard/InventoryPage.vue)) provides players with an organized visual armory displaying their verified in-game possessions. 

The implementation displays authentic item data from the backend relational catalog, supports dynamic category filtering, handles stackable items and empty states cleanly, and enforces strict read-only security.

---

## 2. Backend Relational Inventory Model

The inventory system is defined in `ros-private-server/app/inventory/models.py`:

### 2.1 Catalog Model (`items`)
- **Primary Key:** `id` (Integer)
- **Code:** `item_code` (Unique programmatic string, e.g., `M4A1_DRAGON`)
- **Metadata:** `name`, `description`, `item_type` (`WEAPON_SKIN`, `CLOTHING`, `CONSUMABLE`), `icon`
- **Stacking Configuration:** `stackable` (Boolean), `max_stack` (Integer, constrained `max_stack >= 1`)
- **Catalog State:** `is_active` (Boolean)

### 2.2 Ownership Model (`inventory_items`)
- **Foreign Keys:**
  - `character_gid` -> `characters.gid`
  - `item_id` -> `items.id`
- **Constraints:**
  - `UniqueConstraint("character_gid", "item_id", name="uq_character_inventory_item")` prevents duplicate slot allocations for the same item.
  - `CheckConstraint("quantity > 0", name="chk_inventory_item_quantity_positive")` guarantees zero-quantity items cannot persist in inventory.
- **ORM Relationship:** Uses `lazy="joined"` to automatically load catalog attributes alongside ownership records in a single query.

---

## 3. Backend API Contract (`GET /api/v1/player/character/inventory`)

The client queries the existing endpoint in `ros-private-server/app/player/router.py`:
- **Method:** `GET`
- **Route:** `/api/v1/player/character/inventory`
- **Query Parameters:** `limit: int = 50`, `offset: int = 0`
- **Authentication:** Required (`Bearer <token>`)

#### Response Schema (`CharacterInventoryResponse`):
```json
{
  "character_gid": 101,
  "total_items": 2,
  "items": [
    {
      "id": 1,
      "character_gid": 101,
      "item_id": 10,
      "quantity": 1,
      "created_at": "2026-11-01T12:00:00Z",
      "updated_at": "2026-11-01T12:00:00Z",
      "item": {
        "id": 10,
        "item_code": "M4A1_DRAGON",
        "name": "M4A1 Dragon Flame",
        "description": "Elite animated assault rifle skin.",
        "item_type": "WEAPON_SKIN",
        "icon": null,
        "stackable": false,
        "max_stack": 1,
        "is_active": true,
        "created_at": "2026-11-01T12:00:00Z",
        "updated_at": "2026-11-01T12:00:00Z"
      }
    }
  ]
}
```

---

## 4. Frontend UI & Interaction Architecture

### 4.1 Filter Toolbar
A dedicated toolbar allows operators to filter items by category:
- `ALL ITEMS` (default view)
- `WEAPONS & SKINS` (`WEAPON_SKIN`)
- `CLOTHING & GEAR` (`CLOTHING`)
- `CONSUMABLES & SUPPLIES` (`CONSUMABLE`)
- Active item counter displaying total items stored in personal storage.

### 4.2 Tactical Item Card Grid
Each item is rendered within a dark tactical card:
- **Card Header:** Displays `item_type` badge and quantity pill (e.g. `x5`).
- **Visual Display:** Category-specific tactical glyphs (🔫 Weapons, 🦺 Clothing, 🧪 Consumables).
- **Item Body:** Full display name, programmatic code in gold monospace (`M4A1_DRAGON`), and descriptive lore.
- **Card Footer:** Stacking details (`Stackable (Max: 10)` vs. `Unique Slot`).

### 4.3 Empty State Handling
When a character possesses zero items (or zero items matching the selected category), `EmptyState.vue` renders an armory locker notice:
> *"Your tactical supply locker currently contains zero items. Items acquired through survival matches, rewards, and official airdrops will appear here."*

---

## 5. Security & Isolation Policy

1. **Strict Ownership Scoping:** `GET /character/inventory` derives the target character GID solely from the authenticated caller's account ID. A player cannot supply another player's GID or access other lockers.
2. **Read-Only Posture:** The web client contains no endpoints or UI elements for granting, deleting, equipping, or transferring items.
3. **No Asset Piracy:** All icons and cards utilize project-original tactical typography and standard Unicode glyphs; no copyrighted binaries or image assets were extracted from the original IPA archive.
