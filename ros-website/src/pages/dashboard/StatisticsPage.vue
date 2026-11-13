<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { playerService } from '@/services/player';
import type { CharacterProfile } from '@/types/dashboard';
import DashboardLayout from '@/components/dashboard/DashboardLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const character = ref<CharacterProfile | null>(null);
const loading = ref(true);
const errorMessage = ref('');

onMounted(async () => {
  if (!authStore.token) return;
  loading.value = true;
  errorMessage.value = '';
  try {
    character.value = await playerService.getMyCharacter(authStore.token);
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to load player combat statistics.';
  } finally {
    loading.value = false;
  }
});

const winRate = computed(() => {
  if (!character.value || !character.value.stats || character.value.stats.total_matches === 0) {
    return '0.0%';
  }
  const rate = (character.value.stats.total_wins / character.value.stats.total_matches) * 100;
  return `${rate.toFixed(1)}%`;
});

const killRatio = computed(() => {
  if (!character.value || !character.value.stats || character.value.stats.total_matches === 0) {
    return '0.0';
  }
  const ratio = character.value.stats.total_kills / character.value.stats.total_matches;
  return ratio.toFixed(2);
});
</script>

<template>
  <DashboardLayout
    title="Island Combat Records"
    subtitle="Combat kill counts, match telemetry, and survival statistics."
  >
    <div v-if="loading">
      <LoadingState message="Querying combat statistics and match telemetry..." />
    </div>

    <div v-else class="stats-content fade-in">
      <div v-if="errorMessage" class="alert alert-danger" role="alert">
        {{ errorMessage }}
      </div>

      <!-- If character does not exist -->
      <div v-if="!character" class="card">
        <EmptyState
          icon="🎯"
          title="STATISTICS UNAVAILABLE"
          description="A deployed character profile is required to accumulate combat records. Please initialize your character on the Profile page."
        />
      </div>

      <template v-else>
        <!-- Honest Development Status Banner -->
        <div class="card dev-status-banner">
          <div class="dev-banner-left">
            <span class="badge badge-dev">MATCH TELEMETRY PENDING</span>
            <h3 class="banner-title">Multiplayer Match Tracking In Development</h3>
            <p class="banner-text">
              The metrics below represent actual database records for your character. Because multiplayer dedicated server rooms are in active engineering, your combat statistics remain at initial baseline. Real match stats will populate dynamically once server match resolution is activated.
            </p>
          </div>
          <div class="dev-banner-icon">&#9881;</div>
        </div>

        <!-- 4 Primary Real Stat Cards -->
        <div class="stats-grid">
          <div class="card stat-card">
            <div class="stat-top">
              <span class="stat-label">TOTAL MATCHES</span>
              <span class="stat-icon">🎮</span>
            </div>
            <div class="stat-value">{{ character.stats.total_matches }}</div>
            <span class="stat-note">Survivals Attempted</span>
          </div>

          <div class="card stat-card">
            <div class="stat-top">
              <span class="stat-label">VICTORIES / WINS</span>
              <span class="stat-icon">🏆</span>
            </div>
            <div class="stat-value gold">{{ character.stats.total_wins }}</div>
            <span class="stat-note">Last Man Standing</span>
          </div>

          <div class="card stat-card">
            <div class="stat-top">
              <span class="stat-label">CONFIRMED KILLS</span>
              <span class="stat-icon">🎯</span>
            </div>
            <div class="stat-value">{{ character.stats.total_kills }}</div>
            <span class="stat-note">Eliminations</span>
          </div>

          <div class="card stat-card">
            <div class="stat-top">
              <span class="stat-label">DAMAGE DEALT</span>
              <span class="stat-icon">💥</span>
            </div>
            <div class="stat-value">{{ character.stats.damage_dealt.toLocaleString() }}</div>
            <span class="stat-note">Total Hit Points</span>
          </div>
        </div>

        <!-- Secondary Calculated Metrics -->
        <div class="card derived-metrics-card">
          <h4 class="card-subtitle">DERIVED PERFORMANCE RATIOS</h4>
          <div class="derived-grid">
            <div class="derived-item">
              <span class="d-label">Win Percentage</span>
              <span class="d-val">{{ winRate }}</span>
              <span class="d-desc">Formula: (Wins ÷ Matches) × 100</span>
            </div>
            <div class="derived-item">
              <span class="d-label">Average Kills / Match</span>
              <span class="d-val">{{ killRatio }}</span>
              <span class="d-desc">Formula: Kills ÷ Matches</span>
            </div>
            <div class="derived-item">
              <span class="d-label">Survival Grade</span>
              <span class="d-val gold">RECRUIT</span>
              <span class="d-desc">Initial Placement Bracket</span>
            </div>
          </div>
        </div>

        <!-- Clear Honest Notice -->
        <div class="card honest-notice">
          <span class="notice-icon">📋</span>
          <p class="notice-text">
            <strong>Authenticity Commitment:</strong> Player statistics will appear here when match tracking is available. ROS Sothat does not fabricate match records, fake kill ratios, or invent imaginary combat charts.
          </p>
        </div>
      </template>
    </div>
  </DashboardLayout>
</template>

<style scoped>
.stats-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.dev-status-banner {
  padding: 1.5rem 1.75rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1.5rem;
  background: linear-gradient(135deg, var(--bg-card) 0%, #151D26 100%);
  border-left: 4px solid var(--accent-red);
}

.dev-banner-left {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.banner-title {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
  text-transform: uppercase;
}

.banner-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
  max-width: 800px;
}

.dev-banner-icon {
  font-size: 2.5rem;
  opacity: 0.3;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem;
}

.stat-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  border-radius: 6px;
}

.stat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-label {
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
}

.stat-icon {
  font-size: 1.25rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--text-primary);
  line-height: 1;
}

.stat-value.gold {
  color: var(--accent-gold);
}

.stat-note {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.derived-metrics-card {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.card-subtitle {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-secondary);
  letter-spacing: 0.08em;
  margin: 0;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.derived-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1.25rem;
}

.derived-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background-color: var(--bg-secondary);
  padding: 1rem;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.d-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.d-val {
  font-size: 1.4rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--text-primary);
}

.d-val.gold {
  color: var(--accent-gold);
}

.d-desc {
  font-size: 0.7rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.honest-notice {
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 0.85rem;
  background-color: rgba(38, 52, 66, 0.3);
  border: 1px solid var(--border-color);
}

.notice-icon {
  font-size: 1.3rem;
  flex-shrink: 0;
}

.notice-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
  margin: 0;
}

.notice-text strong {
  color: var(--text-primary);
}
</style>
