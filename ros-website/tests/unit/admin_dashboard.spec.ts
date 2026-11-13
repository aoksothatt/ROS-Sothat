import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { adminService } from '@/services/admin';
import * as apiModule from '@/services/api';
import AdminSidebar from '@/components/admin/AdminSidebar.vue';
import AdminHeader from '@/components/admin/AdminHeader.vue';
import { useAuthStore } from '@/stores/auth';

describe('Phase P05: Admin Dashboard Frontend Test Suite', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
  });

  describe('1. Admin API Service Unit Tests', () => {
    it('getSummary sends GET request with Bearer authorization', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        total_accounts: 10,
        active_accounts: 9,
        suspended_accounts: 1,
        total_characters: 8,
        total_diamonds: 5000,
        total_inventory_items: 45,
        active_lobby_presences: 2,
        active_rooms: 1,
        queued_matchmaking_tickets: 0,
        recent_activity: []
      });

      const res = await adminService.getSummary('test-admin-jwt');
      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/dashboard/summary',
        { method: 'GET' },
        'test-admin-jwt'
      );
      expect(res.total_accounts).toBe(10);
      expect(res.total_diamonds).toBe(5000);
    });

    it('listPlayers builds query parameters correctly', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        total: 1,
        limit: 10,
        offset: 0,
        players: []
      });

      await adminService.listPlayers('test-jwt', {
        q: 'sniper',
        is_banned: true,
        limit: 10,
        offset: 0
      });

      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players?q=sniper&is_banned=true&limit=10&offset=0',
        { method: 'GET' },
        'test-jwt'
      );
    });

    it('getPlayerDetail targets specific player ID', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        account_id: 42,
        username: 'ViperTarget',
        role: 'player',
        is_banned: false,
        created_at: '2026-11-13T00:00:00Z',
        inventory_items: [],
        recent_diamond_transactions: [],
        recent_audit_logs: []
      });

      const detail = await adminService.getPlayerDetail('test-jwt', 42);
      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players/42',
        { method: 'GET' },
        'test-jwt'
      );
      expect(detail.username).toBe('ViperTarget');
    });

    it('suspendPlayer executes POST with reason payload', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        account_id: 5,
        username: 'HackerOne',
        is_banned: true,
        ban_reason: 'Exploit detected'
      });

      await adminService.suspendPlayer('test-jwt', 5, {
        reason: 'Exploit detected'
      });

      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players/5/suspend',
        {
          method: 'POST',
          body: JSON.stringify({ reason: 'Exploit detected' })
        },
        'test-jwt'
      );
    });

    it('reactivatePlayer executes POST with reason payload', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        account_id: 5,
        username: 'HackerOne',
        is_banned: false
      });

      await adminService.reactivatePlayer('test-jwt', 5, {
        reason: 'Appeal approved'
      });

      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players/5/reactivate',
        {
          method: 'POST',
          body: JSON.stringify({ reason: 'Appeal approved' })
        },
        'test-jwt'
      );
    });

    it('grantDiamonds sends positive amount and idempotency key', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        operation_type: 'GRANT',
        amount: 500,
        balance_after: 600
      });

      await adminService.grantDiamonds('test-jwt', 7, {
        amount: 500,
        reason: 'Event reward',
        idempotency_key: 'grant-key-123'
      });

      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players/7/diamonds/grant',
        {
          method: 'POST',
          body: JSON.stringify({
            amount: 500,
            reason: 'Event reward',
            idempotency_key: 'grant-key-123'
          })
        },
        'test-jwt'
      );
    });

    it('deductDiamonds sends amount and reason', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        operation_type: 'DEDUCT',
        amount: 200,
        balance_after: 400
      });

      await adminService.deductDiamonds('test-jwt', 7, {
        amount: 200,
        reason: 'Penalty fee',
        idempotency_key: 'deduct-key-123'
      });

      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players/7/diamonds/deduct',
        {
          method: 'POST',
          body: JSON.stringify({
            amount: 200,
            reason: 'Penalty fee',
            idempotency_key: 'deduct-key-123'
          })
        },
        'test-jwt'
      );
    });

    it('grantInventory and removeInventory invoke respective endpoints', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValue({});

      await adminService.grantInventory('test-jwt', 12, {
        item_id: 101,
        quantity: 2,
        reason: 'Tournament gear',
        idempotency_key: 'inv-g-1'
      });
      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players/12/inventory/grant',
        expect.objectContaining({ method: 'POST' }),
        'test-jwt'
      );

      await adminService.removeInventory('test-jwt', 12, {
        item_id: 101,
        quantity: 1,
        reason: 'Revoke single item',
        idempotency_key: 'inv-r-1'
      });
      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/players/12/inventory/remove',
        expect.objectContaining({ method: 'POST' }),
        'test-jwt'
      );
    });

    it('listAuditLogs formats filter parameters', async () => {
      const spy = vi.spyOn(apiModule, 'apiRequest').mockResolvedValueOnce({
        total: 5,
        limit: 20,
        offset: 0,
        logs: []
      });

      await adminService.listAuditLogs('test-jwt', {
        action_type: 'DIAMOND_GRANT',
        admin_id: 1,
        limit: 20,
        offset: 0
      });

      expect(spy).toHaveBeenCalledWith(
        '/api/v1/admin/audit-logs?admin_id=1&action_type=DIAMOND_GRANT&limit=20&offset=0',
        { method: 'GET' },
        'test-jwt'
      );
    });
  });

  describe('2. Admin Navigation Components', () => {
    it('AdminSidebar renders all administrative navigation links', () => {
      const authStore = useAuthStore();
      authStore.user = {
        id: 1,
        username: 'AdminMaster',
        email: 'admin@rossothat.local',
        role: 'admin',
        is_banned: false,
        created_at: '2026-11-13T00:00:00Z',
        last_login: null,
        has_character: true
      };

      const wrapper = mount(AdminSidebar, {
        global: {
          stubs: {
            RouterLink: {
              template: '<a><slot /></a>'
            }
          }
        }
      });

      expect(wrapper.text()).toContain('ADMIN PORTAL');
      expect(wrapper.text()).toContain('Overview');
      expect(wrapper.text()).toContain('Players & Accounts');
      expect(wrapper.text()).toContain('Diamond Ledger');
      expect(wrapper.text()).toContain('Inventory & Catalog');
      expect(wrapper.text()).toContain('Audit Logs');
      expect(wrapper.text()).toContain('Player Dashboard');
      expect(wrapper.text()).toContain('Logout Session');
    });

    it('AdminHeader renders title, admin badge, and loopback server status', () => {
      const wrapper = mount(AdminHeader, {
        props: {
          title: 'Command Security Center',
          subtitle: 'Live management stream'
        }
      });

      expect(wrapper.find('.page-title').text()).toBe('Command Security Center');
      expect(wrapper.find('.page-subtitle').text()).toBe('Live management stream');
      expect(wrapper.find('.admin-badge').text()).toBe('ADMIN');
      expect(wrapper.find('.badge-text').text()).toContain('127.0.0.1');
    });
  });

  describe('3. Route Guard & Authorization Protection', () => {
    it('authStore correctly computes isAdmin based on user role', () => {
      const authStore = useAuthStore();

      // Unauthenticated
      expect(authStore.isAdmin).toBe(false);

      // Player role
      authStore.user = {
        id: 2,
        username: 'RegularShooter',
        email: 'shooter@rossothat.local',
        role: 'player',
        is_banned: false,
        created_at: '2026-11-13T00:00:00Z',
        last_login: null,
        has_character: true
      };
      expect(authStore.isAdmin).toBe(false);

      // Admin role
      authStore.user = {
        id: 1,
        username: 'IslandAdmin',
        email: 'islandadmin@rossothat.local',
        role: 'admin',
        is_banned: false,
        created_at: '2026-11-13T00:00:00Z',
        last_login: null,
        has_character: true
      };
      expect(authStore.isAdmin).toBe(true);
    });
  });
});
