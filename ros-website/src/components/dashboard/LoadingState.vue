<script setup lang="ts">
defineProps<{
  message?: string;
}>();
</script>

<template>
  <div class="loading-state card fade-in">
    <div class="spinner"></div>
    <p class="loading-text">{{ message || 'Querying tactical island servers...' }}</p>
  </div>
</template>

<style scoped>
.loading-state {
  text-align: center;
  padding: 4rem 2rem;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1.25rem;
}

.spinner {
  width: 44px;
  height: 44px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-gold);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: var(--text-secondary);
  font-size: 0.9rem;
  letter-spacing: 0.05em;
  font-family: var(--font-mono);
}
</style>
