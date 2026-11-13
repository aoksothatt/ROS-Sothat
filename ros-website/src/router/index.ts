import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '@/stores/auth';

import HomePage from '@/pages/HomePage.vue';
import RegisterPage from '@/pages/RegisterPage.vue';
import LoginPage from '@/pages/LoginPage.vue';

// Player Dashboard Pages (Phase P04)
import DashboardOverviewPage from '@/pages/dashboard/DashboardOverviewPage.vue';
import PlayerProfilePage from '@/pages/dashboard/PlayerProfilePage.vue';
import WalletPage from '@/pages/dashboard/WalletPage.vue';
import InventoryPage from '@/pages/dashboard/InventoryPage.vue';
import StatisticsPage from '@/pages/dashboard/StatisticsPage.vue';
import AccountSettingsPage from '@/pages/dashboard/AccountSettingsPage.vue';

// Admin Dashboard Pages (Phase P05)
import AdminOverviewPage from '@/pages/admin/AdminOverviewPage.vue';
import AdminPlayersPage from '@/pages/admin/AdminPlayersPage.vue';
import AdminPlayerDetailPage from '@/pages/admin/AdminPlayerDetailPage.vue';
import AdminDiamondsPage from '@/pages/admin/AdminDiamondsPage.vue';
import AdminInventoryPage from '@/pages/admin/AdminInventoryPage.vue';
import AdminAuditLogsPage from '@/pages/admin/AdminAuditLogsPage.vue';

import NotFoundPage from '@/pages/NotFoundPage.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior() {
    return { top: 0 };
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterPage
    },
    {
      path: '/login',
      name: 'login',
      component: LoginPage
    },
    // Player Dashboard routes
    {
      path: '/dashboard',
      name: 'dashboard',
      component: DashboardOverviewPage,
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard/profile',
      name: 'dashboard-profile',
      component: PlayerProfilePage,
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard/wallet',
      name: 'dashboard-wallet',
      component: WalletPage,
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard/inventory',
      name: 'dashboard-inventory',
      component: InventoryPage,
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard/statistics',
      name: 'dashboard-statistics',
      component: StatisticsPage,
      meta: { requiresAuth: true }
    },
    {
      path: '/dashboard/settings',
      name: 'dashboard-settings',
      component: AccountSettingsPage,
      meta: { requiresAuth: true }
    },
    // Admin Dashboard routes (Phase P05)
    {
      path: '/admin',
      name: 'admin-overview',
      component: AdminOverviewPage,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/players',
      name: 'admin-players',
      component: AdminPlayersPage,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/players/:id',
      name: 'admin-player-detail',
      component: AdminPlayerDetailPage,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/transactions',
      name: 'admin-transactions',
      component: AdminDiamondsPage,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/inventory',
      name: 'admin-inventory',
      component: AdminInventoryPage,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/audit-logs',
      name: 'admin-audit-logs',
      component: AdminAuditLogsPage,
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/404',
      name: 'not-found',
      component: NotFoundPage
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/404'
    }
  ]
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      return next({ name: 'login', query: { redirect: to.fullPath } });
    }

    // Verify session validity if user object not loaded
    if (!authStore.user) {
      const isValid = await authStore.initSession();
      if (!isValid) {
        return next({ name: 'login', query: { redirect: to.fullPath } });
      }
    }

    // Role check for admin routes
    if (to.meta.requiresAdmin) {
      if (!authStore.isAdmin) {
        return next({ name: 'dashboard' });
      }
    }
  }

  // If already authenticated, redirect away from guest-only auth pages
  if ((to.name === 'login' || to.name === 'register') && authStore.isAuthenticated) {
    if (authStore.isAdmin) {
      return next({ name: 'admin-overview' });
    }
    return next({ name: 'dashboard' });
  }

  next();
});

export default router;
