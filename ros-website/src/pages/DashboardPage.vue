<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const authStore = useAuthStore();

onMounted(async () => {
  if (!authStore.user) {
    await authStore.initSession();
  }
});

function handleLogout() {
  authStore.logout();
  router.push({ name: 'login' });
}

function formatDate(isoString: string | null) {
  if (!isoString) return 'Never';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return isoString;
  }
}
</script>

<template>
  <div class="dashboard-page">
    <div class="container">
      <!-- Loading State -->
      <div v-if="authStore.loading" class="card loading-card">
        <div class="spinner"></div>
        <p>Loading tactical profile...</p>
      </div>

      <!-- Dashboard Content -->
      <div v-else-if="authStore.user" class="dashboard-content fade-in">
        <!-- Profile Banner -->
        <div class="card profile-banner">
          <div class="banner-left">
            <div class="avatar-badge">
              <span>{{ authStore.user.username.slice(0, 2).toUpperCase() }}</span>
            </div>
            <div class="banner-text">
              <div class="role-badge-row">
                <span
                  class="badge"
                  :class="{ 'badge-dev': authStore.user.role === 'admin' }"
                >
                  {{ authStore.user.role.toUpperCase() }}
                </span>
                <span
                  class="badge"
                  :class="authStore.user.is_banned ? 'badge-dev' : 'badge-status'"
                >
                  {{ authStore.user.is_banned ? 'SUSPENDED' : 'ACTIVE OPERATOR' }}
                </span>
              </div>
              <h1 class="player-name">{{ authStore.user.username }}</h1>
              <p class="player-email">{{ authStore.user.email || 'No email attached' }}</p>
            </div>
          </div>

          <div class="banner-actions">
            <button class="btn btn-secondary" @click="handleLogout">
              Logout Session
            </button>
          </div>
        </div>

        <!-- Verified Account Telemetry Grid -->
        <div class="telemetry-grid">
          <div class="card telemetry-card">
            <span class="telemetry-label">Account Identifier</span>
            <span class="telemetry-value">#{{ authStore.user.id }}</span>
            <span class="telemetry-note">Unique Database GID</span>
          </div>

          <div class="card telemetry-card">
            <span class="telemetry-label">Account Registered</span>
            <span class="telemetry-value small-text">{{ formatDate(authStore.user.created_at) }}</span>
            <span class="telemetry-note">Creation Timestamp</span>
          </div>

          <div class="card telemetry-card">
            <span class="telemetry-label">Last Authenticated</span>
            <span class="telemetry-value small-text">{{ formatDate(authStore.user.last_login) }}</span>
            <span class="telemetry-note">Active Bearer Session</span>
          </div>

          <div class="card telemetry-card">
            <span class="telemetry-label">Game Character</span>
            <span class="telemetry-value" :class="authStore.user.has_character ? 'gold' : ''">
              {{ authStore.user.has_character ? 'PROVISIONED' : 'UNASSIGNED' }}
            </span>
            <span class="telemetry-note">Legacy Character Link</span>
          </div>
        </div>

        <!-- Future Ecosystem Features (Marked In Development) -->
        <h2 class="section-title-sub">ECOSYSTEM CAPABILITIES</h2>

        <div class="feature-placeholders-grid">
          <div class="card placeholder-card">
            <div class="card-badge-header">
              <span class="card-icon">&#128142;</span>
              <span class="badge badge-dev">IN DEVELOPMENT</span>
            </div>
            <h3 class="placeholder-title">Diamond Currency Vault</h3>
            <p class="placeholder-desc">
              Append-only transaction ledger balance viewing and administrative diamond grants.
            </p>
            <span class="planned-tag">Target: Phase P04 Player Dashboard</span>
          </div>

          <div class="card placeholder-card">
            <div class="card-badge-header">
              <span class="card-icon">&#127898;</span>
              <span class="badge badge-dev">IN DEVELOPMENT</span>
            </div>
            <h3 class="placeholder-title">Tactical Armory & Inventory</h3>
            <p class="placeholder-desc">
              Inspect weapon skins, parachute gear, consumable supplies, and outfit slot configurations.
            </p>
            <span class="planned-tag">Target: Phase P04 Player Dashboard</span>
          </div>

          <div class="card placeholder-card">
            <div class="card-badge-header">
              <span class="card-icon">&#127919;</span>
              <span class="badge badge-dev">IN DEVELOPMENT</span>
            </div>
            <h3 class="placeholder-title">Matchmaking & Combat Records</h3>
            <p class="placeholder-desc">
              Real-time match queue status, combat kill ratios, and island survival rankings.
            </p>
            <span class="planned-tag">Target: Future Multiplayer Phase</span>
          </div>

          <div class="card placeholder-card">
            <div class="card-badge-header">
              <span class="card-icon">&#128241;</span>
              <span class="badge badge-dev">IN DEVELOPMENT</span>
            </div>
            <h3 class="placeholder-title">iOS Companion Launcher</h3>
            <p class="placeholder-desc">
              Ad Hoc distribution handoff, device UDID enrollment, and one-click game execution.
            </p>
            <span class="planned-tag">Target: Phase P06 iOS Launcher</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-page {
  padding: 3rem 0 5rem;
  min-height: calc(100vh - 200px);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.loading-card {
  text-align: center;
  padding: 4rem 2rem;
  color: var(--text-secondary);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-gold);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.profile-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2.25rem;
  margin-bottom: 2rem;
  background: linear-gradient(135deg, #151E29 0%, #101720 100%);
  border-color: rgba(215, 168, 75, 0.3);
  flex-wrap: wrap;
  gap: 1.5rem;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.avatar-badge {
  width: 68px;
  height: 68px;
  border-radius: 8px;
  background: linear-gradient(135deg, #D7A84B 0%, #8E3023 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 900;
  color: #080B10;
  border: 2px solid var(--accent-gold);
  box-shadow: 0 4px 16px rgba(215, 168, 75, 0.3);
}

.role-badge-row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.3rem;
}

.player-name {
  font-size: 1.6rem;
  font-weight: 900;
  letter-spacing: 0.05em;
  color: var(--text-primary);
}

.player-email {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.telemetry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.25rem;
  margin-bottom: 3.5rem;
}

.telemetry-card {
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
}

.telemetry-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin-bottom: 0.5rem;
}

.telemetry-value {
  font-size: 1.4rem;
  font-weight: 900;
  color: var(--text-primary);
  margin-bottom: 0.3rem;
}

.telemetry-value.gold {
  color: var(--accent-gold);
}

.telemetry-value.small-text {
  font-size: 0.95rem;
  font-weight: 700;
}

.telemetry-note {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.section-title-sub {
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--accent-gold);
  margin-bottom: 1.5rem;
}

.feature-placeholders-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.5rem;
}

.placeholder-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-style: dashed;
  border-color: rgba(38, 52, 66, 0.8);
  opacity: 0.9;
}

.placeholder-card:hover {
  border-color: var(--accent-gold);
  border-style: solid;
  opacity: 1;
}

.card-badge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-icon {
  font-size: 1.5rem;
}

.placeholder-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.placeholder-desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  line-height: 1.5;
  margin-bottom: 1.25rem;
}

.planned-tag {
  font-size: 0.75rem;
  color: var(--accent-gold);
  font-weight: 600;
}

@media (max-width: 768px) {
  .profile-banner {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
