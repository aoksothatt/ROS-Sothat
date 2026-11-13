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

const adminNavItems = [
  { name: 'Overview', path: '/admin', icon: '🛡️', exact: true },
  { name: 'Players & Accounts', path: '/admin/players', icon: '👥', exact: false },
  { name: 'Diamond Ledger', path: '/admin/transactions', icon: '💎', exact: false },
  { name: 'Inventory & Catalog', path: '/admin/inventory', icon: '🎒', exact: false },
  { name: 'Audit Logs', path: '/admin/audit-logs', icon: '📜', exact: false }
];

function isActive(item: typeof adminNavItems[0]) {
  if (!route || !route.path) return false;
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
  <aside class="admin-sidebar" :class="{ 'mobile-open': mobileOpen }">
    <!-- Admin User Badge -->
    <div class="sidebar-user-card">
      <div class="user-avatar admin-avatar">
        <span>{{ authStore.user?.username.slice(0, 2).toUpperCase() || 'AD' }}</span>
      </div>
      <div class="user-meta">
        <span class="user-callsign">{{ authStore.user?.username || 'Administrator' }}</span>
        <span class="user-role-badge badge badge-admin">ADMIN PORTAL</span>
      </div>
    </div>

    <!-- Admin Navigation Menu -->
    <nav class="sidebar-nav">
      <div class="nav-section-title">ADMINISTRATION</div>
      <ul class="nav-list">
        <li v-for="item in adminNavItems" :key="item.path" class="nav-item">
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

      <div class="nav-section-title mt-4">SWITCH PORTAL</div>
      <ul class="nav-list">
        <li class="nav-item">
          <RouterLink
            to="/dashboard"
            class="nav-link switch-link"
            @click="emit('close')"
          >
            <span class="nav-icon">🎮</span>
            <span class="nav-text">Player Dashboard</span>
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
.admin-sidebar {
  width: 270px;
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
  border-radius: 8px;
  border: 1px solid rgba(255, 180, 0, 0.2);
}

.user-avatar.admin-avatar {
  width: 44px;
  height: 44px;
  border-radius: 6px;
  background: linear-gradient(135deg, rgba(255, 180, 0, 0.2), rgba(255, 77, 77, 0.2));
  border: 1px solid #ffb400;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  color: #ffb400;
}

.user-meta {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow: hidden;
}

.user-callsign {
  font-weight: 700;
  font-size: 0.95rem;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.badge-admin {
  background-color: rgba(255, 180, 0, 0.15);
  color: #ffb400;
  border: 1px solid rgba(255, 180, 0, 0.4);
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  align-self: flex-start;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
}

.nav-section-title {
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  padding: 0 0.75rem;
  margin-bottom: 0.25rem;
}

.mt-4 {
  margin-top: 1.5rem;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.75rem 0.85rem;
  border-radius: 6px;
  color: var(--text-muted);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.9rem;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.nav-link:hover {
  background-color: rgba(255, 255, 255, 0.05);
  color: #fff;
}

.nav-link.active {
  background-color: rgba(255, 180, 0, 0.12);
  color: #ffb400;
  border-color: rgba(255, 180, 0, 0.3);
  font-weight: 700;
}

.switch-link {
  color: var(--color-primary);
}

.switch-link:hover {
  background-color: rgba(0, 204, 136, 0.1);
  color: #fff;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.btn-block {
  width: 100%;
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  padding: 0.65rem;
}

@media (max-width: 900px) {
  .admin-sidebar {
    position: fixed;
    top: 70px;
    left: 0;
    bottom: 0;
    z-index: 90;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.7);
  }

  .admin-sidebar.mobile-open {
    transform: translateX(0);
  }
}
</style>
