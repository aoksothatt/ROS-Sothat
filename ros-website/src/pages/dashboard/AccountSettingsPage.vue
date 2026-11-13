<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import DashboardLayout from '@/components/dashboard/DashboardLayout.vue';

const router = useRouter();
const authStore = useAuthStore();

function handleLogout() {
  authStore.logout();
  router.push({ name: 'login' });
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return 'Never';
  try {
    return new Date(iso).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return iso;
  }
}
</script>

<template>
  <DashboardLayout
    title="Account & Security Settings"
    subtitle="Active session parameters, authentication controls, and security posture."
  >
    <div class="settings-content fade-in">
      <!-- Section 1: Account Credentials Summary -->
      <section class="card settings-card">
        <h3 class="card-title">OPERATOR IDENTITY & CREDENTIALS</h3>
        <p class="card-desc">
          Verified identification records registered on the ROS Sothat private database.
        </p>

        <div class="settings-fields-grid">
          <div class="field-item">
            <span class="field-label">Username / Callsign</span>
            <span class="field-value">{{ authStore.user?.username }}</span>
          </div>

          <div class="field-item">
            <span class="field-label">Account GID</span>
            <span class="field-value mono">#{{ authStore.user?.id }}</span>
          </div>

          <div class="field-item">
            <span class="field-label">Email Address</span>
            <span class="field-value">{{ authStore.user?.email || 'None Registered' }}</span>
          </div>

          <div class="field-item">
            <span class="field-label">Security Role</span>
            <span class="field-value badge" :class="{ 'badge-dev': authStore.user?.role === 'admin' }">
              {{ authStore.user?.role.toUpperCase() }}
            </span>
          </div>

          <div class="field-item">
            <span class="field-label">Account Created</span>
            <span class="field-value">{{ formatDate(authStore.user?.created_at) }}</span>
          </div>

          <div class="field-item">
            <span class="field-label">Last Active Session</span>
            <span class="field-value">{{ formatDate(authStore.user?.last_login) }}</span>
          </div>
        </div>
      </section>

      <!-- Section 2: Session Security Posture -->
      <section class="card settings-card">
        <h3 class="card-title">SESSION & STORAGE ARCHITECTURE</h3>
        <div class="session-info-box">
          <div class="info-row">
            <span class="info-label">Active Token Type:</span>
            <span class="info-val mono">HMAC-SHA256 Signed JSON Web Token (Bearer)</span>
          </div>
          <div class="info-row">
            <span class="info-label">Client Storage:</span>
            <span class="info-val mono">Browser sessionStorage (Isolated to current tab)</span>
          </div>
          <div class="info-row">
            <span class="info-label">Automatic Expiration:</span>
            <span class="info-val">Sessions automatically terminate when tab or browser closes.</span>
          </div>
        </div>

        <div class="security-advisory">
          <span class="adv-icon">⚠️</span>
          <p class="adv-text">
            <strong>Security Notice:</strong> The private web platform uses client-side Web Storage with scoped Bearer authentication. For maximal operational security on shared devices, always terminate your session using the Logout button below when finished.
          </p>
        </div>
      </section>

      <!-- Section 3: Upcoming Security Features (Marked In Development) -->
      <section class="card settings-card">
        <h3 class="card-title">PLANNED SECURITY CAPABILITIES</h3>
        <p class="card-desc">
          Upcoming features currently in engineering roadmap.
        </p>

        <div class="features-list">
          <div class="feature-item">
            <div class="feat-info">
              <span class="feat-name">Email Address Migration</span>
              <span class="feat-desc">Transfer verified account ownership to an updated email with double-challenge confirmation.</span>
            </div>
            <span class="badge badge-dev">IN DEVELOPMENT</span>
          </div>

          <div class="feature-item">
            <div class="feat-info">
              <span class="feat-name">Passkey / WebAuthn Hardware Keys</span>
              <span class="feat-desc">FIDO2 passwordless authentication using Touch ID, Windows Hello, or physical YubiKeys.</span>
            </div>
            <span class="badge badge-dev">IN DEVELOPMENT</span>
          </div>

          <div class="feature-item">
            <div class="feat-info">
              <span class="feat-name">Client Device Hardware Enrollment</span>
              <span class="feat-desc">Link iOS hardware UUID / device identifier for one-click game launcher execution.</span>
            </div>
            <span class="badge badge-dev">IN DEVELOPMENT</span>
          </div>
        </div>
      </section>

      <!-- Section 4: Session Termination -->
      <section class="card settings-card logout-section">
        <h3 class="card-title">SESSION TERMINATION</h3>
        <p class="card-desc">
          Disconnect from the private island server and clear your active authentication token from memory.
        </p>
        <button class="btn btn-secondary logout-btn" @click="handleLogout">
          <span class="icon">⏻</span>
          <span>Logout Active Session</span>
        </button>
      </section>
    </div>
  </DashboardLayout>
</template>

<style scoped>
.settings-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.settings-card {
  padding: 1.75rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.card-title {
  font-size: 0.95rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--text-primary);
  margin: 0;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.card-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
}

.settings-fields-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.25rem;
}

.field-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background-color: var(--bg-secondary);
  padding: 0.85rem 1rem;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.field-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 600;
}

.field-value {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-primary);
}

.field-value.mono {
  font-family: var(--font-mono);
}

.field-value.badge {
  align-self: flex-start;
  margin-top: 0.2rem;
}

.session-info-box {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  background-color: var(--bg-secondary);
  padding: 1rem 1.25rem;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
  gap: 1rem;
}

.info-label {
  color: var(--text-secondary);
  font-weight: 600;
}

.info-val {
  color: var(--text-primary);
}

.info-val.mono {
  font-family: var(--font-mono);
}

.security-advisory {
  display: flex;
  align-items: center;
  gap: 1rem;
  background-color: rgba(215, 168, 75, 0.08);
  border: 1px solid rgba(215, 168, 75, 0.25);
  padding: 0.85rem 1rem;
  border-radius: 4px;
}

.adv-icon {
  font-size: 1.3rem;
  flex-shrink: 0;
}

.adv-text {
  font-size: 0.85rem;
  color: var(--text-primary);
  margin: 0;
  line-height: 1.5;
}

.features-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.feature-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.85rem 1rem;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  gap: 1rem;
}

.feat-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.feat-name {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-primary);
}

.feat-desc {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.logout-section {
  align-items: flex-start;
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.75rem;
}

@media (max-width: 600px) {
  .info-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.2rem;
  }
  
  .feature-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
