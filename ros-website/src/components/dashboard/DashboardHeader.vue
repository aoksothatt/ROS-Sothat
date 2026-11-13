<script setup lang="ts">
import { RouterLink } from 'vue-router';
import type { CharacterProfile } from '@/types/dashboard';

defineProps<{
  title: string;
  subtitle?: string;
  character: CharacterProfile | null;
}>();

const emit = defineEmits<{
  (e: 'toggleSidebar'): void;
}>();
</script>

<template>
  <header class="dashboard-header card">
    <div class="header-left">
      <button
        class="sidebar-toggle-btn"
        @click="emit('toggleSidebar')"
        aria-label="Toggle Dashboard Menu"
      >
        <span class="bar"></span>
        <span class="bar"></span>
        <span class="bar"></span>
      </button>
      <div class="title-wrap">
        <h1 class="header-title">{{ title }}</h1>
        <p v-if="subtitle" class="header-subtitle">{{ subtitle }}</p>
      </div>
    </div>

    <!-- Quick Currency Vault Pills -->
    <div v-if="character" class="header-currencies">
      <RouterLink to="/dashboard/wallet" class="currency-pill diamonds-pill" title="View Diamond Wallet">
        <span class="curr-icon">💎</span>
        <span class="curr-val">{{ character.diamonds.toLocaleString() }}</span>
        <span class="curr-label">Diamonds</span>
      </RouterLink>

      <div class="currency-pill gold-pill" title="Character Gold Balance">
        <span class="curr-icon">🪙</span>
        <span class="curr-val">{{ character.gold.toLocaleString() }}</span>
        <span class="curr-label">Gold</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.dashboard-header {
  padding: 1.25rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.sidebar-toggle-btn {
  display: none;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  padding: 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  flex-direction: column;
  gap: 4px;
}

.bar {
  width: 18px;
  height: 2px;
  background-color: var(--text-primary);
}

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.header-title {
  font-size: 1.4rem;
  font-weight: 900;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin: 0;
  color: var(--text-primary);
}

.header-subtitle {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
}

.header-currencies {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.currency-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.4rem 0.85rem;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  text-decoration: none;
  transition: all 0.2s ease;
}

.diamonds-pill {
  border-color: rgba(215, 168, 75, 0.4);
}

.diamonds-pill:hover {
  border-color: var(--accent-gold);
  background-color: #1A2433;
  transform: translateY(-1px);
}

.curr-icon {
  font-size: 1rem;
}

.curr-val {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 0.95rem;
  color: var(--accent-gold);
}

.gold-pill .curr-val {
  color: #E2B755;
}

.curr-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

@media (max-width: 900px) {
  .sidebar-toggle-btn {
    display: flex;
  }
}

@media (max-width: 600px) {
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-currencies {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
