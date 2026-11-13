<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { adminService } from '@/services/admin';
import type { AdminPlayerSummary, AdminAuditLog } from '@/types/admin';
import AdminLayout from '@/components/admin/AdminLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();

const players = ref<AdminPlayerSummary[]>([]);
const recentLogs = ref<AdminAuditLog[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// Diamond Operation Form
const selectedPlayerId = ref<number | ''>('');
const opType = ref<'GRANT' | 'DEDUCT'>('GRANT');
const amount = ref<number>(100);
const reason = ref<string>('');
const opLoading = ref(false);
const opError = ref<string | null>(null);
const opSuccess = ref<string | null>(null);

function generateIdempotencyKey(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
}

async function loadData() {
  if (!authStore.token) return;
  loading.value = true;
  error.value = null;
  try {
    const pResp = await adminService.listPlayers(authStore.token, { limit: 100 });
    players.value = pResp.players.filter(p => p.character_gid !== null);

    const logResp = await adminService.listAuditLogs(authStore.token, {
      limit: 50,
      offset: 0
    });
    // Filter diamond-related actions
    recentLogs.value = logResp.logs.filter(l =>
      l.action_type === 'DIAMOND_GRANT' || l.action_type === 'DIAMOND_DEDUCT'
    );
  } catch (err: any) {
    error.value = err.message || 'Failed to load diamond transaction data.';
  } finally {
    loading.value = false;
  }
}

const selectedPlayer = () => {
  return players.value.find(p => p.account_id === selectedPlayerId.value);
};

const expectedNewBalance = () => {
  const p = selectedPlayer();
  const current = p?.diamonds ?? 0;
  const val = Number(amount.value) || 0;
  if (opType.value === 'GRANT') return current + val;
  return Math.max(0, current - val);
};

async function executeDiamondOp() {
  if (!authStore.token || !selectedPlayerId.value) {
    opError.value = 'Please select a player character.';
    return;
  }
  if (!amount.value || amount.value <= 0) {
    opError.value = 'Amount must be a positive integer.';
    return;
  }
  if (!reason.value.trim()) {
    opError.value = 'A valid operational reason is required for auditing.';
    return;
  }

  opLoading.value = true;
  opError.value = null;
  opSuccess.value = null;

  try {
    const key = generateIdempotencyKey(opType.value.toLowerCase());
    if (opType.value === 'GRANT') {
      await adminService.grantDiamonds(authStore.token, Number(selectedPlayerId.value), {
        amount: Math.floor(amount.value),
        reason: reason.value.trim(),
        idempotency_key: key
      });
      opSuccess.value = `Successfully granted ${amount.value.toLocaleString()} diamonds.`;
    } else {
      await adminService.deductDiamonds(authStore.token, Number(selectedPlayerId.value), {
        amount: Math.floor(amount.value),
        reason: reason.value.trim(),
        idempotency_key: key
      });
      opSuccess.value = `Successfully deducted ${amount.value.toLocaleString()} diamonds.`;
    }
    reason.value = '';
    await loadData();
  } catch (err: any) {
    opError.value = err.message || 'Operation failed.';
  } finally {
    opLoading.value = false;
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
    title="Diamond Ledger Administration"
    subtitle="Atomic currency adjustments, overdraft prevention, and append-only transaction logs"
  >
    <div v-if="error" class="alert alert-danger mb-4">
      <span>{{ error }}</span>
      <button class="btn btn-secondary btn-sm" @click="loadData">Retry</button>
    </div>

    <!-- Quick Action Mutation Form Card -->
    <div class="card p-4 mb-4">
      <h3 class="section-title">QUICK DIAMOND ADJUSTMENT</h3>
      <p class="section-desc">
        Select any active player character to grant or deduct diamonds atomically. Transactions update the database ledger instantly and create an immutable audit record.
      </p>

      <div v-if="opError" class="alert alert-danger mb-3">{{ opError }}</div>
      <div v-if="opSuccess" class="alert alert-success mb-3">{{ opSuccess }}</div>

      <form class="op-form" @submit.prevent="executeDiamondOp">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">Target Player Character *</label>
            <select v-model="selectedPlayerId" class="form-input" required>
              <option value="" disabled>-- Select Character --</option>
              <option v-for="p in players" :key="p.account_id" :value="p.account_id">
                {{ p.character_nickname }} ({{ p.username }}) — Current: 💎 {{ (p.diamonds ?? 0).toLocaleString() }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Operation Type</label>
            <div class="btn-group">
              <button
                type="button"
                class="btn-toggle"
                :class="{ active: opType === 'GRANT' }"
                @click="opType = 'GRANT'"
              >
                ➕ Grant
              </button>
              <button
                type="button"
                class="btn-toggle toggle-danger"
                :class="{ active: opType === 'DEDUCT' }"
                @click="opType = 'DEDUCT'"
              >
                ➖ Deduct
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Amount (Diamonds) *</label>
            <input
              v-model.number="amount"
              type="number"
              min="1"
              max="10000000"
              class="form-input"
              required
            />
          </div>
        </div>

        <div v-if="selectedPlayerId" class="balance-calc-strip mb-3">
          <div class="calc-item">
            <span class="calc-label">CURRENT</span>
            <span class="calc-val">💎 {{ (selectedPlayer()?.diamonds ?? 0).toLocaleString() }}</span>
          </div>
          <div class="calc-arrow">➔</div>
          <div class="calc-item">
            <span class="calc-label">ADJUSTMENT</span>
            <span :class="opType === 'GRANT' ? 'text-success' : 'text-danger'">
              {{ opType === 'GRANT' ? '+' : '-' }}{{ (amount || 0).toLocaleString() }}
            </span>
          </div>
          <div class="calc-arrow">➔</div>
          <div class="calc-item">
            <span class="calc-label">RESULT</span>
            <span class="calc-val text-gold font-bold">💎 {{ expectedNewBalance().toLocaleString() }}</span>
          </div>
        </div>

        <div class="form-group mb-3">
          <label class="form-label">Operational Reason *</label>
          <input
            v-model="reason"
            type="text"
            class="form-input"
            maxlength="255"
            placeholder="e.g., Seasonal competition prize or system compensation"
            required
          />
        </div>

        <button
          type="submit"
          class="btn"
          :class="opType === 'GRANT' ? 'btn-primary' : 'btn-danger'"
          :disabled="opLoading || !selectedPlayerId || !amount || amount <= 0 || !reason.trim()"
        >
          <span v-if="opLoading">Executing...</span>
          <span v-else>{{ opType === 'GRANT' ? 'Confirm & Grant' : 'Confirm & Deduct' }}</span>
        </button>
      </form>
    </div>

    <!-- Recent Diamond Transactions Table -->
    <div class="card table-card">
      <div class="card-header">
        <h3 class="card-title">RECENT DIAMOND LEDGER AUDIT RECORDS</h3>
      </div>

      <LoadingState v-if="loading" message="Loading transaction logs..." />

      <div v-else-if="recentLogs.length === 0" class="p-4">
        <EmptyState
          title="No Diamond Ledger Transactions Found"
          description="Administrative diamond grants and deductions will be permanently recorded here with balance before and after details."
          icon="💎"
        />
      </div>

      <div v-else class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Log ID</th>
              <th>Operation</th>
              <th>Target Entity</th>
              <th>Admin Actor</th>
              <th>Delta / Details</th>
              <th>Reason</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in recentLogs" :key="l.id">
              <td class="font-mono text-muted text-sm">#{{ l.id }}</td>
              <td>
                <span
                  class="action-badge"
                  :class="l.action_type === 'DIAMOND_GRANT' ? 'diamond_grant' : 'diamond_deduct'"
                >
                  {{ l.action_type }}
                </span>
              </td>
              <td>
                <span class="target-badge">{{ l.target_type }}: #{{ l.target_id }}</span>
              </td>
              <td class="font-bold text-admin">
                {{ l.admin_username || `Admin #${l.admin_account_id}` }}
              </td>
              <td>
                <span v-if="l.details?.amount" class="font-bold" :class="l.action_type === 'DIAMOND_GRANT' ? 'text-success' : 'text-danger'">
                  {{ l.action_type === 'DIAMOND_GRANT' ? '+' : '-' }}{{ l.details.amount.toLocaleString() }}
                  <span class="text-xs text-muted"> ({{ l.details.balance_before }} ➔ {{ l.details.balance_after }})</span>
                </span>
                <span v-else class="text-xs text-muted font-mono">{{ JSON.stringify(l.details) }}</span>
              </td>
              <td class="text-sm">{{ l.reason }}</td>
              <td class="text-muted text-xs">{{ formatTime(l.created_at) }}</td>
            </tr>
          </tbody>
        </table>
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

.section-title {
  margin: 0 0 0.35rem 0;
  font-size: 1rem;
  font-weight: 800;
  color: #fff;
}

.section-desc {
  margin: 0 0 1.25rem 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.form-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
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

.btn-group {
  display: flex;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  overflow: hidden;
  height: 42px;
}

.btn-toggle {
  flex: 1;
  background: none;
  border: none;
  color: var(--text-muted);
  font-weight: 700;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-toggle.active {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
}

.toggle-danger.active {
  background: rgba(255, 77, 77, 0.15);
  color: #ff4d4d;
}

.balance-calc-strip {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 0.85rem;
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.calc-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.calc-label {
  font-size: 0.65rem;
  font-weight: 800;
  color: var(--text-muted);
}

.calc-val {
  font-family: monospace;
  font-size: 0.95rem;
}

.calc-arrow {
  color: var(--text-muted);
  font-size: 1.1rem;
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
.text-xs { font-size: 0.75rem; }
.text-sm { font-size: 0.85rem; }
.text-gold { color: #ffb400; }
.text-success { color: #00cc88; }
.text-danger { color: #ff4d4d; }
.text-admin { color: #ffb400; }

.action-badge {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 800;
}

.action-badge.diamond_grant {
  background: rgba(0, 204, 136, 0.15);
  color: #00cc88;
}

.action-badge.diamond_deduct {
  background: rgba(255, 180, 0, 0.15);
  color: #ffb400;
}

.target-badge {
  font-family: monospace;
  background: rgba(0, 0, 0, 0.4);
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #ccc;
}

@media (max-width: 900px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
