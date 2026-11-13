import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useAuthStore } from '@/stores/auth';
import { authService } from '@/services/auth';

describe('useAuthStore Unit Tests', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it('1. Initial state has null token and user', () => {
    const store = useAuthStore();
    expect(store.token).toBeNull();
    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
  });

  it('2. setSession persists token in memory and sessionStorage', () => {
    const store = useAuthStore();
    store.setSession('test.bearer.token');

    expect(store.token).toBe('test.bearer.token');
    expect(store.isAuthenticated).toBe(true);
    expect(sessionStorage.getItem('ros_sothat_token')).toBe('test.bearer.token');
  });

  it('3. logout clears in-memory state and sessionStorage', () => {
    const store = useAuthStore();
    store.setSession('test.bearer.token');
    store.logout();

    expect(store.token).toBeNull();
    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem('ros_sothat_token')).toBeNull();
  });

  it('4. Role evaluation: isPlayer and isAdmin based on backend profile', async () => {
    const store = useAuthStore();
    store.setSession('valid.token');

    // Mock player profile
    vi.spyOn(authService, 'getProfile').mockResolvedValueOnce({
      id: 5,
      username: 'recon_unit',
      email: 'recon@example.com',
      role: 'player',
      is_banned: false,
      created_at: '2026-11-13T10:00:00',
      last_login: '2026-11-13T12:00:00',
      has_character: false
    });

    const ok = await store.initSession();
    expect(ok).toBe(true);
    expect(store.isPlayer).toBe(true);
    expect(store.isAdmin).toBe(false);

    // Mock admin profile
    vi.spyOn(authService, 'getProfile').mockResolvedValueOnce({
      id: 1,
      username: 'server_admin',
      email: 'admin@example.com',
      role: 'admin',
      is_banned: false,
      created_at: '2026-11-13T10:00:00',
      last_login: '2026-11-13T12:00:00',
      has_character: true
    });

    await store.initSession();
    expect(store.isPlayer).toBe(false);
    expect(store.isAdmin).toBe(true);
  });

  it('5. Expired or invalid token clears session on initSession failure', async () => {
    const store = useAuthStore();
    store.setSession('expired.token');

    vi.spyOn(authService, 'getProfile').mockRejectedValueOnce(
      new Error('Token expired or unauthorized')
    );

    const ok = await store.initSession();
    expect(ok).toBe(false);
    expect(store.token).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem('ros_sothat_token')).toBeNull();
  });
});
