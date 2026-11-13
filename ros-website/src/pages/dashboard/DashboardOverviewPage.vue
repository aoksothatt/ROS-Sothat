<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { playerService } from '@/services/player';
import type { CharacterProfile, CharacterInventoryResponse } from '@/types/dashboard';
import DashboardLayout from '@/components/dashboard/DashboardLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';

const authStore = useAuthStore();
const character = ref<CharacterProfile | null>(null);
const inventory = ref<CharacterInventoryResponse | null>(null);
const loading = ref(true);
const errorMessage = ref('');

onMounted(async () => {
  if (!authStore.token) return;
  try {
    character.value = await playerService.getMyCharacter(authStore.token);
    if (character.value) {
      inventory.value = await playerService.getMyInventory(authStore.token, 10, 0);
    }
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to load operator overview telemetry.';
  } finally {
    loading.value = false;
  }
});

function formatDate(iso: string | null | undefined) {
  if (!iso) return 'Recent';
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return iso;
  }
}
</script>

<template>
  <DashboardLayout
    title="Tactical Command Overview"
    subtitle="Personal status, currency vault, and island operational readiness."
  >
    <div v-if="loading">
      <LoadingState message="Synchronizing command telemetry with ROS Sothat server..." />
    </div>

    <div v-else-if="errorMessage" class="alert alert-danger" role="alert">
      {{ errorMessage }}
    </div>

    <div v-else class="overview-content fade-in">
      <!-- Top Welcome Banner -->
      <section class="card welcome-card">
        <div class="welcome-left">
          <div class="operator-avatar">
            <span>{{ authStore.user?.username.slice(0, 2).toUpperCase() || 'OP' }}</span>
          </div>
          <div class="welcome-meta">
            <div class="badge-row">
              <span class="badge" :class="{ 'badge-dev': authStore.user?.role === 'admin' }">
                {{ authStore.user?.role.toUpperCase() || 'PLAYER' }}
              </span>
              <span class="badge badge-status">ACTIVE OPERATOR</span>
            </div>
            <h2 class="operator-name">
              WELCOME BACK, <span class="gold-text">{{ character ? character.nickname : authStore.user?.username }}</span>
            </h2>
            <p class="operator-sub">
              Account registered on {{ formatDate(authStore.user?.created_at) }} • Private Server Node #1
            </p>
          </div>
        </div>
        <div class="welcome-actions">
          <RouterLink to="/dashboard/profile" class="btn btn-secondary">
            View Profile
          </RouterLink>
          <RouterLink to="/dashboard/wallet" class="btn btn-primary">
            Open Wallet
          </RouterLink>
        </div>
      </section>

      <!-- 3 Key Metric Summary Cards -->
      <section class="metrics-grid">
        <!-- 1. Diamond Wallet Card -->
        <div class="card metric-card">
          <div class="metric-top">
            <span class="metric-label">AUTHORITATIVE WALLET</span>
            <span class="metric-icon">💎</span>
          </div>
          <div class="metric-value-wrap">
            <span class="metric-value gold">
              {{ character ? character.diamonds.toLocaleString() : '0' }}
            </span>
            <span class="metric-unit">Diamonds</span>
          </div>
          <div class="metric-sub-row">
            <span>Gold Balance:</span>
            <span class="gold-sub-val">{{ character ? character.gold.toLocaleString() : '0' }} G</span>
          </div>
          <RouterLink to="/dashboard/wallet" class="metric-action-link">
            <span>View Transaction Ledger</span>
            <span>&rarr;</span>
          </RouterLink>
        </div>

        <!-- 2. Inventory Summary Card -->
        <div class="card metric-card">
          <div class="metric-top">
            <span class="metric-label">TACTICAL INVENTORY</span>
            <span class="metric-icon">🎒</span>
          </div>
          <div class="metric-value-wrap">
            <span class="metric-value">
              {{ inventory ? inventory.total_items : '0' }}
            </span>
            <span class="metric-unit">Items Stored</span>
          </div>
          <div class="metric-sub-row">
            <span>Equipped Gear:</span>
            <span class="sub-val">
              {{ character ? character.appearances.equipped_clothing.length : 0 }} slots
            </span>
          </div>
          <RouterLink to="/dashboard/inventory" class="metric-action-link">
            <span>Inspect Armory</span>
            <span>&rarr;</span>
          </RouterLink>
        </div>

        <!-- 3. Combat Stats Card -->
        <div class="card metric-card">
          <div class="metric-top">
            <span class="metric-label">ISLAND COMBAT RECORD</span>
            <span class="metric-icon">🎯</span>
          </div>
          <div class="metric-value-wrap">
            <span class="metric-value">
              {{ character ? character.stats.total_matches : '0' }}
            </span>
            <span class="metric-unit">Matches Logged</span>
          </div>
          <div class="metric-sub-row">
            <span>Confirmed Kills:</span>
            <span class="sub-val">{{ character ? character.stats.total_kills : 0 }}</span>
          </div>
          <RouterLink to="/dashboard/statistics" class="metric-action-link">
            <span>Combat Analytics</span>
            <span>&rarr;</span>
          </RouterLink>
        </div>
      </section>

      <!-- Account Details & System Telemetry Grid -->
      <section class="card telemetry-section">
        <h3 class="section-title-sm">OPERATOR TELEMETRY LEDGER</h3>
        <div class="telemetry-grid">
          <div class="telemetry-item">
            <span class="t-label">Account GID</span>
            <span class="t-val">#{{ authStore.user?.id }}</span>
          </div>
          <div class="telemetry-item">
            <span class="t-label">Character GID</span>
            <span class="t-val">{{ character ? `#${character.gid}` : 'Not Created' }}</span>
          </div>
          <div class="telemetry-item">
            <span class="t-label">In-Game Callsign</span>
            <span class="t-val gold">{{ character ? character.nickname : 'Unassigned' }}</span>
          </div>
          <div class="telemetry-item">
            <span class="t-label">Account Status</span>
            <span class="t-val" :class="authStore.user?.is_banned ? 'danger' : 'success'">
              {{ authStore.user?.is_banned ? 'SUSPENDED' : 'AUTHORIZED' }}
            </span>
          </div>
          <div class="telemetry-item">
            <span class="t-label">Transport Protocol</span>
            <span class="t-val mono">Mercury UDP (127.0.0.1)</span>
          </div>
          <div class="telemetry-item">
            <span class="t-label">Session Storage</span>
            <span class="t-val mono">sessionStorage (Tab-Isolated)</span>
          </div>
        </div>
      </section>
    </div>
  </DashboardLayout>
