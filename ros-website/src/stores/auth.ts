import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authService } from '@/services/auth';
import type { AccountProfile } from '@/types/auth';

const STORAGE_KEY = 'ros_sothat_token';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(sessionStorage.getItem(STORAGE_KEY));
  const user = ref<AccountProfile | null>(null);
  const loading = ref<boolean>(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!token.value);
  const isPlayer = computed(() => user.value?.role === 'player');
  const isAdmin = computed(() => user.value?.role === 'admin');

  /**
   * Initialize or restore user session from stored Bearer token.
   */
  async function initSession(): Promise<boolean> {
    if (!token.value) {
      user.value = null;
      return false;
    }

    loading.value = true;
    error.value = null;
    try {
      const profile = await authService.getProfile(token.value);
      user.value = profile;
      return true;
    } catch (err: any) {
      // Invalid, expired, or rejected token
      logout();
      return false;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Save newly authenticated session token.
   */
  function setSession(newToken: string): void {
    token.value = newToken;
    sessionStorage.setItem(STORAGE_KEY, newToken);
  }

  /**
   * Clear session state and remove token.
   */
  function logout(): void {
    token.value = null;
    user.value = null;
    error.value = null;
    sessionStorage.removeItem(STORAGE_KEY);
  }

  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    isPlayer,
    isAdmin,
    initSession,
    setSession,
    logout
  };
});
