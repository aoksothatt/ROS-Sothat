<script setup lang="ts">
defineProps<{
  icon?: string;
  title: string;
  description: string;
}>();
</script>

<template>
  <div class="empty-state-card card fade-in">
    <div class="empty-icon">{{ icon || '📦' }}</div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-desc">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action"></slot>
    </div>
  </div>
</template>

<style scoped>
.empty-state-card {
  text-align: center;
  padding: 3.5rem 2rem;
  background-color: var(--bg-card);
  border: 1px dashed var(--border-color);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 0.5rem;
  filter: drop-shadow(0 2px 8px rgba(0, 0, 0, 0.4));
}

.empty-title {
  font-size: 1.25rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-primary);
}

.empty-desc {
  font-size: 0.9rem;
  color: var(--text-secondary);
  max-width: 440px;
  line-height: 1.6;
}

.empty-action {
  margin-top: 1rem;
}
</style>
