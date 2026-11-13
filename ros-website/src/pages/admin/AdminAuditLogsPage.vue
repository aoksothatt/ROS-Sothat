<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { adminService } from '@/services/admin';
import type { AdminAuditLog } from '@/types/admin';
import AdminLayout from '@/components/admin/AdminLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const logs = ref<AdminAuditLog[]>([]);
const total = ref(0);
const loading = ref(true);
const error = ref<string | null>(null);

// Filters
const actionTypeFilter = ref<string>('all');
const page = ref(1);
const limit = 20;

async function fetchLogs() {
  if (!authStore.token) return;
  loading.value = true;
  error.value = null;

  try {
    const offset = (page.value - 1) * limit;
    const actionParam = actionTypeFilter.value === 'all' ? undefined : actionTypeFilter.value;
    const res = await adminService.listAuditLogs(authStore.token, {
      action_type: actionParam,
      limit,
      offset
    });
    logs.value = res.logs;
    total.value = res.total;
  } catch (err: any) {
    error.value = err.message || 'Failed to retrieve administrative audit logs.';
  } finally {
    loading.value = false;
  }
}

watch([actionTypeFilter], () => {
  page.value = 1;
  fetchLogs();
});

function prevPage() {
  if (page.value > 1) {
    page.value--;
    fetchLogs();
  }
}

function nextPage() {
  if (page.value * limit < total.value) {
    page.value++;
    fetchLogs();
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
  fetchLogs();
});
</script>

<template>
  <AdminLayout
    title="Administrator Audit Logs"
    subtitle="Immutable, append-only security ledger tracking all sensitive management operations"
  >
    <div v-if="error" class="alert alert-danger mb-4">
      <span>{{ error }}</span>
      <button class="btn btn-secondary btn-sm" @click="fetchLogs">Retry</button>
    </div>

    <!-- Filter Bar -->
    <div class="card toolbar-card mb-4">
      <div class="filter-group">
        <span class="filter-label">Filter Action:</span>
        <button
          class="filter-tab"
          :class="{ active: actionTypeFilter === 'all' }"
          @click="actionTypeFilter = 'all'"
        >
          All Actions
        </button>
        <button
          class="filter-tab"
          :class="{ active: actionTypeFilter === 'DIAMOND_GRANT' }"
          @click="actionTypeFilter = 'DIAMOND_GRANT'"
        >
          Diamond Grants
        </button>
        <button
          class="filter-tab"
          :class="{ active: actionTypeFilter === 'DIAMOND_DEDUCT' }"
          @click="actionTypeFilter = 'DIAMOND_DEDUCT'"
        >
          Diamond Deductions
        </button>
        <button
          class="filter-tab"
          :class="{ active: actionTypeFilter === 'INVENTORY_GRANT' }"
          @click="actionTypeFilter = 'INVENTORY_GRANT'"
        >
          Item Grants
        </button>
        <button
          class="filter-tab"
          :class="{ active: actionTypeFilter === 'INVENTORY_REMOVE' }"
          @click="actionTypeFilter = 'INVENTORY_REMOVE'"
        >
          Item Removals
        </button>
        <button
          class="filter-tab"
          :class="{ active: actionTypeFilter === 'ACCOUNT_SUSPEND' }"
          @click="actionTypeFilter = 'ACCOUNT_SUSPEND'"
        >
          Suspensions
        </button>
      </div>

      <div class="toolbar-right">
        <span class="text-sm text-muted">
          Total Logged Actions: <strong>{{ total }}</strong>
        </span>
      </div>
    </div>

    <LoadingState v-if="loading" message="Loading audit log records..." />

    <div v-else-if="logs.length === 0" class="card p-4">
      <EmptyState
        title="No Audit Records Found"
        description="No administrative actions match the selected filter criteria."
        icon="📜"
      />
    </div>

    <!-- Audit Logs Table -->
    <div v-else class="card table-card">
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Audit ID</th>
              <th>Timestamp</th>
              <th>Administrator</th>
              <th>Action Type</th>
              <th>Target</th>
              <th>Reason</th>
              <th>Metadata Details</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in logs" :key="l.id">
              <td class="font-mono text-muted text-sm">#{{ l.id }}</td>
              <td class="text-muted text-xs whitespace-nowrap">{{ formatTime(l.created_at) }}</td>
              <td class="font-bold text-admin whitespace-nowrap">
                {{ l.admin_username || `Admin #${l.admin_account_id}` }}
              </td>
              <td>
                <span class="action-badge" :class="l.action_type.toLowerCase()">
                  {{ l.action_type }}
                </span>
              </td>
              <td>
                <span class="target-badge">{{ l.target_type }}: #{{ l.target_id }}</span>
              </td>
              <td class="reason-cell font-medium">{{ l.reason }}</td>
              <td>
                <div class="details-box">
                  <code>{{ JSON.stringify(l.details) }}</code>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <div class="pagination-footer">
        <span class="page-info">
          Showing {{ ((page - 1) * limit) + 1 }}–{{ Math.min(page * limit, total) }} of {{ total }} records
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
  </AdminLayout>
</template>

<style scoped>
.mb-4 { margin-bottom: 1.5rem; }
.p-4 { padding: 1.5rem; }

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.table-card { overflow: hidden; }

.toolbar-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  gap: 1rem;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-muted);
}

.filter-tab {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.4rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-tab:hover {
  color: #fff;
}

.filter-tab.active {
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

.font-mono { font-family: monospace; }
.font-bold { font-weight: 700; }
.font-medium { font-weight: 500; }
.text-admin { color: #ffb400; }
.text-xs { font-size: 0.75rem; }
.text-sm { font-size: 0.85rem; }
.whitespace-nowrap { white-space: nowrap; }

.action-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  white-space: nowrap;
}

.action-badge.diamond_grant {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
  border: 1px solid rgba(0, 204, 136, 0.3);
}

.action-badge.diamond_deduct {
  background: rgba(255, 180, 0, 0.15);
  color: #ffb400;
  border: 1px solid rgba(255, 180, 0, 0.3);
}

.action-badge.inventory_grant {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
  border: 1px solid rgba(0, 204, 136, 0.3);
}

.action-badge.inventory_remove {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
  border: 1px solid rgba(255, 77, 77, 0.3);
}

.action-badge.account_suspend {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
  border: 1px solid rgba(255, 77, 77, 0.3);
}

.action-badge.account_reactivate {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
  border: 1px solid rgba(0, 204, 136, 0.3);
}

.action-badge.role_change {
  background: rgba(255, 180, 0, 0.15);
  color: #ffb400;
  border: 1px solid rgba(255, 180, 0, 0.3);
}

.target-badge {
  font-family: monospace;
  background: rgba(0, 0, 0, 0.4);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #ccc;
  white-space: nowrap;
}

.reason-cell {
  color: #eee;
  max-width: 200px;
}

.details-box {
  background: rgba(0, 0, 0, 0.3);
  padding: 0.35rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  max-width: 280px;
  overflow-x: auto;
  white-space: nowrap;
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

@media (max-width: 900px) {
  .toolbar-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
