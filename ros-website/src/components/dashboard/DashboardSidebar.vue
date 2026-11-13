<script setup lang="ts">
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

defineProps<{
  mobileOpen?: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const navItems = [
  { name: 'Overview', path: '/dashboard', icon: '📊', exact: true },
  { name: 'My Profile', path: '/dashboard/profile', icon: '🎖️', exact: false },
  { name: 'Diamond Wallet', path: '/dashboard/wallet', icon: '💎', exact: false },
  { name: 'Inventory', path: '/dashboard/inventory', icon: '🎒', exact: false },
  { name: 'Statistics', path: '/dashboard/statistics', icon: '🎯', exact: false },
  { name: 'Settings', path: '/dashboard/settings', icon: '⚙️', exact: false }
];

function isActive(item: typeof navItems[0]) {
  if (item.exact) {
    return route.path === item.path;
  }
  return route.path.startsWith(item.path);
}

function handleLogout() {
  emit('close');
  authStore.logout();
  router.push({ name: 'login' });
}
</script>

<template>
  <aside class="dashboard-sidebar" :class="{ 'mobile-open': mobileOpen }">
    <!-- User Telemetry Widget in Sidebar -->
    <div class="sidebar-user-card">
      <div class="user-avatar">
        <span>{{ authStore.user?.username.slice(0, 2).toUpperCase() || 'OP' }}</span>
      </div>
      <div class="user-meta">
        <span class="user-callsign">{{ authStore.user?.username || 'Operator' }}</span>
        <span class="user-role-badge badge" :class="{ 'badge-dev': authStore.user?.role === 'admin' }">
          {{ authStore.user?.role.toUpperCase() || 'PLAYER' }}
        </span>
      </div>
    </div>

    <!-- Navigation Menu -->
    <nav class="sidebar-nav">
      <div class="nav-section-title">COMMAND CENTER</div>
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.path" class="nav-item">
          <RouterLink
            :to="item.path"
            class="nav-link"
            :class="{ 'active': isActive(item) }"
            @click="emit('close')"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-text">{{ item.name }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>

    <!-- Sidebar Bottom Actions -->
    <div class="sidebar-footer">
      <button class="btn btn-secondary btn-block logout-btn" @click="handleLogout">
        <span class="logout-icon">⏻</span>
        <span>Logout Session</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.dashboard-sidebar {
  width: 260px;
  background-color: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  gap: 1.5rem;
  min-height: calc(100vh - 70px);
}

.sidebar-user-card {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 1rem;
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 6px;
}

.user-avatar {
  width: 44px;
  height: 44px;
  background: linear-gradient(135deg, var(--bg-secondary), #1C2836);
  border: 1px solid var(--accent-gold);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 900;
  color: var(--accent-gold);
  font-family: var(--font-mono);
  font-size: 1.1rem;
  flex-shrink: 0;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow: hidden;
}

.user-callsign {
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role-badge {
  font-size: 0.65rem;
  padding: 0.15rem 0.4rem;
  align-self: flex-start;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  flex: 1;
}

.nav-section-title {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--text-secondary);
  padding-left: 0.5rem;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.nav-link:hover {
  background-color: var(--bg-card);
  color: var(--text-primary);
}

.nav-link.active {
  background-color: var(--bg-card);
  color: var(--accent-gold);
  border-color: rgba(215, 168, 75, 0.4);
  box-shadow: inset 3px 0 0 var(--accent-gold);
}

.nav-icon {
  font-size: 1.15rem;
}

.sidebar-footer {
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

@media (max-width: 900px) {
  .dashboard-sidebar {
    position: fixed;
    top: 70px;
    left: 0;
    bottom: 0;
    z-index: 90;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.6);
  }

  .dashboard-sidebar.mobile-open {
    transform: translateX(0);
  }
}
</style>
