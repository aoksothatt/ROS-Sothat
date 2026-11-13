<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { playerService } from '@/services/player';
import type { CharacterProfile, DiamondHistoryResponse } from '@/types/dashboard';
import DashboardLayout from '@/components/dashboard/DashboardLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const character = ref<CharacterProfile | null>(null);
const walletHistory = ref<DiamondHistoryResponse | null>(null);
const loading = ref(true);
const errorMessage = ref('');

onMounted(async () => {
  if (!authStore.token) return;
  loading.value = true;
  errorMessage.value = '';
  try {
    character.value = await playerService.getMyCharacter(authStore.token);
    if (character.value) {
      walletHistory.value = await playerService.getMyDiamondHistory(authStore.token, 50, 0);
    }
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to synchronize diamond wallet ledger.';
  } finally {
    loading.value = false;
  }
});

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return iso;
  }
}
</script>

<template>
  <DashboardLayout
    title="Diamond Currency Vault"
    subtitle="Authoritative diamond ledger, transaction records, and reserve balance."
  >
    <div v-if="loading">
      <LoadingState message="Auditing diamond transaction ledger against database..." />
    </div>

    <div v-else class="wallet-content fade-in">
      <div v-if="errorMessage" class="alert alert-danger" role="alert">
        {{ errorMessage }}
      </div>

      <!-- If character does not exist -->
      <div v-if="!character" class="card">
        <EmptyState
          icon="💎"
          title="WALLET UNAVAILABLE"
          description="A game character has not been provisioned for this account yet. Please deploy a character on the Profile page to activate your personal currency vault."
        />
      </div>

      <template v-else>
        <!-- Vault Summary Cards -->
        <section class="vault-summary-grid">
          <div class="card vault-card primary-vault">
            <div class="vault-top">
              <span class="vault-label">AUTHORITATIVE DIAMOND RESERVE</span>
              <span class="vault-icon">💎</span>
            </div>
            <div class="vault-amount-wrap">
              <span class="vault-amount gold">{{ character.diamonds.toLocaleString() }}</span>
              <span class="vault-symbol">DIAMONDS</span>
            </div>
            <p class="vault-desc">
              Synchronized with server character balance. Append-only overdraft protected ledger.
            </p>
          </div>

          <div class="card vault-card secondary-vault">
            <div class="vault-top">
              <span class="vault-label">ISLAND GOLD CURRENCY</span>
              <span class="vault-icon">🪙</span>
            </div>
            <div class="vault-amount-wrap">
              <span class="vault-amount gold-sub">{{ character.gold.toLocaleString() }}</span>
              <span class="vault-symbol">GOLD</span>
            </div>
            <p class="vault-desc">
              Standard survival currency for repair parts, supplies, and basic attachments.
            </p>
          </div>
        </section>

        <!-- Read-Only Policy Security Notice -->
        <div class="card policy-notice-card">
          <span class="notice-icon">🛡️</span>
          <div class="notice-text">
            <strong>Immutable Economy Ledger:</strong> Player balances are tracked with atomic database locks and checked constraints. Diamond grants are administered exclusively through verified events and official administrative rewards. Self-granting, purchasing, or transfers are disabled for player accounts.
          </div>
        </div>

        <!-- Transaction History Ledger -->
        <section class="card history-section">
          <div class="history-header">
            <h3 class="history-title">TRANSACTION AUDIT LOG</h3>
            <span class="history-count">
              Total Logged: <strong>{{ walletHistory ? walletHistory.total_transactions : 0 }}</strong>
            </span>
          </div>

          <div v-if="!walletHistory || walletHistory.transactions.length === 0" class="history-empty">
            <EmptyState
              icon="📜"
              title="NO TRANSACTIONS LOGGED"
              description="Your account holds initial starter diamonds. Future administrative grants, battle rewards, or deductions will be permanently recorded here."
            />
          </div>

          <div v-else class="table-responsive">
            <table class="tactical-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Before</th>
                  <th>After</th>
                  <th>Audit Justification</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="tx in walletHistory.transactions" :key="tx.id">
                  <td class="mono-cell">{{ formatDate(tx.created_at) }}</td>
                  <td>
                    <span
                      class="badge"
                      :class="tx.operation_type === 'GRANT' ? 'badge-status' : 'badge-dev'"
                    >
                      {{ tx.operation_type }}
                    </span>
                  </td>
                  <td class="mono-cell" :class="tx.operation_type === 'GRANT' ? 'tx-plus' : 'tx-minus'">
                    {{ tx.operation_type === 'GRANT' ? `+${tx.amount.toLocaleString()}` : `-${tx.amount.toLocaleString()}` }} 💎
                  </td>
                  <td class="mono-cell text-muted">{{ tx.balance_before.toLocaleString() }}</td>
                  <td class="mono-cell gold-cell">{{ tx.balance_after.toLocaleString() }}</td>
                  <td class="reason-cell">{{ tx.reason }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </DashboardLayout>
</template>

<style scoped>
.wallet-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.vault-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.5rem;
}

.vault-card {
  padding: 1.75rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-radius: 6px;
}

.primary-vault {
  background: linear-gradient(135deg, var(--bg-card) 0%, #1A2636 100%);
  border-top: 3px solid var(--accent-gold);
}

.secondary-vault {
  background: linear-gradient(135deg, var(--bg-card) 0%, #19232F 100%);
  border-top: 3px solid #E2B755;
}

.vault-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.vault-label {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
}

.vault-icon {
  font-size: 1.5rem;
}

.vault-amount-wrap {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.vault-amount {
  font-size: 2.75rem;
  font-weight: 900;
  font-family: var(--font-mono);
  line-height: 1;
}

.vault-amount.gold {
  color: var(--accent-gold);
  text-shadow: 0 0 20px rgba(215, 168, 75, 0.3);
}

.vault-amount.gold-sub {
  color: #E2B755;
}

.vault-symbol {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
}

.vault-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.policy-notice-card {
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  background-color: rgba(215, 168, 75, 0.08);
  border: 1px solid rgba(215, 168, 75, 0.25);
}

.notice-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.notice-text {
  font-size: 0.85rem;
  color: var(--text-primary);
  line-height: 1.5;
}

.history-section {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.75rem;
}

.history-title {
  font-size: 0.95rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin: 0;
  color: var(--text-primary);
}

.history-count {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.history-empty {
  padding: 1rem 0;
}

.table-responsive {
  overflow-x: auto;
}

.tactical-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 0.85rem;
}

.tactical-table th {
  padding: 0.75rem 1rem;
  background-color: var(--bg-secondary);
  color: var(--text-secondary);
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  font-size: 0.75rem;
  border-bottom: 1px solid var(--border-color);
}

.tactical-table td {
  padding: 0.85rem 1rem;
  border-bottom: 1px solid var(--border-color);
}

.mono-cell {
  font-family: var(--font-mono);
}

.gold-cell {
  color: var(--accent-gold);
  font-weight: 700;
}

.tx-plus {
  color: #4CAF50;
  font-weight: 700;
}

.tx-minus {
  color: var(--accent-red);
  font-weight: 700;
}

.text-muted {
  color: var(--text-secondary);
}

.reason-cell {
  color: var(--text-primary);
}
</style>
