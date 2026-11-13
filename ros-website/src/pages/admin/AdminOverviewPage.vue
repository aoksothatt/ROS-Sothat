<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { adminService } from '@/services/admin';
import type { AdminDashboardSummary } from '@/types/admin';
import AdminLayout from '@/components/admin/AdminLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const summary = ref<AdminDashboardSummary | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

async function loadData() {
  if (!authStore.token) return;
  loading.value = true;
  error.value = null;
  try {
    summary.value = await adminService.getSummary(authStore.token);
  } catch (err: any) {
    error.value = err.message || 'Failed to load dashboard overview data.';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadData();
});

function formatTime(isoStr: string): string {
  try {
    const d = new Date(isoStr);
    return d.toLocaleString();
  } catch {
    return isoStr;
  }
}
</script>

<template>
  <AdminLayout
    title="Administrative Overview"
    subtitle="Operational metrics, account statuses, and system audit feed"
  >
    <div v-if="error" class="alert alert-danger mb-4">
      <span>{{ error }}</span>
      <button class="btn btn-secondary btn-sm" @click="loadData">Retry</button>
    </div>

    <LoadingState v-if="loading" message="Loading server metrics..." />

    <div v-else-if="summary" class="overview-content">
      <!-- Top Metrics Grid -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">👥</span>
            <span class="metric-title">TOTAL ACCOUNTS</span>
          </div>
          <div class="metric-value">{{ summary.total_accounts }}</div>
          <div class="metric-sub">
            <span class="text-success">{{ summary.active_accounts }} Active</span> •
            <span :class="summary.suspended_accounts > 0 ? 'text-danger font-bold' : 'text-muted'">
              {{ summary.suspended_accounts }} Suspended
            </span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">🎖️</span>
            <span class="metric-title">PLAYER CHARACTERS</span>
          </div>
          <div class="metric-value">{{ summary.total_characters }}</div>
          <div class="metric-sub text-muted">Active In-Game Profiles</div>
        </div>

        <div class="metric-card highlight-metric">
          <div class="metric-header">
            <span class="metric-icon">💎</span>
            <span class="metric-title">TOTAL DIAMONDS</span>
          </div>
          <div class="metric-value text-gold">{{ summary.total_diamonds.toLocaleString() }}</div>
          <div class="metric-sub text-muted">Total Ledger Balances</div>
        </div>

        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">🎒</span>
            <span class="metric-title">INVENTORY ITEMS</span>
          </div>
          <div class="metric-value">{{ summary.total_inventory_items.toLocaleString() }}</div>
          <div class="metric-sub text-muted">Owned Player Items</div>
        </div>
      </div>

      <!-- Server Operational Services Strip -->
      <div class="card status-strip mb-4">
        <div class="strip-item">
          <span class="strip-label">LOBBY PRESENCES</span>
          <span class="strip-val">{{ summary.active_lobby_presences }}</span>
        </div>
        <div class="strip-divider"></div>
        <div class="strip-item">
          <span class="strip-label">ACTIVE ROOMS</span>
          <span class="strip-val">{{ summary.active_rooms }}</span>
        </div>
        <div class="strip-divider"></div>
        <div class="strip-item">
          <span class="strip-label">MATCH TICKETS</span>
          <span class="strip-val">{{ summary.queued_matchmaking_tickets }}</span>
        </div>
        <div class="strip-divider"></div>
        <div class="strip-item">
          <span class="strip-label">HOST / NETWORK</span>
          <span class="strip-val text-success">127.0.0.1 (Loopback)</span>
        </div>
      </div>

      <!-- Quick Actions Grid -->
      <div class="actions-strip mb-4">
        <RouterLink to="/admin/players" class="action-btn">
          <span class="btn-icon">👥</span>
          <span class="btn-text">Manage Players</span>
        </RouterLink>
        <RouterLink to="/admin/transactions" class="action-btn">
          <span class="btn-icon">💎</span>
          <span class="btn-text">Diamond Transactions</span>
        </RouterLink>
        <RouterLink to="/admin/inventory" class="action-btn">
          <span class="btn-icon">🎒</span>
          <span class="btn-text">Inventory Catalog</span>
        </RouterLink>
        <RouterLink to="/admin/audit-logs" class="action-btn">
          <span class="btn-icon">📜</span>
          <span class="btn-text">Audit Log Feed</span>
        </RouterLink>
      </div>

      <!-- Recent Audit Activity -->
      <div class="card activity-card">
        <div class="card-header">
          <h2 class="card-title">RECENT ADMINISTRATIVE ACTIVITY</h2>
          <RouterLink to="/admin/audit-logs" class="view-all-link">View Full Audit Log →</RouterLink>
        </div>

        <div v-if="summary.recent_activity.length === 0" class="p-4">
          <EmptyState
            title="No Recent Administrative Actions"
            description="All sensitive actions (diamond grants, bans, inventory alterations) will appear in this real-time audit ledger."
            icon="📜"
          />
        </div>

        <div v-else class="table-responsive">
          <table class="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Administrator</th>
                <th>Action</th>
                <th>Target</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in summary.recent_activity" :key="item.id">
                <td class="text-muted text-sm">{{ formatTime(item.created_at) }}</td>
                <td class="font-bold text-admin">{{ item.admin_username || `Admin #${item.admin_account_id}` }}</td>
                <td>
                  <span class="action-badge" :class="item.action_type.toLowerCase()">
                    {{ item.action_type }}
                  </span>
                </td>
                <td>
                  <span class="target-badge">{{ item.target_type }}: #{{ item.target_id }}</span>
                </td>
                <td class="reason-cell">{{ item.reason }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </AdminLayout>
</template>

<style scoped>
.mb-4 {
  margin-bottom: 1.5rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.metric-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.highlight-metric {
  border-color: rgba(255, 180, 0, 0.4);
  background: linear-gradient(135deg, rgba(255, 180, 0, 0.05), rgba(8, 11, 16, 0.8));
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.metric-icon {
  font-size: 1.2rem;
}

.metric-title {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.metric-value {
  font-size: 2rem;
  font-weight: 900;
  color: #fff;
  letter-spacing: -0.02em;
}

.text-gold {
  color: #ffb400;
}

.metric-sub {
  font-size: 0.8rem;
}

.text-success {
  color: #00cc88;
}

.text-danger {
  color: #ff4d4d;
}

.text-admin {
  color: #ffb400;
}

.status-strip {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 1rem;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.strip-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.strip-label {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 0.08em;
}

.strip-val {
  font-size: 1.1rem;
  font-weight: 700;
  color: #fff;
}

.strip-divider {
  width: 1px;
  height: 32px;
  background-color: var(--border-color);
}

.actions-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 1rem;
  color: #fff;
  text-decoration: none;
  font-weight: 700;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(255, 180, 0, 0.1);
  border-color: #ffb400;
  transform: translateY(-2px);
}

.btn-icon {
  font-size: 1.25rem;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.view-all-link {
  color: var(--color-primary);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 700;
}

.view-all-link:hover {
  text-decoration: underline;
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

.action-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
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

.target-badge {
  font-family: monospace;
  background: rgba(0, 0, 0, 0.4);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #ccc;
}

.reason-cell {
  max-width: 250px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #ddd;
}

.p-4 {
  padding: 1.5rem;
}

.text-sm {
  font-size: 0.75rem;
}

@media (max-width: 1024px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .actions-strip {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  .status-strip {
    flex-direction: column;
    gap: 1rem;
  }
  .strip-divider {
    display: none;
  }
  .actions-strip {
    grid-template-columns: 1fr;
  }
}
</style>
