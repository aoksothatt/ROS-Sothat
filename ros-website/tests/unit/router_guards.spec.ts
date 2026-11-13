import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import router from '@/router';
import { useAuthStore } from '@/stores/auth';
import { authService } from '@/services/auth';

describe('Router Navigation Guards', () => {
  beforeEach(async () => {
    window.scrollTo = vi.fn();
    setActivePinia(createPinia());
    sessionStorage.clear();
    vi.restoreAllMocks();
    await router.push('/');
  });

  it('1. Anonymous user visiting /dashboard is redirected to /login', async () => {
    await router.push('/dashboard');
    expect(router.currentRoute.value.name).toBe('login');
    expect(router.currentRoute.value.query.redirect).toBe('/dashboard');
  });

  it('2. Authenticated user can access /dashboard', async () => {
    const store = useAuthStore();
    store.setSession('valid.bearer.token');

    vi.spyOn(authService, 'getProfile').mockResolvedValueOnce({
      id: 1,
      username: 'test_player',
      email: 'player@example.com',
      role: 'player',
      is_banned: false,
      created_at: '2026-11-13T10:00:00',
      last_login: null,
      has_character: false
    });

    await router.push('/dashboard');
    expect(router.currentRoute.value.name).toBe('dashboard');
  });

  it('3. Authenticated user visiting /login is redirected to /dashboard', async () => {
    const store = useAuthStore();
    store.setSession('valid.bearer.token');

    vi.spyOn(authService, 'getProfile').mockResolvedValue({
      id: 1,
      username: 'test_player',
      email: 'player@example.com',
      role: 'player',
      is_banned: false,
      created_at: '2026-11-13T10:00:00',
      last_login: null,
      has_character: false
    });

    await router.push('/login');
    expect(router.currentRoute.value.name).toBe('dashboard');
  });
});
