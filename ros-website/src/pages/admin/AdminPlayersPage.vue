<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { adminService } from '@/services/admin';
import type { AdminPlayerSummary } from '@/types/admin';
import AdminLayout from '@/components/admin/AdminLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const players = ref<AdminPlayerSummary[]>([]);
const total = ref(0);
const loading = ref(true);
const error = ref<string | null>(null);

// Filters and Pagination
const searchQuery = ref('');
const statusFilter = ref<'all' | 'active' | 'suspended'>('all');
const page = ref(1);
const limit = 20;

// Modal States
const actionModalOpen = ref(false);
const modalAction = ref<'suspend' | 'reactivate' | null>(null);
const selectedPlayer = ref<AdminPlayerSummary | null>(null);
const actionReason = ref('');
const actionLoading = ref(false);
const actionError = ref<string | null>(null);

async function fetchPlayers() {
  if (!authStore.token) return;
  loading.value = true;
  error.value = null;

  try {
    let isBannedParam: boolean | undefined = undefined;
    if (statusFilter.value === 'active') isBannedParam = false;
    if (statusFilter.value === 'suspended') isBannedParam = true;

    const offset = (page.value - 1) * limit;
    const res = await adminService.listPlayers(authStore.token, {
      q: searchQuery.value,
      is_banned: isBannedParam,
      limit,
      offset
    });
    players.value = res.players;
    total.value = res.total;
  } catch (err: any) {
    error.value = err.message || 'Failed to retrieve player accounts.';
  } finally {
    loading.value = false;
  }
}

watch([statusFilter], () => {
  page.value = 1;
  fetchPlayers();
});

let debounceTimer: any = null;
function handleSearchInput() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    page.value = 1;
    fetchPlayers();
  }, 350);
}

function prevPage() {
  if (page.value > 1) {
    page.value--;
    fetchPlayers();
  }
}

function nextPage() {
  if (page.value * limit < total.value) {
    page.value++;
    fetchPlayers();
  }
}

// Modal handling
function openSuspendModal(player: AdminPlayerSummary) {
  selectedPlayer.value = player;
  modalAction.value = 'suspend';
  actionReason.value = '';
  actionError.value = null;
  actionModalOpen.value = true;
}

function openReactivateModal(player: AdminPlayerSummary) {
  selectedPlayer.value = player;
  modalAction.value = 'reactivate';
  actionReason.value = 'Account appeal approved after review';
  actionError.value = null;
  actionModalOpen.value = true;
}

function closeModal() {
  actionModalOpen.value = false;
  selectedPlayer.value = null;
  modalAction.value = null;
  actionError.value = null;
}

async function submitAction() {
  if (!authStore.token || !selectedPlayer.value || !modalAction.value) return;
  if (!actionReason.value.trim()) {
    actionError.value = 'A valid operational reason is required for moderation actions.';
    return;
  }

  actionLoading.value = true;
  actionError.value = null;
  try {
    if (modalAction.value === 'suspend') {
      await adminService.suspendPlayer(authStore.token, selectedPlayer.value.account_id, {
        reason: actionReason.value.trim()
      });
    } else {
      await adminService.reactivatePlayer(authStore.token, selectedPlayer.value.account_id, {
        reason: actionReason.value.trim()
      });
    }
    closeModal();
    await fetchPlayers();
  } catch (err: any) {
    actionError.value = err.message || 'Action failed.';
  } finally {
    actionLoading.value = false;
  }
}

onMounted(() => {
  fetchPlayers();
});
</script>

