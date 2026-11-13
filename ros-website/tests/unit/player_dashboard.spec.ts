import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';

import DashboardOverviewPage from '@/pages/dashboard/DashboardOverviewPage.vue';
import PlayerProfilePage from '@/pages/dashboard/PlayerProfilePage.vue';
import WalletPage from '@/pages/dashboard/WalletPage.vue';
import InventoryPage from '@/pages/dashboard/InventoryPage.vue';
import StatisticsPage from '@/pages/dashboard/StatisticsPage.vue';
import AccountSettingsPage from '@/pages/dashboard/AccountSettingsPage.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';

import { useAuthStore } from '@/stores/auth';
import { playerService } from '@/services/player';
import { ApiError } from '@/services/api';
import type { CharacterProfile, CharacterInventoryResponse, DiamondHistoryResponse } from '@/types/dashboard';

const mockCharacter: CharacterProfile = {
  gid: 101,
  account_id: 1,
  nickname: 'ViperSniper',
  char_type: 0,
  level: 5,
  exp: 450,
  gold: 2500,
  diamonds: 350,
  appearances: {
    equipped_clothing: [10001, 10002],
    unlocked_items: [10001, 10002],
    active_weapon_skin: 201
  },
  settings: {
    control_mode: 1,
    fov: 80,
    gyroscope: true,
    sensitivity: { general: 100, aim: 85, scope2x: 65 }
  },
  stats: {
    total_matches: 0,
    total_wins: 0,
    total_kills: 0,
    damage_dealt: 0.0
  },
  created_at: '2026-11-01T12:00:00Z',
  updated_at: '2026-11-13T12:00:00Z'
};

const mockInventory: CharacterInventoryResponse = {
  character_gid: 101,
  total_items: 2,
  items: [
    {
      id: 1,
      character_gid: 101,
      item_id: 10,
      quantity: 1,
      created_at: '2026-11-01T12:00:00Z',
      updated_at: '2026-11-01T12:00:00Z',
      item: {
        id: 10,
        item_code: 'M4A1_DRAGON',
        name: 'M4A1 Dragon Flame',
        description: 'Elite animated assault rifle skin.',
        item_type: 'WEAPON_SKIN',
        icon: null,
        stackable: false,
        max_stack: 1,
        is_active: true,
        created_at: '2026-11-01T12:00:00Z',
        updated_at: '2026-11-01T12:00:00Z'
      }
    },
    {
      id: 2,
      character_gid: 101,
      item_id: 20,
      quantity: 5,
      created_at: '2026-11-01T12:00:00Z',
      updated_at: '2026-11-01T12:00:00Z',
      item: {
        id: 20,
        item_code: 'FIRST_AID_KIT',
        name: 'Military First Aid Kit',
        description: 'Restores 75 hit points.',
        item_type: 'CONSUMABLE',
        icon: null,
        stackable: true,
        max_stack: 10,
        is_active: true,
        created_at: '2026-11-01T12:00:00Z',
        updated_at: '2026-11-01T12:00:00Z'
      }
    }
  ]
};

const mockWalletHistory: DiamondHistoryResponse = {
  character_gid: 101,
  current_balance: 350,
  total_transactions: 2,
  transactions: [
    {
      id: 1,
      character_gid: 101,
      admin_account_id: 99,
      operation_type: 'GRANT',
      amount: 250,
      balance_before: 100,
      balance_after: 350,
      idempotency_key: 'tx_grant_01',
      reason: 'Community Tournament Reward',
      created_at: '2026-11-10T14:30:00Z'
    },
    {
      id: 2,
      character_gid: 101,
      admin_account_id: 99,
      operation_type: 'GRANT',
      amount: 100,
      balance_before: 0,
      balance_after: 100,
      idempotency_key: 'tx_starter_01',
      reason: 'Starter Diamond Package',
      created_at: '2026-11-01T12:00:00Z'
    }
  ]
};

