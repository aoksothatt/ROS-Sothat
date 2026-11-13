<script setup lang="ts">
const currentYear = new Date().getFullYear();
</script>

<template>
  <footer class="footer-wrapper">
    <div class="container footer-content">
      <div class="footer-col brand-col">
        <div class="brand">
          <span class="brand-title">ROS <span class="highlight">SOTHAT</span></span>
        </div>
        <p class="tagline">
          Private Rules of Survival Legacy multiplayer community and independent research platform.
        </p>
        <div class="disclaimer">
          Independent community project. Not affiliated with, endorsed by, or connected to NetEase Games or original copyright holders.
        </div>
      </div>

      <div class="footer-col">
        <h4 class="col-title">Navigation</h4>
        <ul class="col-links">
          <li><RouterLink to="/">Home</RouterLink></li>
          <li><a href="/#about">About Community</a></li>
          <li><a href="/#features">Roadmap & Features</a></li>
          <li><a href="/#announcements">Announcements</a></li>
          <li><a href="/#download">Download Status</a></li>
        </ul>
      </div>

      <div class="footer-col">
        <h4 class="col-title">Player Access</h4>
        <ul class="col-links">
          <li><RouterLink to="/login">Player Login</RouterLink></li>
          <li><RouterLink to="/register">Request Registration</RouterLink></li>
          <li><RouterLink to="/dashboard">Player Dashboard</RouterLink></li>
        </ul>
      </div>

      <div class="footer-col">
        <h4 class="col-title">Development Status</h4>
        <div class="status-card">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">Phase P03 Local Active</span>
          </div>
          <p class="status-note">
            Multiplayer ecosystem in active local development. Closed invite-only access for friends.
          </p>
        </div>
      </div>
    </div>

    <div class="footer-bottom">
      <div class="container bottom-content">
        <span>&copy; {{ currentYear }} ROS Sothat Project. All rights reserved.</span>
        <span>Environment: Local Research & Development</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer-wrapper {
  background-color: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  padding: 3.5rem 0 1.5rem;
  margin-top: 5rem;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.footer-content {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1.5fr;
  gap: 2.5rem;
  margin-bottom: 2.5rem;
}

.brand-title {
  font-size: 1.2rem;
  font-weight: 900;
  letter-spacing: 0.1em;
  color: var(--text-primary);
}

.highlight {
  color: var(--accent-gold);
}

.tagline {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin: 0.75rem 0;
  line-height: 1.5;
}

.disclaimer {
  color: var(--text-muted);
  font-size: 0.75rem;
  line-height: 1.4;
}

.col-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent-gold);
  margin-bottom: 1rem;
}

.col-links {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.col-links a {
  color: var(--text-secondary);
  font-size: 0.85rem;
  transition: color 0.2s ease;
}

.col-links a:hover {
  color: var(--accent-gold);
}

.status-card {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 1rem;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #34D399;
  box-shadow: 0 0 8px #34D399;
}

.status-text {
  font-size: 0.8rem;
  font-weight: 700;
  color: #34D399;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-note {
  font-size: 0.75rem;
  color: var(--text-muted);
  line-height: 1.4;
}

.footer-bottom {
  border-top: 1px solid var(--border-color);
  padding-top: 1.5rem;
  color: var(--text-muted);
  font-size: 0.75rem;
}

.bottom-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

@media (max-width: 900px) {
  .footer-content {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 600px) {
  .footer-content {
    grid-template-columns: 1fr;
  }
}
</style>