</template>

<style scoped>
.overview-content {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.welcome-card {
  padding: 1.75rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
  background: linear-gradient(135deg, var(--bg-card) 0%, #172230 100%);
  border-left: 4px solid var(--accent-gold);
}

.welcome-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.operator-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background-color: var(--bg-secondary);
  border: 2px solid var(--accent-gold);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 900;
  color: var(--accent-gold);
  font-family: var(--font-mono);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.welcome-meta {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.badge-row {
  display: flex;
  gap: 0.5rem;
}

.operator-name {
  font-size: 1.4rem;
  font-weight: 900;
  letter-spacing: 0.05em;
  margin: 0;
  text-transform: uppercase;
}

.operator-sub {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
}

.welcome-actions {
  display: flex;
  gap: 0.85rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.metric-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: relative;
  transition: transform 0.2s ease, border-color 0.2s ease;
}

.metric-card:hover {
  transform: translateY(-2px);
  border-color: rgba(215, 168, 75, 0.4);
}

.metric-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-label {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  color: var(--text-secondary);
}

.metric-icon {
  font-size: 1.4rem;
}

.metric-value-wrap {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.metric-value {
  font-size: 2.25rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: 1;
}

.metric-value.gold {
  color: var(--accent-gold);
  text-shadow: 0 0 15px rgba(215, 168, 75, 0.3);
}

.metric-unit {
  font-size: 0.85rem;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
}

.metric-sub-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: var(--text-secondary);
  padding: 0.5rem 0;
  border-top: 1px solid var(--border-color);
}

.gold-sub-val {
  color: #E2B755;
  font-weight: 700;
  font-family: var(--font-mono);
}

.sub-val {
  color: var(--text-primary);
  font-weight: 700;
  font-family: var(--font-mono);
}

.metric-action-link {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--accent-gold);
  text-decoration: none;
  padding-top: 0.5rem;
  border-top: 1px dashed var(--border-color);
  transition: color 0.2s ease;
}

.metric-action-link:hover {
  color: #FFFFFF;
}

.telemetry-section {
  padding: 1.75rem;
}

.section-title-sm {
  font-size: 0.9rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin-bottom: 1.25rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.telemetry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.25rem;
}

.telemetry-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.t-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 600;
}

.t-val {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.t-val.gold {
  color: var(--accent-gold);
}

.t-val.success {
  color: #4CAF50;
}

.t-val.danger {
  color: var(--accent-red);
}

.t-val.mono {
  font-size: 0.85rem;
}

@media (max-width: 768px) {
  .welcome-card {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .welcome-actions {
    width: 100%;
  }

  .welcome-actions .btn {
    flex: 1;
    text-align: center;
  }
}
</style>
