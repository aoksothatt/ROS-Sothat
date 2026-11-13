<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { adminService } from '@/services/admin';
import type { CatalogItem, AdminPlayerSummary, AdminAuditLog } from '@/types/admin';
import AdminLayout from '@/components/admin/AdminLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const catalog = ref<CatalogItem[]>([]);
const players = ref<AdminPlayerSummary[]>([]);
const recentInvLogs = ref<AdminAuditLog[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Filter
const typeFilter = ref<string>('all');

// Grant Modal State
const grantModalOpen = ref(false);
const selectedItem = ref<CatalogItem | null>(null);
const targetPlayerId = ref<number | ''>('');
const grantQuantity = ref(1);
const grantReason = ref('');
const grantLoading = ref(false);
const grantError = ref<string | null>(null);
const grantSuccess = ref<string | null>(null);

function generateIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

async function loadData() {
  if (!authStore.token) return;
  loading.value = true;
  error.value = null;
  try {
    catalog.value = await adminService.listCatalogItems(authStore.token, { limit: 100 });
    const pResp = await adminService.listPlayers(authStore.token, { limit: 100 });
    players.value = pResp.players.filter(p => p.character_gid !== null);

    const logResp = await adminService.listAuditLogs(authStore.token, { limit: 50 });
    recentInvLogs.value = logResp.logs.filter(l =>
      l.action_type === 'INVENTORY_GRANT' || l.action_type === 'INVENTORY_REMOVE'
    );
  } catch (err: any) {
    error.value = err.message || 'Failed to load inventory data.';
  } finally {
    loading.value = false;
  }
}

const filteredCatalog = () => {
  if (typeFilter.value === 'all') return catalog.value;
  return catalog.value.filter(it => it.item_type.toLowerCase() === typeFilter.value.toLowerCase());
};

function openGrantModal(item: CatalogItem) {
  selectedItem.value = item;
  targetPlayerId.value = '';
  grantQuantity.value = 1;
  grantReason.value = '';
  grantError.value = null;
  grantSuccess.value = null;
  grantModalOpen.value = true;
}

function closeGrantModal() {
  grantModalOpen.value = false;
  selectedItem.value = null;
}

async function submitGrant() {
  if (!authStore.token || !selectedItem.value || !targetPlayerId.value) {
    grantError.value = 'Please select a player character.';
    return;
  }
  if (!grantReason.value.trim()) {
    grantError.value = 'Operational reason is required.';
    return;
  }

  grantLoading.value = true;
  grantError.value = null;
  try {
    const key = generateIdempotencyKey('cat-grant');
    await adminService.grantInventory(authStore.token, Number(targetPlayerId.value), {
      item_id: selectedItem.value.id,
      quantity: Math.max(1, Math.floor(grantQuantity.value)),
      reason: grantReason.value.trim(),
      idempotency_key: key
    });
    grantSuccess.value = `Successfully granted ${grantQuantity.value}x ${selectedItem.value.name}.`;
    setTimeout(() => {
      closeGrantModal();
      loadData();
    }, 1200);
  } catch (err: any) {
    grantError.value = err.message || 'Grant operation failed.';
  } finally {
    grantLoading.value = false;
  }
}

function formatTime(isoStr: string): string {
  try {
    return new Date(isoStr).toLocaleString();
  } catch {
    return isoStr;
  }
}

onMounted(() => {
  loadData();
});
</script>

<template>
  <AdminLayout
    title="Item Catalog & Inventory Curation"
    subtitle="Inspect items, verify stackability rules, and execute administrative item grants"
  >
    <div v-if="error" class="alert alert-danger mb-4">
      <span>{{ error }}</span>
      <button class="btn btn-secondary btn-sm" @click="loadData">Retry</button>
    </div>

    <!-- Filter Bar -->
    <div class="filter-card card mb-4">
      <div class="filter-group">
        <span class="filter-label">Filter by Type:</span>
        <button
          class="filter-pill"
          :class="{ active: typeFilter === 'all' }"
          @click="typeFilter = 'all'"
        >
          All Items ({{ catalog.length }})
        </button>
        <button
          class="filter-pill"
          :class="{ active: typeFilter === 'clothing' }"
          @click="typeFilter = 'clothing'"
        >
          Clothing
        </button>
        <button
          class="filter-pill"
          :class="{ active: typeFilter === 'skin' }"
          @click="typeFilter = 'skin'"
        >
          Weapon Skins
        </button>
        <button
          class="filter-pill"
          :class="{ active: typeFilter === 'consumable' }"
          @click="typeFilter = 'consumable'"
        >
          Consumables
        </button>
      </div>
    </div>

    <LoadingState v-if="loading" message="Loading catalog items..." />

    <!-- Catalog Items Table -->
    <div v-else-if="filteredCatalog().length === 0" class="card p-4 mb-4">
      <EmptyState
        title="No Catalog Items"
        description="No items found matching the selected filter criteria."
        icon="🎒"
      />
    </div>

    <div v-else class="card table-card mb-4">
      <div class="card-header">
        <h3 class="card-title">SERVER RELATIONAL ITEM CATALOG</h3>
      </div>
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Item Code</th>
              <th>Name & Description</th>
              <th>Category</th>
              <th>Stacking Limit</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="it in filteredCatalog()" :key="it.id">
              <td class="font-mono text-muted text-sm">#{{ it.id }}</td>
              <td class="font-mono font-bold text-white">{{ it.item_code }}</td>
              <td>
                <div class="item-name-col">
                  <span class="font-bold text-white">{{ it.name }}</span>
                  <span class="text-xs text-muted">{{ it.description || 'No description provided' }}</span>
                </div>
              </td>
              <td>
                <span class="badge badge-player">{{ it.item_type }}</span>
              </td>
              <td class="text-sm">
                <span v-if="it.stackable" class="text-success font-bold">Stackable (Max {{ it.max_stack }})</span>
                <span v-else class="text-muted">Unique (1)</span>
              </td>
              <td>
                <span v-if="it.is_active" class="status-pill status-active">ACTIVE</span>
                <span v-else class="status-pill status-banned">INACTIVE</span>
              </td>
              <td>
                <button
                  class="btn btn-primary btn-sm"
                  :disabled="!it.is_active"
                  @click="openGrantModal(it)"
                >
                  Grant to Player
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Recent Inventory Logs -->
    <div class="card table-card">
      <div class="card-header">
        <h3 class="card-title">RECENT INVENTORY AUDIT RECORDS</h3>
      </div>
      <div v-if="recentInvLogs.length === 0" class="p-4">
        <EmptyState
          title="No Inventory Logs"
          description="Administrative item grants and removals will appear here."
          icon="📜"
        />
      </div>
      <div v-else class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Log ID</th>
              <th>Action</th>
              <th>Target Character</th>
              <th>Admin Actor</th>
              <th>Item & Quantity</th>
              <th>Reason</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in recentInvLogs" :key="l.id">
              <td class="font-mono text-muted text-sm">#{{ l.id }}</td>
              <td>
                <span class="action-badge" :class="l.action_type.toLowerCase()">
                  {{ l.action_type }}
                </span>
              </td>
              <td>
                <span class="target-badge">Char GID: #{{ l.target_id }}</span>
              </td>
              <td class="font-bold text-admin">
                {{ l.admin_username || `Admin #${l.admin_account_id}` }}
              </td>
              <td>
                <span class="font-bold text-white">{{ l.details?.item_name || `Item #${l.details?.item_id}` }}</span>
                <span class="text-xs text-primary font-mono font-bold"> (x{{ l.details?.quantity || 1 }})</span>
              </td>
              <td class="text-sm">{{ l.reason }}</td>
              <td class="text-muted text-xs">{{ formatTime(l.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Grant Item Modal -->
    <div v-if="grantModalOpen" class="modal-backdrop" @click.self="closeGrantModal">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3 class="modal-title">Grant Item: {{ selectedItem?.name }}</h3>
          <button class="modal-close" @click="closeGrantModal">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="grantError" class="alert alert-danger mb-3">{{ grantError }}</div>
          <div v-if="grantSuccess" class="alert alert-success mb-3">{{ grantSuccess }}</div>

          <div class="form-group mb-3">
            <label class="form-label">Recipient Player Character *</label>
            <select v-model="targetPlayerId" class="form-input" required>
              <option value="" disabled>-- Select Character --</option>
              <option v-for="p in players" :key="p.account_id" :value="p.account_id">
                {{ p.character_nickname }} ({{ p.username }}) — Level {{ p.character_level || 1 }}
              </option>
            </select>
          </div>

          <div class="form-group mb-3">
            <label class="form-label">Quantity (Max Stack: {{ selectedItem?.max_stack }})</label>
            <input
              v-model.number="grantQuantity"
              type="number"
              min="1"
              :max="selectedItem?.max_stack || 1"
              class="form-input"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label">Grant Reason *</label>
            <input
              v-model="grantReason"
              type="text"
              class="form-input"
              maxlength="255"
              placeholder="e.g., Event prize or compensation"
              required
            />
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" :disabled="grantLoading" @click="closeGrantModal">
            Cancel
          </button>
          <button
            class="btn btn-primary"
            :disabled="grantLoading || !targetPlayerId || !grantReason.trim()"
            @click="submitGrant"
          >
            <span v-if="grantLoading">Granting...</span>
            <span v-else>Confirm Grant</span>
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

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.table-card { overflow: hidden; }

.card-header {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.card-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #fff;
}

.filter-card {
  padding: 0.85rem 1.25rem;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
}

.filter-pill {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.35rem 0.75rem;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-pill:hover {
  color: #fff;
}

.filter-pill.active {
  background: rgba(255, 180, 0, 0.15);
  border-color: #ffb400;
  color: #ffb400;
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

.item-name-col {
  display: flex;
  flex-direction: column;
}

.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.text-white { color: #fff; }
.text-xs { font-size: 0.75rem; }
.text-sm { font-size: 0.85rem; }
.text-success { color: #00cc88; }
.text-admin { color: #ffb400; }

.status-pill {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 800;
}

.status-active {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
}

.status-banned {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
}

.action-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
}

.action-badge.inventory_grant {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
}

.action-badge.inventory_remove {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
}

.target-badge {
  font-family: monospace;
  background: rgba(0, 0, 0, 0.4);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #ccc;
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

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
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

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border-color);
  background: rgba(0, 0, 0, 0.2);
}
</style>