<template>
  <AdminLayout
    title="Player Accounts Directory"
    subtitle="Search, audit, inspect characters, and manage player account statuses"
  >
    <div v-if="error" class="alert alert-danger mb-4">
      <span>{{ error }}</span>
      <button class="btn btn-secondary btn-sm" @click="fetchPlayers">Retry</button>
    </div>

    <!-- Filter & Search Toolbar -->
    <div class="toolbar-card card mb-4">
      <div class="toolbar-left">
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Search by username, email, nickname, or ID..."
            @input="handleSearchInput"
          />
          <button v-if="searchQuery" class="clear-btn" @click="searchQuery = ''; fetchPlayers();">✕</button>
        </div>

        <div class="filter-tabs">
          <button
            class="filter-tab"
            :class="{ active: statusFilter === 'all' }"
            @click="statusFilter = 'all'"
          >
            All Players
          </button>
          <button
            class="filter-tab"
            :class="{ active: statusFilter === 'active' }"
            @click="statusFilter = 'active'"
          >
            Active Only
          </button>
          <button
            class="filter-tab"
            :class="{ active: statusFilter === 'suspended' }"
            @click="statusFilter = 'suspended'"
          >
            Suspended
          </button>
        </div>
      </div>

      <div class="toolbar-right">
        <span class="total-indicator">
          Total Players: <strong>{{ total }}</strong>
        </span>
      </div>
    </div>

    <LoadingState v-if="loading" message="Loading player directory..." />

    <div v-else-if="players.length === 0" class="card p-4">
      <EmptyState
        title="No Players Found"
        :description="searchQuery ? 'No accounts matched your search criteria. Try a different query.' : 'No player accounts currently registered in database.'"
        icon="👥"
      />
    </div>

    <!-- Players Data Table -->
    <div v-else class="card table-card">
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Account Username</th>
              <th>Character Nickname</th>
              <th>Diamonds</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in players" :key="p.account_id">
              <td class="font-mono text-muted text-sm">#{{ p.account_id }}</td>
              <td>
                <div class="player-ident">
                  <span class="font-bold text-white">{{ p.username }}</span>
                  <span v-if="p.email" class="text-xs text-muted">{{ p.email }}</span>
                </div>
              </td>
              <td>
                <span v-if="p.character_nickname" class="char-badge">
                  {{ p.character_nickname }} <span class="char-lvl">Lv.{{ p.character_level || 1 }}</span>
                </span>
                <span v-else class="text-muted text-xs italic">No Character</span>
              </td>
              <td>
                <span v-if="p.diamonds !== null && p.diamonds !== undefined" class="diamond-val">
                  💎 {{ p.diamonds.toLocaleString() }}
                </span>
                <span v-else class="text-muted text-xs">—</span>
              </td>
              <td>
                <span class="badge" :class="p.role === 'admin' ? 'badge-dev' : 'badge-player'">
                  {{ p.role.toUpperCase() }}
                </span>
              </td>
              <td>
                <span v-if="p.is_banned" class="status-pill status-banned" :title="p.ban_reason || ''">
                  SUSPENDED
                </span>
                <span v-else class="status-pill status-active">
                  ACTIVE
                </span>
              </td>
              <td class="actions-cell">
                <RouterLink
                  :to="`/admin/players/${p.account_id}`"
                  class="btn btn-secondary btn-sm"
                  title="Inspect Details"
                >
                  Inspect
                </RouterLink>

                <button
                  v-if="!p.is_banned && p.role !== 'admin'"
                  class="btn btn-danger btn-sm"
                  @click="openSuspendModal(p)"
                  title="Suspend Account"
                >
                  Suspend
                </button>
                <button
                  v-else-if="p.is_banned"
                  class="btn btn-primary btn-sm"
                  @click="openReactivateModal(p)"
                  title="Reactivate Account"
                >
                  Reactivate
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Toolbar -->
      <div class="pagination-footer">
        <span class="page-info">
          Showing {{ ((page - 1) * limit) + 1 }}–{{ Math.min(page * limit, total) }} of {{ total }} accounts
        </span>
        <div class="pagination-controls">
          <button
            class="btn btn-secondary btn-sm"
            :disabled="page <= 1"
            @click="prevPage"
          >
            ← Previous
          </button>
          <span class="current-page">Page {{ page }}</span>
          <button
            class="btn btn-secondary btn-sm"
            :disabled="page * limit >= total"
            @click="nextPage"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- Moderation Modal (Suspend / Reactivate) -->
    <div v-if="actionModalOpen" class="modal-backdrop" @click.self="closeModal">
      <div class="modal-dialog">
        <div class="modal-header">
          <h3 class="modal-title">
            {{ modalAction === 'suspend' ? 'Suspend Player Account' : 'Reactivate Player Account' }}
          </h3>
          <button class="modal-close" @click="closeModal">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="actionError" class="alert alert-danger mb-3">
            {{ actionError }}
          </div>

          <p class="modal-desc">
            Target Operator: <strong>{{ selectedPlayer?.username }}</strong> (Account #{{ selectedPlayer?.account_id }})
          </p>

          <div v-if="modalAction === 'suspend'" class="warning-box mb-3">
            ⚠️ Suspending this account will immediately revoke all authenticated session tokens and block future OTP logins. Character records, diamonds, and inventory items remain fully preserved in database.
          </div>

          <div class="form-group">
            <label class="form-label">
              {{ modalAction === 'suspend' ? 'Reason for Suspension *' : 'Reason for Reactivation *' }}
            </label>
            <input
              v-model="actionReason"
              type="text"
              class="form-input"
              maxlength="255"
              placeholder="e.g., Exploiting terrain collision or appeal granted"
              required
            />
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" :disabled="actionLoading" @click="closeModal">
            Cancel
          </button>
          <button
            class="btn"
            :class="modalAction === 'suspend' ? 'btn-danger' : 'btn-primary'"
            :disabled="actionLoading || !actionReason.trim()"
            @click="submitAction"
          >
            <span v-if="actionLoading">Processing...</span>
            <span v-else>{{ modalAction === 'suspend' ? 'Confirm Suspension' : 'Confirm Reactivation' }}</span>
          </button>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.mb-4 { margin-bottom: 1.5rem; }
.mb-3 { margin-bottom: 1rem; }
.p-4 { padding: 1.5rem; }

.toolbar-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  gap: 1rem;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 1;
}

