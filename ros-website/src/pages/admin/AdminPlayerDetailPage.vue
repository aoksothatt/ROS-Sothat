<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { adminService } from '@/services/admin';
import type { AdminPlayerDetail, CatalogItem } from '@/types/admin';
import AdminLayout from '@/components/admin/AdminLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const route = useRoute();
const authStore = useAuthStore();

const playerId = computed(() => Number(route.params.id));
const player = ref<AdminPlayerDetail | null>(null);
const catalog = ref<CatalogItem[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Active Tab
const activeTab = ref<'diamonds' | 'inventory' | 'history' | 'audit'>('diamonds');

// Diamond Form State
const diamondOp = ref<'GRANT' | 'DEDUCT'>('GRANT');
const diamondAmount = ref<number>(100);
const diamondReason = ref<string>('');
const diamondLoading = ref(false);
const diamondError = ref<string | null>(null);
const diamondSuccess = ref<string | null>(null);

// Inventory Form State
const selectedCatalogItemId = ref<number | ''>('');
const inventoryQuantity = ref<number>(1);
const inventoryGrantReason = ref<string>('');
const inventoryLoading = ref(false);
const inventoryError = ref<string | null>(null);
const inventorySuccess = ref<string | null>(null);

// Inventory Removal Modal
const removeModalOpen = ref(false);
const itemToRemove = ref<any>(null);
const removeReason = ref('');
const removeQuantity = ref(1);

// Account Moderation Modal
const moderationModalOpen = ref(false);
const moderationAction = ref<'suspend' | 'reactivate'>('suspend');
const moderationReason = ref('');
const moderationLoading = ref(false);
const moderationError = ref<string | null>(null);

function generateIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

async function loadPlayerData() {
  if (!authStore.token || isNaN(playerId.value)) return;
  loading.value = true;
  error.value = null;
  try {
    player.value = await adminService.getPlayerDetail(authStore.token, playerId.value);
    // Load catalog items in background for grant dropdown
    catalog.value = await adminService.listCatalogItems(authStore.token, { is_active: true, limit: 100 });
  } catch (err: any) {
    error.value = err.message || 'Failed to load player details.';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadPlayerData();
});

// Computed Preview for Diamonds
const expectedResultingBalance = computed(() => {
  const current = player.value?.character?.diamonds ?? 0;
  const amt = Number(diamondAmount.value) || 0;
  if (diamondOp.value === 'GRANT') {
    return current + amt;
  } else {
    return Math.max(0, current - amt);
  }
});

// Execute Diamond Mutation
async function handleDiamondSubmit() {
  if (!authStore.token || !player.value) return;
  if (!diamondAmount.value || diamondAmount.value <= 0) {
    diamondError.value = 'Amount must be a positive integer greater than zero.';
    return;
  }
  if (!diamondReason.value.trim()) {
    diamondError.value = 'Please specify an operational reason for this diamond adjustment.';
    return;
  }

  diamondLoading.value = true;
  diamondError.value = null;
  diamondSuccess.value = null;

  try {
    const key = generateIdempotencyKey(diamondOp.value.toLowerCase());
    if (diamondOp.value === 'GRANT') {
      await adminService.grantDiamonds(authStore.token, player.value.account_id, {
        amount: Math.floor(diamondAmount.value),
        reason: diamondReason.value.trim(),
        idempotency_key: key
      });
      diamondSuccess.value = `Successfully granted ${diamondAmount.value.toLocaleString()} diamonds.`;
    } else {
      await adminService.deductDiamonds(authStore.token, player.value.account_id, {
        amount: Math.floor(diamondAmount.value),
        reason: diamondReason.value.trim(),
        idempotency_key: key
      });
      diamondSuccess.value = `Successfully deducted ${diamondAmount.value.toLocaleString()} diamonds.`;
    }
    diamondReason.value = '';
    await loadPlayerData();
  } catch (err: any) {
    diamondError.value = err.message || 'Diamond operation failed.';
  } finally {
    diamondLoading.value = false;
  }
}

// Execute Inventory Grant
async function handleInventoryGrant() {
  if (!authStore.token || !player.value || !selectedCatalogItemId.value) {
    inventoryError.value = 'Please select a catalog item to grant.';
    return;
  }
  if (!inventoryGrantReason.value.trim()) {
    inventoryError.value = 'A valid operational reason is required for item grants.';
    return;
  }

  inventoryLoading.value = true;
  inventoryError.value = null;
  inventorySuccess.value = null;

  try {
    const key = generateIdempotencyKey('inv-grant');
    await adminService.grantInventory(authStore.token, player.value.account_id, {
      item_id: Number(selectedCatalogItemId.value),
      quantity: Math.max(1, Math.floor(inventoryQuantity.value)),
      reason: inventoryGrantReason.value.trim(),
      idempotency_key: key
    });
    inventorySuccess.value = 'Item granted successfully to player inventory.';
    inventoryGrantReason.value = '';
    await loadPlayerData();
  } catch (err: any) {
    inventoryError.value = err.message || 'Inventory grant failed.';
  } finally {
    inventoryLoading.value = false;
  }
}

// Open Remove Modal
function openRemoveItemModal(item: any) {
  itemToRemove.value = item;
  removeQuantity.value = 1;
  removeReason.value = '';
  inventoryError.value = null;
  removeModalOpen.value = true;
}

async function confirmRemoveItem() {
  if (!authStore.token || !player.value || !itemToRemove.value) return;
  if (!removeReason.value.trim()) {
    inventoryError.value = 'Reason is mandatory for inventory removal.';
    return;
  }

  inventoryLoading.value = true;
  inventoryError.value = null;
  inventorySuccess.value = null;

  try {
    const key = generateIdempotencyKey('inv-rem');
    await adminService.removeInventory(authStore.token, player.value.account_id, {
      item_id: itemToRemove.value.item_id,
      quantity: Math.min(itemToRemove.value.quantity, Math.max(1, Math.floor(removeQuantity.value))),
      reason: removeReason.value.trim(),
      idempotency_key: key
    });
    removeModalOpen.value = false;
    inventorySuccess.value = `Removed ${itemToRemove.value.item_name} safely from inventory.`;
    await loadPlayerData();
  } catch (err: any) {
    inventoryError.value = err.message || 'Failed to remove item.';
  } finally {
    inventoryLoading.value = false;
  }
}

// Moderation Handling
function openModerationModal(action: 'suspend' | 'reactivate') {
  moderationAction.value = action;
  moderationReason.value = action === 'suspend' ? '' : 'Account appeal approved after review';
  moderationError.value = null;
  moderationModalOpen.value = true;
}

async function submitModeration() {
  if (!authStore.token || !player.value) return;
  if (!moderationReason.value.trim()) {
    moderationError.value = 'Reason is mandatory.';
    return;
  }

  moderationLoading.value = true;
  moderationError.value = null;
  try {
    if (moderationAction.value === 'suspend') {
      await adminService.suspendPlayer(authStore.token, player.value.account_id, {
        reason: moderationReason.value.trim()
      });
    } else {
      await adminService.reactivatePlayer(authStore.token, player.value.account_id, {
        reason: moderationReason.value.trim()
      });
    }
    moderationModalOpen.value = false;
    await loadPlayerData();
  } catch (err: any) {
    moderationError.value = err.message || 'Moderation action failed.';
  } finally {
    moderationLoading.value = false;
  }
}

function formatTime(isoStr?: string | null): string {
  if (!isoStr) return 'Never';
  try {
    return new Date(isoStr).toLocaleString();
  } catch {
    return isoStr;
  }
}
</script>

<template>
  <AdminLayout
    :title="player ? `Player Inspection: ${player.username}` : 'Player Inspection'"
    subtitle="Account telemetry, atomic diamond management, inventory curation, and audit records"
  >
    <div class="mb-3">
      <RouterLink to="/admin/players" class="back-link">← Return to Players Directory</RouterLink>
    </div>

    <div v-if="error" class="alert alert-danger mb-4">
      <span>{{ error }}</span>
      <button class="btn btn-secondary btn-sm" @click="loadPlayerData">Retry</button>
    </div>

    <LoadingState v-if="loading" message="Loading player account and character records..." />

    <div v-else-if="player" class="player-detail-wrapper">
      <!-- Player Header Card -->
      <div class="card player-hero-card mb-4">
        <div class="hero-left">
          <div class="hero-avatar">
            <span>{{ player.username.slice(0, 2).toUpperCase() }}</span>
          </div>
          <div class="hero-info">
            <div class="hero-title-row">
              <h2 class="hero-username">{{ player.username }}</h2>
              <span class="badge" :class="player.role === 'admin' ? 'badge-dev' : 'badge-player'">
                {{ player.role.toUpperCase() }}
              </span>
              <span v-if="player.is_banned" class="status-pill status-banned">SUSPENDED</span>
              <span v-else class="status-pill status-active">ACTIVE</span>
            </div>

            <div class="hero-meta-row">
              <span>Account ID: <strong>#{{ player.account_id }}</strong></span>
              <span>Email: <strong>{{ player.email || 'Not verified' }}</strong></span>
              <span>Joined: <strong>{{ formatTime(player.created_at) }}</strong></span>
              <span>Last Login: <strong>{{ formatTime(player.last_login) }}</strong></span>
            </div>

            <div v-if="player.is_banned" class="ban-banner">
              ⚠️ Suspended Reason: <em>{{ player.ban_reason || 'No specific reason provided' }}</em>
            </div>
          </div>
        </div>

        <div class="hero-right">
          <button
            v-if="!player.is_banned && player.role !== 'admin'"
            class="btn btn-danger"
            @click="openModerationModal('suspend')"
          >
            Suspend Account
          </button>
          <button
            v-else-if="player.is_banned"
            class="btn btn-primary"
            @click="openModerationModal('reactivate')"
          >
            Reactivate Account
          </button>
        </div>
      </div>

      <!-- Character Card Summary (if character created) -->
      <div v-if="player.character" class="card char-summary-card mb-4">
        <div class="char-stat">
          <span class="stat-label">CHARACTER NICKNAME</span>
          <span class="stat-value text-primary font-bold">{{ player.character.nickname }}</span>
        </div>
        <div class="char-stat">
          <span class="stat-label">CHARACTER GID</span>
          <span class="stat-value font-mono">#{{ player.character.gid }}</span>
        </div>
        <div class="char-stat">
          <span class="stat-label">LEVEL / EXP</span>
          <span class="stat-value">Lv.{{ player.character.level }} ({{ player.character.exp }} EXP)</span>
        </div>
        <div class="char-stat">
          <span class="stat-label">DIAMOND BALANCE</span>
          <span class="stat-value text-gold font-bold">💎 {{ player.character.diamonds.toLocaleString() }}</span>
        </div>
        <div class="char-stat">
          <span class="stat-label">GOLD RESERVES</span>
          <span class="stat-value">🪙 {{ player.character.gold.toLocaleString() }}</span>
        </div>
      </div>

      <div v-else class="card p-4 mb-4">
        <EmptyState
          title="No Character Profile Found"
          description="This player has registered their account but has not yet created an in-game character profile."
          icon="🎮"
        />
      </div>

      <!-- Interactive Tabs -->
      <div v-if="player.character" class="tabs-nav mb-4">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'diamonds' }"
          @click="activeTab = 'diamonds'"
        >
          💎 Diamond Management
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'inventory' }"
          @click="activeTab = 'inventory'"
        >
          🎒 Player Inventory ({{ player.inventory_items.length }})
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'history' }"
          @click="activeTab = 'history'"
        >
          📜 Diamond Ledger History
        </button>
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'audit' }"
          @click="activeTab = 'audit'"
        >
          🛡️ Admin Action Audits
        </button>
      </div>

      <!-- Tab 1: Diamond Management -->
      <div v-if="activeTab === 'diamonds' && player.character" class="card tab-content-card">
        <h3 class="section-title">ATOMIC DIAMOND LEDGER ADJUSTMENT</h3>
        <p class="section-desc">
          Execute atomic grants or deductions directly against the player's character ledger. All changes are enforced with transactional row updates, check constraints, and immutable audit logs.
        </p>

        <div v-if="diamondError" class="alert alert-danger mb-3">{{ diamondError }}</div>
        <div v-if="diamondSuccess" class="alert alert-success mb-3">{{ diamondSuccess }}</div>

        <form class="mutation-form" @submit.prevent="handleDiamondSubmit">
          <div class="form-row">
            <div class="form-group flex-1">
              <label class="form-label">Operation Type</label>
              <div class="radio-pill-group">
                <button
                  type="button"
                  class="radio-pill"
                  :class="{ active: diamondOp === 'GRANT' }"
                  @click="diamondOp = 'GRANT'"
                >
                  ➕ Grant Diamonds
                </button>
                <button
                  type="button"
                  class="radio-pill radio-pill-danger"
                  :class="{ active: diamondOp === 'DEDUCT' }"
                  @click="diamondOp = 'DEDUCT'"
                >
                  ➖ Deduct Diamonds
                </button>
              </div>
            </div>

            <div class="form-group flex-1">
              <label class="form-label">Diamond Amount *</label>
              <input
                v-model.number="diamondAmount"
                type="number"
                min="1"
                max="10000000"
                class="form-input"
                required
              />
            </div>
          </div>

          <!-- Balance Calculation Live Preview -->
          <div class="balance-preview-box mb-3">
            <div class="preview-item">
              <span class="preview-label">CURRENT BALANCE:</span>
              <span class="preview-val">💎 {{ player.character.diamonds.toLocaleString() }}</span>
            </div>
            <div class="preview-arrow">➔</div>
            <div class="preview-item">
              <span class="preview-label">OPERATION:</span>
              <span :class="diamondOp === 'GRANT' ? 'text-success' : 'text-danger'">
                {{ diamondOp === 'GRANT' ? '+' : '-' }}{{ (diamondAmount || 0).toLocaleString() }}
              </span>
            </div>
            <div class="preview-arrow">➔</div>
            <div class="preview-item">
              <span class="preview-label">EXPECTED RESULT:</span>
              <span class="preview-val text-gold font-bold">
                💎 {{ expectedResultingBalance.toLocaleString() }}
              </span>
            </div>
          </div>

          <div class="form-group mb-3">
            <label class="form-label">Operational Reason (Required for Audit Trail) *</label>
            <input
              v-model="diamondReason"
              type="text"
              class="form-input"
              maxlength="255"
              placeholder="e.g., Bug bounty reward or Tournament adjustment"
              required
            />
          </div>

          <button
            type="submit"
            class="btn"
            :class="diamondOp === 'GRANT' ? 'btn-primary' : 'btn-danger'"
            :disabled="diamondLoading || !diamondAmount || diamondAmount <= 0 || !diamondReason.trim()"
          >
            <span v-if="diamondLoading">Executing Transaction...</span>
            <span v-else>{{ diamondOp === 'GRANT' ? 'Confirm & Grant Diamonds' : 'Confirm & Deduct Diamonds' }}</span>
          </button>
        </form>
      </div>

      <!-- Tab 2: Inventory Management -->
      <div v-if="activeTab === 'inventory' && player.character" class="tab-content-wrapper">
        <!-- Grant New Item Card -->
        <div class="card p-4 mb-4">
          <h3 class="section-title">GRANT CATALOG ITEM TO INVENTORY</h3>
          <div v-if="inventoryError" class="alert alert-danger mb-3">{{ inventoryError }}</div>
          <div v-if="inventorySuccess" class="alert alert-success mb-3">{{ inventorySuccess }}</div>

          <form class="inventory-grant-form" @submit.prevent="handleInventoryGrant">
            <div class="form-row">
              <div class="form-group flex-2">
                <label class="form-label">Select Active Catalog Item *</label>
                <select v-model="selectedCatalogItemId" class="form-input" required>
                  <option value="" disabled>-- Select Catalog Item --</option>
                  <option v-for="it in catalog" :key="it.id" :value="it.id">
                    {{ it.name }} ({{ it.item_type }}) — Code: {{ it.item_code }} [Max Stack: {{ it.max_stack }}]
                  </option>
                </select>
              </div>

              <div class="form-group flex-1">
                <label class="form-label">Quantity</label>
                <input
                  v-model.number="inventoryQuantity"
                  type="number"
                  min="1"
                  max="999"
                  class="form-input"
                  required
                />
              </div>
            </div>

            <div class="form-group mb-3">
              <label class="form-label">Grant Reason *</label>
              <input
                v-model="inventoryGrantReason"
                type="text"
                class="form-input"
                maxlength="255"
                placeholder="e.g., Special event participation reward"
                required
              />
            </div>

            <button
              type="submit"
              class="btn btn-primary"
              :disabled="inventoryLoading || !selectedCatalogItemId || !inventoryGrantReason.trim()"
            >
              <span v-if="inventoryLoading">Granting Item...</span>
              <span v-else>Grant Item to Player</span>
            </button>
          </form>
        </div>

        <!-- Current Inventory Table -->
        <div class="card table-card">
          <div class="card-header">
            <h3 class="card-title">CURRENT PLAYER INVENTORY SLOTS</h3>
          </div>

          <div v-if="player.inventory_items.length === 0" class="p-4">
            <EmptyState
              title="Inventory is Empty"
              description="This character does not currently hold any inventory items in their storage."
              icon="🎒"
            />
          </div>

          <div v-else class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Slot ID</th>
                  <th>Item Name</th>
                  <th>Item Type</th>
                  <th>Quantity</th>
                  <th>Stackable</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in player.inventory_items" :key="item.id">
                  <td class="font-mono text-muted text-sm">#{{ item.id }}</td>
                  <td class="font-bold text-white">{{ item.item_name }}</td>
                  <td>
                    <span class="badge badge-player">{{ item.item_type }}</span>
                  </td>
                  <td class="font-bold text-primary font-mono">x{{ item.quantity }}</td>
                  <td class="text-xs text-muted">{{ item.stackable ? `Yes (Max ${item.max_stack})` : 'No (Single)' }}</td>
                  <td>
                    <button class="btn btn-danger btn-sm" @click="openRemoveItemModal(item)">
                      Remove Item
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tab 3: Diamond History -->
      <div v-if="activeTab === 'history' && player.character" class="card table-card">
        <div class="card-header">
          <h3 class="card-title">DIAMOND TRANSACTION LEDGER</h3>
        </div>

        <div v-if="player.recent_diamond_transactions.length === 0" class="p-4">
          <EmptyState
            title="No Diamond Transactions"
            description="No transactions have been recorded on this character's diamond ledger."
            icon="💎"
          />
        </div>

        <div v-else class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tx ID</th>
                <th>Operation</th>
                <th>Amount</th>
                <th>Balance Before</th>
                <th>Balance After</th>
                <th>Reason</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tx in player.recent_diamond_transactions" :key="tx.id">
                <td class="font-mono text-muted text-sm">#{{ tx.id }}</td>
                <td>
                  <span
                    class="action-badge"
                    :class="tx.operation_type === 'GRANT' ? 'diamond_grant' : 'diamond_deduct'"
                  >
                    {{ tx.operation_type }}
                  </span>
                </td>
                <td class="font-mono font-bold" :class="tx.operation_type === 'GRANT' ? 'text-success' : 'text-danger'">
                  {{ tx.operation_type === 'GRANT' ? '+' : '-' }}{{ tx.amount.toLocaleString() }}
                </td>
                <td class="font-mono text-muted">💎 {{ tx.balance_before.toLocaleString() }}</td>
                <td class="font-mono font-bold text-gold">💎 {{ tx.balance_after.toLocaleString() }}</td>
                <td class="text-sm">{{ tx.reason }}</td>
                <td class="text-muted text-xs">{{ formatTime(tx.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab 4: Audit Logs -->
      <div v-if="activeTab === 'audit' && player.character" class="card table-card">
        <div class="card-header">
          <h3 class="card-title">ADMINISTRATIVE ACTION AUDIT TRAIL</h3>
        </div>

        <div v-if="player.recent_audit_logs.length === 0" class="p-4">
          <EmptyState
            title="No Audit Records"
            description="No administrative actions targeting this player account have been executed yet."
            icon="📜"
          />
        </div>

        <div v-else class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Audit ID</th>
                <th>Action Type</th>
                <th>Admin Actor</th>
                <th>Reason</th>
                <th>Details</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in player.recent_audit_logs" :key="log.id">
                <td class="font-mono text-muted text-sm">#{{ log.id }}</td>
                <td>
                  <span class="action-badge" :class="log.action_type.toLowerCase()">
                    {{ log.action_type }}
                  </span>
                </td>
                <td class="font-bold text-admin">
                  {{ log.admin_username || `Admin #${log.admin_account_id}` }}
                </td>
                <td class="text-sm">{{ log.reason }}</td>
                <td class="text-xs font-mono text-muted">
                  {{ JSON.stringify(log.details) }}
                </td>
                <td class="text-muted text-xs">{{ formatTime(log.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Inventory Removal Modal -->
    <div v-if="removeModalOpen" class="modal-backdrop" @click.self="removeModalOpen = false">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3 class="modal-title">Remove Item from Player</h3>
          <button class="modal-close" @click="removeModalOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <p class="modal-desc">
            Removing <strong>{{ itemToRemove?.item_name }}</strong> from <strong>{{ player?.username }}</strong>.
          </p>

          <div class="warning-box mb-3">
            ⚠️ If this clothing or skin is currently equipped by the character, it will be automatically safely unequipped to prevent broken appearance states.
          </div>

          <div class="form-group mb-3">
            <label class="form-label">Quantity to Remove (Max: {{ itemToRemove?.quantity }})</label>
            <input
              v-model.number="removeQuantity"
              type="number"
              min="1"
              :max="itemToRemove?.quantity || 1"
              class="form-input"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label">Reason for Removal *</label>
            <input
              v-model="removeReason"
              type="text"
              class="form-input"
              maxlength="255"
              placeholder="e.g., Duplication exploit correction"
              required
            />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" :disabled="inventoryLoading" @click="removeModalOpen = false">
            Cancel
          </button>
          <button
            class="btn btn-danger"
            :disabled="inventoryLoading || !removeReason.trim()"
            @click="confirmRemoveItem"
          >
            <span v-if="inventoryLoading">Removing...</span>
            <span v-else>Confirm Removal</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Account Moderation Modal -->
    <div v-if="moderationModalOpen" class="modal-backdrop" @click.self="moderationModalOpen = false">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ moderationAction === 'suspend' ? 'Suspend Player Account' : 'Reactivate Player Account' }}
          </h3>
          <button class="modal-close" @click="moderationModalOpen = false">✕</button>
        </div>
        <div class="modal-body">
          <div v-if="moderationError" class="alert alert-danger mb-3">{{ moderationError }}</div>
          <p class="modal-desc">
            Target: <strong>{{ player?.username }}</strong> (Account #{{ player?.account_id }})
          </p>

          <div class="form-group">
            <label class="form-label">Reason *</label>
            <input
              v-model="moderationReason"
              type="text"
              class="form-input"
              maxlength="255"
              required
            />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" :disabled="moderationLoading" @click="moderationModalOpen = false">
            Cancel
          </button>
          <button
            class="btn"
            :class="moderationAction === 'suspend' ? 'btn-danger' : 'btn-primary'"
            :disabled="moderationLoading || !moderationReason.trim()"
            @click="submitModeration"
          >
            <span v-if="moderationLoading">Processing...</span>
            <span v-else>{{ moderationAction === 'suspend' ? 'Confirm Suspension' : 'Confirm Reactivation' }}</span>
          </button>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.mb-3 { margin-bottom: 1rem; }
.mb-4 { margin-bottom: 1.5rem; }
.p-4 { padding: 1.5rem; }

.back-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 700;
}
.back-link:hover { text-decoration: underline; }

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.player-hero-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  gap: 1.5rem;
}

.hero-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.hero-avatar {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(0, 204, 136, 0.2), rgba(0, 102, 255, 0.2));
  border: 1px solid var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  font-size: 1.4rem;
  color: var(--color-primary);
}

.hero-info {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.hero-username {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
  color: #fff;
}

.hero-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.hero-meta-row strong {
  color: #ddd;
}

.ban-banner {
  margin-top: 0.4rem;
  background: rgba(255, 77, 77, 0.1);
  border: 1px solid rgba(255, 77, 77, 0.3);
  color: #ff9999;
  font-size: 0.8rem;
  padding: 0.4rem 0.65rem;
  border-radius: 4px;
}

.char-summary-card {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  padding: 1.25rem;
  gap: 1rem;
  background: var(--bg-secondary);
}

.char-stat {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-size: 0.65rem;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 0.08em;
}

.stat-value {
  font-size: 1rem;
  color: #fff;
}

.tabs-nav {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
  overflow-x: auto;
}

.tab-btn {
  background: none;
  border: 1px solid transparent;
  padding: 0.65rem 1rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-muted);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.04);
}

.tab-btn.active {
  background: rgba(255, 180, 0, 0.12);
  color: #ffb400;
  border-color: rgba(255, 180, 0, 0.3);
}

.tab-content-card {
  padding: 1.5rem;
}

.section-title {
  margin: 0 0 0.4rem 0;
  font-size: 1rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.05em;
}

.section-desc {
  margin: 0 0 1.25rem 0;
  font-size: 0.85rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.form-row {
  display: flex;
  gap: 1.25rem;
  margin-bottom: 1rem;
}

.flex-1 { flex: 1; }
.flex-2 { flex: 2; }

.radio-pill-group {
  display: flex;
  gap: 0.5rem;
}

.radio-pill {
  flex: 1;
  padding: 0.7rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-muted);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
}

.radio-pill.active {
  background: rgba(0, 204, 136, 0.15);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.radio-pill-danger.active {
  background: rgba(255, 77, 77, 0.15);
  border-color: #ff4d4d;
  color: #ff4d4d;
}

.form-input {
  width: 100%;
  padding: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: #fff;
  font-size: 0.9rem;
}

.balance-preview-box {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0.85rem 1rem;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.preview-label {
  font-size: 0.65rem;
  font-weight: 800;
  color: var(--text-muted);
}

.preview-val {
  font-size: 1rem;
  font-family: monospace;
}

.preview-arrow {
  color: var(--text-muted);
  font-size: 1.2rem;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.data-table th {
  background: rgba(255, 255, 255, 0.02);
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 0.85rem 1.25rem;
  border-bottom: 1px solid var(--border-color);
}

.data-table td {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-color);
  font-size: 0.85rem;
  vertical-align: middle;
}

.text-gold { color: #ffb400; }
.text-success { color: #00cc88; }
.text-danger { color: #ff4d4d; }
.text-admin { color: #ffb400; }
.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.text-xs { font-size: 0.75rem; }
.text-sm { font-size: 0.85rem; }

.status-pill {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.status-active {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
  border: 1px solid rgba(0, 204, 136, 0.3);
}

.status-banned {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
  border: 1px solid rgba(255, 77, 77, 0.3);
}

.action-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.action-badge.diamond_grant {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
}

.action-badge.diamond_deduct {
  background: rgba(255, 180, 0, 0.15);
  color: #ffb400;
}

.badge-dev {
  background: rgba(255, 180, 0, 0.15);
  color: #ffb400;
  border: 1px solid rgba(255, 180, 0, 0.3);
}

.badge-player {
  background: rgba(255, 255, 255, 0.08);
  color: #ccc;
  border: 1px solid var(--border-color);
}

/* Modal */
.modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
}

.modal-dialog {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  width: 100%;
  max-width: 520px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.modal-title { margin: 0; font-size: 1.1rem; font-weight: 800; color: #fff; }
.modal-close { background: none; border: none; color: var(--text-muted); font-size: 1.25rem; cursor: pointer; }
.modal-body { padding: 1.5rem; }
.modal-desc { margin: 0 0 1rem 0; font-size: 0.9rem; color: #ccc; }
.warning-box {
  background: rgba(255, 77, 77, 0.1);
  border: 1px solid rgba(255, 77, 77, 0.3);
  padding: 0.85rem;
  border-radius: 6px;
  color: #ff9999;
  font-size: 0.8rem;
  line-height: 1.4;
}
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.2);
}

@media (max-width: 900px) {
  .player-hero-card { flex-direction: column; align-items: flex-start; }
  .char-summary-card { grid-template-columns: repeat(2, 1fr); }
  .form-row { flex-direction: column; }
}

@media (max-width: 600px) {
  .char-summary-card { grid-template-columns: 1fr; }
  .balance-preview-box { flex-direction: column; gap: 0.5rem; }
  .preview-arrow { display: none; }
}
</style>