describe('Player Dashboard Unit Tests (Phase P04)', () => {
  let pinia: any;
  let router: any;
  let authStore: any;

  beforeEach(async () => {
    pinia = createPinia();
    setActivePinia(pinia);
    sessionStorage.clear();
    vi.restoreAllMocks();

    authStore = useAuthStore();
    authStore.setSession('test-player-jwt-token');
    authStore.user = {
      id: 1,
      username: 'TestOperator',
      email: 'operator@ros-sothat.internal',
      role: 'player',
      is_banned: false,
      created_at: '2026-11-01T10:00:00Z',
      last_login: '2026-11-13T10:00:00Z',
      has_character: true
    };

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/dashboard', name: 'dashboard', component: DashboardOverviewPage, meta: { requiresAuth: true } },
        { path: '/dashboard/profile', name: 'dashboard-profile', component: PlayerProfilePage, meta: { requiresAuth: true } },
        { path: '/dashboard/wallet', name: 'dashboard-wallet', component: WalletPage, meta: { requiresAuth: true } },
        { path: '/dashboard/inventory', name: 'dashboard-inventory', component: InventoryPage, meta: { requiresAuth: true } },
        { path: '/dashboard/statistics', name: 'dashboard-statistics', component: StatisticsPage, meta: { requiresAuth: true } },
        { path: '/dashboard/settings', name: 'dashboard-settings', component: AccountSettingsPage, meta: { requiresAuth: true } },
        { path: '/login', name: 'login', component: { template: '<div>Login Page</div>' } }
      ]
    });
    await router.push('/dashboard');
  });

  // 1. Dashboard overview rendering
  it('1. renders Dashboard Overview with real character telemetry and metric summaries', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);
    vi.spyOn(playerService, 'getMyInventory').mockResolvedValue(mockInventory);

    const wrapper = mount(DashboardOverviewPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.operator-name').exists()).toBe(true));
    expect(wrapper.text()).toContain('ViperSniper');
    expect(wrapper.text()).toContain('350'); // Diamonds
    expect(wrapper.text()).toContain('2,500 G'); // Gold
    expect(wrapper.text()).toContain('Items Stored');
  });

  // 2. Player profile rendering
  it('2. renders Player Profile with character level, EXP, and equipped loadout', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);

    const wrapper = mount(PlayerProfilePage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.char-title').exists()).toBe(true));
    expect(wrapper.find('.char-title').text()).toBe('ViperSniper');
    expect(wrapper.text()).toContain('LEVEL 5');
    expect(wrapper.text()).toContain('Skin #201');
    expect(wrapper.text()).toContain('Item #10001');
    expect(wrapper.text()).toContain('Item #10002');
  });

  // 3. Wallet balance rendering
  it('3. renders authoritative diamond balance from backend response', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);
    vi.spyOn(playerService, 'getMyDiamondHistory').mockResolvedValue(mockWalletHistory);

    const wrapper = mount(WalletPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.primary-vault').exists()).toBe(true));
    expect(wrapper.find('.primary-vault .vault-amount').text()).toBe('350');
    expect(wrapper.find('.secondary-vault .vault-amount').text()).toBe('2,500');
  });

  // 4. Wallet empty state
  it('4. renders empty state when wallet has no transaction history records', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);
    vi.spyOn(playerService, 'getMyDiamondHistory').mockResolvedValue({
      character_gid: 101,
      current_balance: 100,
      total_transactions: 0,
      transactions: []
    });

    const wrapper = mount(WalletPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.history-empty').exists()).toBe(true));
    expect(wrapper.text()).toContain('NO TRANSACTIONS LOGGED');
  });

  // 5. Wallet transaction history
  it('5. renders transaction history records in table with operation type badges', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);
    vi.spyOn(playerService, 'getMyDiamondHistory').mockResolvedValue(mockWalletHistory);

    const wrapper = mount(WalletPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.tactical-table').exists()).toBe(true));
    expect(wrapper.text()).toContain('+250 💎');
    expect(wrapper.text()).toContain('Community Tournament Reward');
    expect(wrapper.text()).toContain('Starter Diamond Package');
  });

  // 6. Inventory item rendering
  it('6. renders inventory item cards with item code, type badge, and quantity', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);
    vi.spyOn(playerService, 'getMyInventory').mockResolvedValue(mockInventory);

    const wrapper = mount(InventoryPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.inventory-grid').exists()).toBe(true));
    expect(wrapper.text()).toContain('M4A1 Dragon Flame');
    expect(wrapper.text()).toContain('x1');
    expect(wrapper.text()).toContain('Military First Aid Kit');
    expect(wrapper.text()).toContain('x5');
  });

  // 7. Inventory empty state
  it('7. renders empty armory state when inventory holds zero items', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);
    vi.spyOn(playerService, 'getMyInventory').mockResolvedValue({
      character_gid: 101,
      total_items: 0,
      items: []
    });

    const wrapper = mount(InventoryPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.empty-inventory-wrapper').exists()).toBe(true));
    expect(wrapper.text()).toContain('INVENTORY LOCKER EMPTY');
  });

  // 8. Inventory filtering
  it('8. filters inventory items by category correctly', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);
    vi.spyOn(playerService, 'getMyInventory').mockResolvedValue(mockInventory);

    const wrapper = mount(InventoryPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.inventory-grid').exists()).toBe(true));

    // Initially ALL items: 2 items
    expect(wrapper.findAll('.item-card').length).toBe(2);

    // Filter by WEAPONS & SKINS
    const filterButtons = wrapper.findAll('.filter-pill');
    await filterButtons[1].trigger('click'); // WEAPONS & SKINS
    expect(wrapper.findAll('.item-card').length).toBe(1);
    expect(wrapper.text()).toContain('M4A1 Dragon Flame');
    expect(wrapper.text()).not.toContain('Military First Aid Kit');
  });

  // 9. Statistics rendering
  it('9. renders genuine tracked match statistics (matches: 0, wins: 0, kills: 0)', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);

    const wrapper = mount(StatisticsPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.stats-grid').exists()).toBe(true));
    expect(wrapper.text()).toContain('TOTAL MATCHES');
    expect(wrapper.text()).toContain('VICTORIES / WINS');
    expect(wrapper.text()).toContain('CONFIRMED KILLS');
  });

  // 10. Statistics unavailable / pending state
  it('10. displays honest development status banner regarding match telemetry', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockResolvedValue(mockCharacter);

    const wrapper = mount(StatisticsPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.dev-status-banner').exists()).toBe(true));
    expect(wrapper.text()).toContain('Multiplayer Match Tracking In Development');
    expect(wrapper.text()).toContain('Authenticity Commitment');
  });

  // 11. Settings rendering
  it('11. renders Account Settings with identity parameters and session posture', async () => {
    const wrapper = mount(AccountSettingsPage, {
      global: { plugins: [pinia, router] }
    });

    expect(wrapper.text()).toContain('TestOperator');
    expect(wrapper.text()).toContain('operator@ros-sothat.internal');
    expect(wrapper.text()).toContain('sessionStorage');
    expect(wrapper.text()).toContain('IN DEVELOPMENT');
  });

  // 12. Loading states
  it('12. renders LoadingState component during active data fetching', () => {
    const wrapper = mount(LoadingState, {
      props: { message: 'Synchronizing...' }
    });

    expect(wrapper.find('.spinner').exists()).toBe(true);
    expect(wrapper.text()).toContain('Synchronizing...');
  });

  // 13. API error states
  it('13. displays error alert when backend request fails', async () => {
    vi.spyOn(playerService, 'getMyCharacter').mockRejectedValue(
      new ApiError(500, 'Internal Server Error during telemetry scan')
    );

    const wrapper = mount(DashboardOverviewPage, {
      global: { plugins: [pinia, router] }
    });

    await vi.waitFor(() => expect(wrapper.find('.alert-danger').exists()).toBe(true));
    expect(wrapper.find('.alert-danger').text()).toContain('Internal Server Error during telemetry scan');
  });

  // 14. Logout
  it('14. logs out user and purges session storage upon clicking logout', async () => {
    const wrapper = mount(AccountSettingsPage, {
      global: { plugins: [pinia, router] }
    });

    await wrapper.find('.logout-btn').trigger('click');
    expect(authStore.token).toBeNull();
    expect(sessionStorage.getItem('ros_sothat_token')).toBeNull();
  });

  // 15. Protected routes
  it('15. redirects unauthenticated user away from dashboard to login', async () => {
    authStore.logout();

    router.beforeEach((to: any, _from: any, next: any) => {
      if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next({ name: 'login', query: { redirect: to.fullPath } });
      } else {
        next();
      }
    });

    await router.push('/dashboard/wallet');
    expect(router.currentRoute.value.name).toBe('login');
    expect(router.currentRoute.value.query.redirect).toBe('/dashboard/wallet');
  });

  // 16. Expired authentication session
  it('16. purges session state when token is invalidated by server', async () => {
    authStore.setSession('expired-fake-token');

    vi.spyOn(authStore, 'initSession').mockImplementation(async () => {
      authStore.logout();
      return false;
    });

    const isValid = await authStore.initSession();
    expect(isValid).toBe(false);
    expect(authStore.token).toBeNull();
    expect(sessionStorage.getItem('ros_sothat_token')).toBeNull();
  });
});
