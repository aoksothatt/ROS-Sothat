<script setup lang="ts">
import { ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const router = useRouter();
const mobileMenuOpen = ref(false);

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value;
}

function handleLogout() {
  authStore.logout();
  mobileMenuOpen.value = false;
  router.push({ name: 'home' });
}
</script>

<template>
  <header class="navbar-wrapper">
    <div class="container navbar-container">
      <RouterLink to="/" class="brand" @click="mobileMenuOpen = false">
        <span class="brand-badge">P03</span>
        <span class="brand-title">ROS <span class="highlight">SOTHAT</span></span>
      </RouterLink>

      <button
        class="mobile-toggle"
        @click="toggleMobileMenu"
        :aria-expanded="mobileMenuOpen"
        aria-label="Toggle navigation menu"
      >
        <span class="toggle-bar"></span>
        <span class="toggle-bar"></span>
        <span class="toggle-bar"></span>
      </button>

      <nav class="nav-links" :class="{ 'open': mobileMenuOpen }">
        <RouterLink to="/" class="nav-link" @click="mobileMenuOpen = false">Home</RouterLink>
        <a href="/#about" class="nav-link" @click="mobileMenuOpen = false">About</a>
        <a href="/#features" class="nav-link" @click="mobileMenuOpen = false">Features</a>
        <a href="/#announcements" class="nav-link" @click="mobileMenuOpen = false">Announcements</a>
        <a href="/#download" class="nav-link" @click="mobileMenuOpen = false">Download</a>

        <div class="nav-auth">
          <template v-if="authStore.isAuthenticated">
            <RouterLink v-if="authStore.isAdmin" to="/admin" class="btn btn-warning nav-btn admin-badge-btn" @click="mobileMenuOpen = false">
              Admin Portal
            </RouterLink>
            <RouterLink to="/dashboard" class="btn btn-secondary nav-btn" @click="mobileMenuOpen = false">
              Dashboard
            </RouterLink>
            <button class="btn btn-danger nav-btn" @click="handleLogout">
              Logout
            </button>
          </template>
          <template v-else>
            <RouterLink to="/login" class="nav-link auth-link" @click="mobileMenuOpen = false">
              Login
            </RouterLink>
            <RouterLink to="/register" class="btn btn-primary nav-btn" @click="mobileMenuOpen = false">
              Join Island
            </RouterLink>
          </template>
        </div>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.navbar-wrapper {
  background-color: rgba(8, 11, 16, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0.75rem 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

.navbar-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
  font-weight: 900;
  letter-spacing: 0.12em;
  font-size: 1.15rem;
  color: var(--text-primary);
}

.brand-badge {
  background-color: var(--accent-red);
  color: #FFFFFF;
  font-size: 0.65rem;
  font-weight: 800;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  letter-spacing: 0.05em;
}

.highlight {
  color: var(--accent-gold);
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-link {
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  transition: color 0.2s ease;
}

.nav-link:hover, .nav-link.router-link-active {
  color: var(--accent-gold);
}

.nav-auth {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-left: 1rem;
  border-left: 1px solid var(--border-color);
  padding-left: 1.5rem;
}

.nav-btn {
  padding: 0.5rem 1rem;
  font-size: 0.75rem;
}

.mobile-toggle {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  flex-direction: column;
  gap: 5px;
  padding: 0.5rem;
}

.toggle-bar {
  width: 24px;
  height: 2px;
  background-color: var(--text-primary);
  transition: all 0.2s ease;
}

@media (max-width: 860px) {
  .mobile-toggle {
    display: flex;
  }

  .nav-links {
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background-color: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    flex-direction: column;
    padding: 1.5rem;
    gap: 1.25rem;
    align-items: flex-start;
  }

  .nav-links.open {
    display: flex;
  }

  .nav-auth {
    margin-left: 0;
    border-left: none;
    padding-left: 0;
    border-top: 1px solid var(--border-color);
    padding-top: 1.25rem;
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
