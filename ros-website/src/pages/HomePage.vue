<script setup lang="ts">
import { RouterLink } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();

const announcements = [
  {
    id: 1,
    title: 'Phase P03: Tactical Web Ecosystem Online',
    date: 'November 2026',
    category: 'Ecosystem',
    summary: 'The ROS Sothat web portal is now operational for invited players, featuring passwordless email verification, session security, and account provisioning.'
  },
  {
    id: 2,
    title: 'Phase P02.1: Keyed HMAC-SHA256 OTP Remediation',
    date: 'November 2026',
    category: 'Security',
    summary: 'Verification code generation has been upgraded with server-side HMAC-SHA256 keying and 5-attempt challenge isolation to safeguard against offline database dictionary attacks.'
  },
  {
    id: 3,
    title: 'Mercury Protocol & UDP Gateway Architecture',
    date: 'November 2026',
    category: 'Engine Research',
    summary: 'Independent network research on Mercury protocol framing, Blowfish decryption, and LoginApp datagram dispatch successfully validated.'
  }
];

const ecosystemFeatures = [
  {
    title: 'Private Community',
    status: 'Active',
    description: 'An exclusive, closed multiplayer community for 10–20 invited friends playing Rules of Survival Legacy.'
  },
  {
    title: 'Passwordless Email OTP',
    status: 'Active',
    description: 'Instant, secure authentication using 6-digit cryptographic verification codes delivered directly to your inbox.'
  },
  {
    title: 'Diamond Currency Ledger',
    status: 'Backend Ready',
    description: 'Relational, append-only economic ledger tracking diamond transactions with strict overdraft protection.'
  },
  {
    title: 'Tactical Inventory System',
    status: 'Backend Ready',
    description: 'Item catalog management and slot-based inventory systems built directly on the private server foundation.'
  },
  {
    title: 'Mercury Game Gateway',
    status: 'In Development',
    description: 'Low-latency UDP transport layer handling custom server discovery, authentication handshakes, and game rooms.'
  },
  {
    title: 'Player & Companion Launcher',
    status: 'In Development',
    description: 'Dedicated iOS companion app and dashboard for managing stats, inventory, and launching legacy game sessions.'
  }
];
</script>

