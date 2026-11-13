# Phase P04 — Diamond Wallet & Economy Implementation

**Document:** `03_diamond_wallet_implementation.md`  
**Phase:** P04 (Player Dashboard Implementation)  
**Project:** ROS Sothat (Private Rules of Survival Legacy Server Platform)  
**Scope:** Authoritative Diamond Balance, Ledger Tracing & Wallet UI  
**Security Level:** Read-Only Analysis & Isolated Development  

---

## 1. Executive Summary

The Diamond Wallet view ([src/pages/dashboard/WalletPage.vue](file:///D:/ROS-Legacy-Analysis/ros-website/src/pages/dashboard/WalletPage.vue)) provides players with real-time visibility into their authoritative diamond currency reserves and complete audit ledger history.

In strict compliance with project protection rules:
1. The frontend displays only the true balance returned by the backend database.
2. No secondary or independent balance calculation is maintained on the client.
3. No player-facing grant, deduction, purchase, or transfer actions are exposed.
4. An authoritative, read-only endpoint was added to the backend to expose personal transaction logs safely.

---

## 2. Authoritative Source of Truth

The diamond economy is implemented in `ros-private-server/app/economy/`:

### 2.1 Database Entities & Constraints
- **Character Balance (`characters.diamonds`):** A `BigInteger` column initialized to `100` (starter package). Enforces non-negative balances at the database engine level via `CheckConstraint("diamonds >= 0", name="chk_character_diamonds_non_negative")`.
- **Relational Ledger Table (`diamond_transactions`):** An immutable, append-only table recording every modification. Columns include:
  - `id`: Unique transaction identifier
  - `character_gid`: Target character GID
  - `admin_account_id`: Originating operator account
  - `operation_type`: `GRANT` or `DEDUCT`
  - `amount`: Number of diamonds transferred (`amount > 0`)
  - `balance_before`: Verified balance immediately prior to execution
  - `balance_after`: Resulting balance immediately following execution
  - `idempotency_key`: Unique token preventing duplicate transactions
  - `reason`: Audit text explanation
  - `created_at`: UTC timestamp

### 2.2 Atomic Consistency
All balance mutations in `EconomyService` execute inside atomic database transactions (`atomic_grant` / `atomic_deduct`). The character balance and the transaction log record are committed together. If an operation fails, the transaction is completely rolled back.

---

## 3. Backend Read-Only API Integration

To allow players to inspect their personal transaction ledger without exposing administrative endpoints, a minimal read-only route was added to [ros-private-server/app/player/router.py](file:///D:/ROS-Legacy-Analysis/ros-private-server/app/player/router.py):

```python
@router.get("/character/diamonds/history", response_model=DiamondHistoryResponse)
async def get_my_diamond_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_account: Account = Depends(get_current_account),
    player_service: PlayerService = Depends(get_player_service),
    economy_service: EconomyService = Depends(get_economy_service)
):
    """Retrieve the authenticated player's own diamond transaction ledger."""
    char = await player_service.repository.get_by_account_id(current_account.id)
    if not char:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No character found for this account."
        )
    return await economy_service.get_character_history(
        character_gid=char.gid,
        limit=limit,
        offset=offset
    )
```

### Authorization & Scope Verification:
- **Authentication:** Enforced by FastAPI's `Depends(get_current_account)`.
- **Zero Cross-Account Leakage:** The character GID is derived solely from `current_account.id`. Callers cannot pass arbitrary GIDs.
- **Read-Only:** Returns `DiamondHistoryResponse` containing `current_balance`, `total_transactions`, and the list of `transactions`.

---

## 4. Wallet User Interface Design

The Wallet page renders 3 tactical sections:
1. **Currency Reserve Cards:**
   - **Primary Vault:** Displays live authoritative diamond balance (`character.diamonds`) in large gold typography (`--accent-gold`).
   - **Secondary Vault:** Displays character gold balance (`character.gold`).
2. **Security Policy Notice:**
   - Highlights that the private platform maintains an immutable, append-only economy. Self-granting, purchasing, and peer transfers are strictly disabled for player accounts.
3. **Transaction Audit Log Table:**
   - Renders UTC timestamps, operation type badges (`GRANT` in green, `DEDUCT` in red), signed amounts (`+250 💎`, `-50 💎`), balance before/after, and audit justifications.
   - If the player has no transactions, renders `EmptyState.vue` with `"NO TRANSACTIONS LOGGED"`.

---

## 5. Future Game Client Integration Requirement

> [!IMPORTANT]
> **Long-Term Synchronization Architecture:**  
> The long-term economy architecture must preserve one authoritative diamond and inventory system that can eventually be synchronized by the private game server through BaseApp/native Mercury property updates.  
> A database balance alone does not prove that the original iOS game client displays the same balance. BaseApp and CellApp synchronization remain reserved for future engine phases.
