<script setup lang="ts">
import { RouterLink } from 'vue-router';
</script>

<template>
  <div class="not-found-page">
    <div class="container not-found-card card fade-in">
      <span class="badge badge-dev">SECTOR ERROR 404</span>
      <h1 class="error-code">404</h1>
      <h2 class="error-title">COORDINATES NOT FOUND</h2>
      <p class="error-text">
        The drop zone or sector you requested does not exist or has been cleared from active radar.
      </p>
      <div class="actions">
        <RouterLink to="/" class="btn btn-primary">
          Return To Home Sector
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<style scoped>
.not-found-page {
  min-height: calc(100vh - 250px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4rem 1.5rem;
}

.not-found-card {
  max-width: 560px;
  width: 100%;
  text-align: center;
  padding: 3.5rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.error-code {
  font-size: 5rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--accent-red);
  letter-spacing: 0.1em;
  line-height: 1;
}

.error-title {
  font-size: 1.5rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.error-text {
  color: var(--text-secondary);
  font-size: 0.95rem;
  max-width: 420px;
  line-height: 1.6;
}

.actions {
  margin-top: 1rem;
}
</style>