<template>
  <div class="home-page">
    <!-- Hero Section -->
    <section class="hero-section">
      <div class="hero-overlay"></div>
      <div class="container hero-content">
        <div class="hero-badge fade-in">
          <span class="badge">PRIVATE INVITE-ONLY COMMUNITY</span>
        </div>
        <h1 class="hero-title fade-in">
          THE ISLAND IS <span class="gold-text">WAITING.</span>
        </h1>
        <p class="hero-subtitle fade-in">
          A private Rules of Survival Legacy community. Survive together, compete together, and build your own battlefield.
        </p>

        <div class="hero-actions fade-in">
          <template v-if="authStore.isAuthenticated">
            <RouterLink to="/dashboard" class="btn btn-primary hero-btn">
              Open Player Dashboard
            </RouterLink>
          </template>
          <template v-else>
            <RouterLink to="/register" class="btn btn-primary hero-btn">
              Join The Community
            </RouterLink>
            <a href="#about" class="btn btn-secondary hero-btn">
              Explore ROS Sothat
            </a>
          </template>
        </div>

        <div class="hero-stats-row">
          <div class="hero-stat-card">
            <span class="stat-number">10–20</span>
            <span class="stat-label">Invited Friends</span>
          </div>
          <div class="hero-stat-card">
            <span class="stat-number">100%</span>
            <span class="stat-label">Independent Server</span>
          </div>
          <div class="hero-stat-card">
            <span class="stat-number">Legacy</span>
            <span class="stat-label">Original RoS Engine</span>
          </div>
        </div>
      </div>
    </section>

    <!-- About Section -->
    <section id="about" class="section about-section">
      <div class="container">
        <div class="section-header">
          <span class="badge">PROJECT SCOPE</span>
          <h2 class="section-title">ABOUT ROS SOTHAT</h2>
          <div class="title-underline"></div>
        </div>

        <div class="about-grid">
          <div class="about-card card">
            <div class="about-icon">&#128737;</div>
            <h3 class="about-card-title">Not Rebuilding the Game</h3>
            <p class="about-card-text">
              The original Rules of Survival Legacy client already exists inside our preserved iOS archive. We are developing the private server, account ecosystem, and community platform around it.
            </p>
          </div>

          <div class="about-card card">
            <div class="about-icon">&#9874;</div>
            <h3 class="about-card-title">Invite-Only Access</h3>
            <p class="about-card-text">
              Built exclusively for a small private circle of invited friends. Access is restricted to verified email addresses, free from corporate monetization or public griefing.
            </p>
          </div>

          <div class="about-card card">
            <div class="about-icon">&#128274;</div>
            <h3 class="about-card-title">Modern Security Architecture</h3>
            <p class="about-card-text">
              Zero passwords to remember or lose. Fast 6-digit email OTP login backed by HMAC-SHA256 verification, sliding-window rate limiters, and complete attempt lockout isolation.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Features & Roadmap Section -->
    <section id="features" class="section features-section">
      <div class="container">
        <div class="section-header">
          <span class="badge">ECOSYSTEM ROADMAP</span>
          <h2 class="section-title">PLANNED PLATFORM FEATURES</h2>
          <div class="title-underline"></div>
        </div>

        <div class="features-grid">
          <div
            v-for="feat in ecosystemFeatures"
            :key="feat.title"
            class="card feature-card"
          >
            <div class="feature-top">
              <h3 class="feature-title">{{ feat.title }}</h3>
              <span
                class="badge"
                :class="{
                  'badge-status': feat.status === 'Active',
                  'badge-dev': feat.status === 'In Development'
                }"
              >
                {{ feat.status }}
              </span>
            </div>
            <p class="feature-desc">{{ feat.description }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Announcements Section -->
    <section id="announcements" class="section announcements-section">
      <div class="container">
        <div class="section-header">
          <span class="badge">DEVELOPMENT UPDATES</span>
          <h2 class="section-title">COMMUNITY ANNOUNCEMENTS</h2>
          <div class="title-underline"></div>
        </div>

        <div class="announcements-list">
          <article
            v-for="item in announcements"
            :key="item.id"
            class="card announcement-card"
          >
            <div class="announcement-meta">
              <span class="badge">{{ item.category }}</span>
              <time class="announcement-date">{{ item.date }}</time>
            </div>
            <h3 class="announcement-title">{{ item.title }}</h3>
            <p class="announcement-summary">{{ item.summary }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- Download Section -->
    <section id="download" class="section download-section">
      <div class="container">
        <div class="card download-card">
          <span class="badge badge-dev">DISTRIBUTION PREPARATION</span>
          <h2 class="download-title">GAME CLIENT DISTRIBUTION</h2>
          <p class="download-text">
            Game distribution for invited friends is currently in preparation. Our Ad Hoc distribution research verifies that the original iOS client can be provisioned directly to registered devices via an Apple installation manifest.
          </p>
          <div class="download-notice">
            <span class="notice-icon">&#9888;</span>
            <div class="notice-body">
              <strong>Notice:</strong> The original game IPA is not directly downloadable via public HTTP links. Once your email is registered and your device is enrolled in the private Ad Hoc profile, distribution handoff will become available through the ROS Sothat companion launcher.
            </div>
          </div>
          <div class="download-cta">
            <RouterLink to="/register" class="btn btn-primary">
              Register To Receive Updates
            </RouterLink>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero-section {
  position: relative;
  min-height: 80vh;
  display: flex;
  align-items: center;
  padding: 6rem 0 4rem;
  background: radial-gradient(circle at 50% 20%, #151E29 0%, #080B10 80%);
  border-bottom: 1px solid var(--border-color);
  text-align: center;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.hero-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 900px;
}

.hero-title {
  font-size: 3.5rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  line-height: 1.1;
  margin: 1.25rem 0 1rem;
  text-transform: uppercase;
}

.gold-text {
  color: var(--accent-gold);
  text-shadow: 0 0 30px rgba(215, 168, 75, 0.4);
}

.hero-subtitle {
  font-size: 1.2rem;
  color: var(--text-secondary);
  max-width: 720px;
  line-height: 1.6;
  margin-bottom: 2.25rem;
}

.hero-actions {
  display: flex;
  gap: 1.25rem;
  margin-bottom: 3.5rem;
  flex-wrap: wrap;
  justify-content: center;
}

.hero-btn {
  padding: 0.9rem 2rem;
  font-size: 0.95rem;
}

.hero-stats-row {
  display: flex;
  gap: 2rem;
  border-top: 1px solid var(--border-color);
  padding-top: 2rem;
  width: 100%;
  justify-content: center;
  flex-wrap: wrap;
}

.hero-stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 140px;
}

.stat-number {
  font-size: 2rem;
  font-weight: 900;
  color: var(--text-primary);
  letter-spacing: 0.05em;
}

.stat-label {
  font-size: 0.75rem;
  color: var(--accent-gold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
}

.section {
  padding: 5rem 0;
}

.section-header {
  text-align: center;
  margin-bottom: 3.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.title-underline {
  width: 60px;
  height: 3px;
  background-color: var(--accent-gold);
  border-radius: 2px;
}

.about-grid, .features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.75rem;
}

.about-card {
  padding: 2.25rem;
}

.about-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.about-card-title {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.75rem;
  letter-spacing: 0.04em;
}

.about-card-text {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.6;
}

.feature-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.feature-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  gap: 1rem;
}

.feature-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-primary);
}

.feature-desc {
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.5;
}

.announcements-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-width: 900px;
  margin: 0 auto;
}

.announcement-card {
  padding: 1.75rem;
}

.announcement-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.announcement-date {
  color: var(--text-muted);
  font-size: 0.8rem;
  font-weight: 600;
}

.announcement-title {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.announcement-summary {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.6;
}

.download-card {
  max-width: 840px;
  margin: 0 auto;
  text-align: center;
  padding: 3rem 2.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  border-color: rgba(215, 168, 75, 0.3);
}

.download-title {
  font-size: 1.8rem;
  font-weight: 900;
  letter-spacing: 0.08em;
}

.download-text {
  color: var(--text-secondary);
  font-size: 0.95rem;
  max-width: 640px;
  line-height: 1.6;
}

.download-notice {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  background-color: rgba(215, 168, 75, 0.08);
  border: 1px solid rgba(215, 168, 75, 0.25);
  border-radius: 4px;
  padding: 1rem 1.25rem;
  text-align: left;
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 1rem 0;
}

.notice-icon {
  font-size: 1.25rem;
  color: var(--accent-gold);
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 2.25rem;
  }
  .hero-subtitle {
    font-size: 1rem;
  }
  .hero-stats-row {
    gap: 1.25rem;
  }
}
</style>