.search-input-wrapper {
  position: relative;
  flex: 1;
  max-width: 480px;
}

.search-icon {
  position: absolute;
  left: 0.85rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.9rem;
  opacity: 0.6;
}

.search-input {
  width: 100%;
  padding: 0.65rem 2rem 0.65rem 2.4rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: #fff;
  font-size: 0.85rem;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #ffb400;
}

.clear-btn {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.85rem;
}

.filter-tabs {
  display: flex;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 2px;
}

.filter-tab {
  background: none;
  border: none;
  padding: 0.45rem 0.85rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-muted);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-tab.active {
  background: var(--bg-card);
  color: #ffb400;
}

.total-indicator {
  font-size: 0.85rem;
  color: var(--text-muted);
}

.total-indicator strong {
  color: #fff;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.table-card {
  overflow: hidden;
}

.table-responsive {
  overflow-x: auto;
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

.data-table tr:hover {
  background: rgba(255, 255, 255, 0.02);
}

.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.text-white { color: #fff; }
.text-xs { font-size: 0.75rem; }
.text-sm { font-size: 0.85rem; }
.italic { font-style: italic; }

.player-ident {
  display: flex;
  flex-direction: column;
}

.char-badge {
  background: rgba(0, 204, 136, 0.08);
  border: 1px solid rgba(0, 204, 136, 0.25);
  color: var(--color-primary);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.8rem;
}

.char-lvl {
  color: var(--text-muted);
  font-size: 0.7rem;
  margin-left: 0.25rem;
}

.diamond-val {
  color: #ffb400;
  font-weight: 700;
  font-family: monospace;
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

.actions-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pagination-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-top: 1px solid var(--border-color);
}

.page-info {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.current-page {
  font-size: 0.85rem;
  font-weight: 700;
  color: #fff;
}

/* Modal Styling */
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
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border-color);
}

.modal-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: #fff;
}

.modal-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.25rem;
  cursor: pointer;
}

.modal-body {
  padding: 1.5rem;
}

.modal-desc {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: #ccc;
}

.warning-box {
  background: rgba(255, 77, 77, 0.1);
  border: 1px solid rgba(255, 77, 77, 0.3);
  padding: 0.85rem;
  border-radius: 6px;
  color: #ff9999;
  font-size: 0.8rem;
  line-height: 1.4;
}

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

@media (max-width: 768px) {
  .toolbar-card {
    flex-direction: column;
    align-items: flex-start;
  }
  .toolbar-left {
    flex-direction: column;
    width: 100%;
  }
  .search-input-wrapper {
    max-width: 100%;
    width: 100%;
  }
}
</style>
