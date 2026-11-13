<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void;
}>();
</script>

<template>
  <header class="admin-header">
    <div class="header-left">
      <button
        class="sidebar-mobile-toggle"
        @click="emit('toggle-sidebar')"
        aria-label="Toggle admin navigation menu"
      >
        <span class="bar"></span>
        <span class="bar"></span>
        <span class="bar"></span>
      </button>

      <div class="title-meta">
        <div class="title-with-pill">
          <h1 class="page-title">{{ title }}</h1>
          <span class="admin-badge">ADMIN</span>
        </div>
        <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      </div>
    </div>

    <div class="header-right">
      <div class="server-badge">
        <span class="pulse-indicator"></span>
        <span class="badge-text">LOCAL SERVER (127.0.0.1)</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem 0;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 1.75rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.sidebar-mobile-toggle {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 38px;
  height: 38px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  padding: 6px;
}

.bar {
  display: block;
  width: 100%;
  height: 2px;
  background-color: var(--text-color);
  border-radius: 2px;
}

.title-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.title-with-pill {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.page-title {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.02em;
}

.admin-badge {
  background: rgba(255, 180, 0, 0.2);
  color: #ffb400;
  border: 1px solid rgba(255, 180, 0, 0.5);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
}

.page-subtitle {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-muted);
}

.server-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(0, 204, 136, 0.08);
  border: 1px solid rgba(0, 204, 136, 0.25);
  padding: 0.4rem 0.75rem;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 0.05em;
}

.pulse-indicator {
  width: 8px;
  height: 8px;
  background-color: var(--color-primary);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--color-primary);
}

@media (max-width: 900px) {
  .sidebar-mobile-toggle {
    display: flex;
  }
}

@media (max-width: 600px) {
  .admin-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }
  .page-title {
    font-size: 1.4rem;
  }
}
</style>
