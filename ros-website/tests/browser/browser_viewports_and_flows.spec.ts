import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createRouter, createMemoryHistory } from 'vue-router';

import AppNavbar from '@/components/AppNavbar.vue';
import HomePage from '@/pages/HomePage.vue';
import RegisterPage from '@/pages/RegisterPage.vue';
import LoginPage from '@/pages/LoginPage.vue';
import DashboardPage from '@/pages/DashboardPage.vue';
import NotFoundPage from '@/pages/NotFoundPage.vue';
import OtpInput from '@/components/OtpInput.vue';
import { useAuthStore } from '@/stores/auth';
import { authService } from '@/services/auth';
import { ApiError } from '@/services/api';

// Viewport sizes specified in Phase P03.1
const VIEWPORTS = [
  { name: 'Desktop Ultra-Wide', width: 1920, height: 1080, isMobile: false },
  { name: 'Desktop Laptop', width: 1440, height: 900, isMobile: false },
  { name: 'Tablet Portrait', width: 768, height: 1024, isMobile: true },
  { name: 'Mobile Modern (iPhone 12/13/14)', width: 390, height: 844, isMobile: true },
  { name: 'Mobile Legacy (iPhone SE / 8)', width: 375, height: 667, isMobile: true }
];

function setViewport(width: number, height: number) {
  Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: width });
  Object.defineProperty(window, 'innerHeight', { writable: true, configurable: true, value: height });
  window.dispatchEvent(new Event('resize'));
}

describe('Browser Viewports & Functional Workflows (P03.1)', () => {
  let pinia: any;
  let router: any;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    sessionStorage.clear();
    vi.restoreAllMocks();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'home', component: HomePage },
        { path: '/register', name: 'register', component: RegisterPage },
        { path: '/login', name: 'login', component: LoginPage },
        { path: '/dashboard', name: 'dashboard', component: DashboardPage, meta: { requiresAuth: true } },
        { path: '/404', name: 'not-found', component: NotFoundPage }
      ]
    });
  });

  // -------------------------------------------------------------
  // 1. Viewport Responsiveness across all 5 required dimensions
  // -------------------------------------------------------------
  describe('Viewport Responsiveness (1920x1080 down to 375x667)', () => {
    VIEWPORTS.forEach((vp) => {
      it(`renders navigation correctly at ${vp.name} (${vp.width}x${vp.height})`, async () => {
        setViewport(vp.width, vp.height);
        const wrapper = mount(AppNavbar, {
          global: {
            plugins: [pinia, router]
          }
        });

        expect(wrapper.find('.brand-title').text()).toContain('ROS SOTHAT');
        const toggleBtn = wrapper.find('.mobile-toggle');
        expect(toggleBtn.exists()).toBe(true);

        if (vp.isMobile) {
          // On mobile viewports, toggle opens the drawer
          expect(wrapper.find('.nav-links').classes()).not.toContain('open');
          await toggleBtn.trigger('click');
          expect(wrapper.find('.nav-links').classes()).toContain('open');
          await toggleBtn.trigger('click');
          expect(wrapper.find('.nav-links').classes()).not.toContain('open');
        }
      });

      it(`renders Landing Page hero and stats at ${vp.name} (${vp.width}x${vp.height})`, async () => {
        setViewport(vp.width, vp.height);
        const wrapper = mount(HomePage, {
          global: {
            plugins: [pinia, router]
          }
        });

        expect(wrapper.find('.hero-title').text()).toContain('THE ISLAND IS WAITING');
        expect(wrapper.find('.hero-stats-row').text()).toContain('10–20');
        expect(wrapper.find('.hero-stats-row').text()).toContain('Invited Friends');
      });
    });
  });

  // -------------------------------------------------------------
  // 2. Functional Workflow: Registration Flow & Cooldown
  // -------------------------------------------------------------
  describe('Workflow: Registration with OTP & Cooldown', () => {
    it('executes 2-step registration: request OTP -> countdown -> verify', async () => {
      vi.spyOn(authService, 'requestOTP').mockResolvedValueOnce({
        status: 'ok',
        message: 'Verification code dispatched to your inbox.',
        cooldown_seconds: 60,
        masked_email: 'p***@example.com'
      });

      vi.spyOn(authService, 'verifyOTP').mockResolvedValueOnce({
        access_token: 'fake-jwt-token-recruit',
        token_type: 'bearer',
        account_id: 42,
        username: 'RecruitAlpha'
      });

      vi.spyOn(authService, 'getProfile').mockResolvedValueOnce({
        id: 42,
        username: 'RecruitAlpha',
        email: 'pilot@example.com',
        role: 'player',
        is_banned: false,
        created_at: new Date().toISOString(),
        last_login: new Date().toISOString(),
        has_character: false
      });

      const wrapper = mount(RegisterPage, {
        global: {
          plugins: [pinia, router]
        }
      });

      // Step 1: Enter email and username
      const emailInput = wrapper.find('#reg-email');
      await emailInput.setValue('pilot@example.com');
      const userInput = wrapper.find('#reg-username');
      await userInput.setValue('RecruitAlpha');

      // Submit step 1
      await wrapper.find('form').trigger('submit.prevent');
      await wrapper.vm.$nextTick();

      expect(authService.requestOTP).toHaveBeenCalledWith({
        email: 'pilot@example.com',
        purpose: 'registration'
      });

      // Step 2: OTP verification step rendered with cooldown
      expect(wrapper.text()).toContain('Code sent to:');
      expect(wrapper.text()).toContain('p***@example.com');
      expect(wrapper.find('.resend-btn').text()).toContain('Resend code in');

      // Fill OTP and submit
      const otpComponent = wrapper.findComponent(OtpInput);
      expect(otpComponent.exists()).toBe(true);
      await otpComponent.vm.$emit('update:modelValue', '123456');

      await wrapper.find('form').trigger('submit.prevent');
      await wrapper.vm.$nextTick();

      expect(authService.verifyOTP).toHaveBeenCalledWith({
        email: 'pilot@example.com',
        code: '123456',
        purpose: 'registration',
        username: 'RecruitAlpha'
      });

      const authStore = useAuthStore();
      expect(authStore.token).toBe('fake-jwt-token-recruit');
      expect(sessionStorage.getItem('ros_sothat_token')).toBe('fake-jwt-token-recruit');
    });

    it('handles 429 rate limit during registration OTP request', async () => {
      vi.spyOn(authService, 'requestOTP').mockRejectedValueOnce(
        new ApiError(429, 'Rate limit exceeded. Please wait before requesting another code.', 45)
      );

      const wrapper = mount(RegisterPage, {
        global: {
          plugins: [pinia, router]
        }
      });

      await wrapper.find('#reg-email').setValue('pilot@example.com');
      await wrapper.find('form').trigger('submit.prevent');
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.alert-danger').text()).toContain('Rate limit exceeded');
      expect(wrapper.find('button[type="submit"]').text()).toContain('RESEND IN');
    });
  });

  // -------------------------------------------------------------
  // 3. Functional Workflow: OTP Input typing, paste & backspace
  // -------------------------------------------------------------
  describe('Workflow: OTP Input Component Interactions', () => {
    it('supports 6 individual boxes, single digit typing, and backspace navigation', async () => {
      const wrapper = mount(OtpInput, {
        props: {
          modelValue: ''
        }
      });

      const inputs = wrapper.findAll('.otp-box');
      expect(inputs.length).toBe(6);

      // Type first digit
      await inputs[0].setValue('7');
      await inputs[0].trigger('input');
      expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['7']);

      // Backspace clears and syncs
      await inputs[0].trigger('keydown', { key: 'Backspace' });
      expect(wrapper.emitted('update:modelValue')?.slice(-1)[0]).toEqual(['']);
    });

    it('splits a pasted 6-digit numeric string across all boxes', async () => {
      const wrapper = mount(OtpInput, {
        props: {
          modelValue: ''
        }
      });

      const mockClipboardEvent = {
        clipboardData: {
          getData: (type: string) => (type === 'text' ? '948201' : '')
        }
      };

      await wrapper.find('.otp-container').trigger('paste', mockClipboardEvent);

      const lastEmit = wrapper.emitted('update:modelValue')?.slice(-1)[0];
      expect(lastEmit).toEqual(['948201']);
      expect(wrapper.emitted('complete')?.[0]).toEqual(['948201']);
    });
  });

  // -------------------------------------------------------------
  // 4. Functional Workflow: Login Flow & Invalid OTP Handling
  // -------------------------------------------------------------
  describe('Workflow: Login & Invalid OTP Error Handling', () => {
    it('handles wrong OTP error and propagates remaining attempts message', async () => {
      vi.spyOn(authService, 'requestOTP').mockResolvedValueOnce({
        status: 'ok',
        message: 'Verification code dispatched.',
        cooldown_seconds: 60,
        masked_email: 'o***@ros-sothat.internal'
      });

      vi.spyOn(authService, 'verifyOTP').mockRejectedValueOnce(
        new ApiError(400, 'Invalid OTP code. 3 attempts remaining.')
      );

      const wrapper = mount(LoginPage, {
        global: {
          plugins: [pinia, router]
        }
      });

      // Request OTP
      await wrapper.find('#login-email').setValue('operator@ros-sothat.internal');
      await wrapper.find('form').trigger('submit.prevent');
      await wrapper.vm.$nextTick();

      // Submit incorrect OTP
      const otpComp = wrapper.findComponent(OtpInput);
      await otpComp.vm.$emit('update:modelValue', '000000');
      await wrapper.find('form').trigger('submit.prevent');
      await wrapper.vm.$nextTick();

      expect(wrapper.find('.alert-danger').text()).toContain('Invalid OTP code. 3 attempts remaining.');
      const authStore = useAuthStore();
      expect(authStore.isAuthenticated).toBe(false);
      expect(sessionStorage.getItem('ros_sothat_token')).toBeNull();
    });

    it('authenticates returning user and redirects to destination', async () => {
      vi.spyOn(authService, 'requestOTP').mockResolvedValueOnce({
        status: 'ok',
        message: 'Verification code dispatched.',
        cooldown_seconds: 60,
        masked_email: 'o***@ros-sothat.internal'
      });

      vi.spyOn(authService, 'verifyOTP').mockResolvedValueOnce({
        access_token: 'valid-player-jwt',
        token_type: 'bearer',
        account_id: 10,
        username: 'ViperSquadron'
      });

      vi.spyOn(authService, 'getProfile').mockResolvedValueOnce({
        id: 10,
        username: 'ViperSquadron',
        email: 'operator@ros-sothat.internal',
        role: 'player',
        is_banned: false,
        created_at: new Date().toISOString(),
        last_login: new Date().toISOString(),
        has_character: true
      });

      const wrapper = mount(LoginPage, {
        global: {
          plugins: [pinia, router]
        }
      });

      await wrapper.find('#login-email').setValue('operator@ros-sothat.internal');
      await wrapper.find('form').trigger('submit.prevent');
      await wrapper.vm.$nextTick();

      const otpComp = wrapper.findComponent(OtpInput);
      await otpComp.vm.$emit('update:modelValue', '654321');
      await wrapper.find('form').trigger('submit.prevent');
      await wrapper.vm.$nextTick();

      const authStore = useAuthStore();
      expect(authStore.isAuthenticated).toBe(true);
      expect(authStore.user?.username).toBe('ViperSquadron');
      expect(authStore.isPlayer).toBe(true);
      expect(authStore.isAdmin).toBe(false);
    });
  });

  // -------------------------------------------------------------
  // 5. Functional Workflow: Dashboard Protection, Telemetry & Logout
  // -------------------------------------------------------------
  describe('Workflow: Dashboard Protection & Logout Session', () => {
    it('displays authentic profile data on Dashboard and logs out cleanly', async () => {
      const authStore = useAuthStore();
      authStore.setSession('mock-valid-token');
      authStore.user = {
        id: 77,
        username: 'ApexLeader',
        email: 'apex@island.internal',
        role: 'player',
        is_banned: false,
        created_at: '2026-11-01T10:00:00Z',
        last_login: '2026-11-13T12:00:00Z',
        has_character: true
      };

      const wrapper = mount(DashboardPage, {
        global: {
          plugins: [pinia, router]
        }
      });

      expect(wrapper.find('.player-name').text()).toBe('ApexLeader');
      expect(wrapper.find('.player-email').text()).toBe('apex@island.internal');
      expect(wrapper.text()).toContain('#77');
      expect(wrapper.text()).toContain('PROVISIONED');

      // Confirm unimplemented features are marked In Development
      const devBadges = wrapper.findAll('.badge-dev');
      expect(devBadges.length).toBeGreaterThan(0);
      expect(wrapper.text()).toContain('Diamond Currency Vault');
      expect(wrapper.text()).toContain('IN DEVELOPMENT');

      // Trigger Logout
      await wrapper.find('.btn-secondary').trigger('click');
      expect(authStore.token).toBeNull();
      expect(authStore.user).toBeNull();
      expect(sessionStorage.getItem('ros_sothat_token')).toBeNull();
    });

    it('purges session if token is expired or rejected by server', async () => {
      const authStore = useAuthStore();
      authStore.setSession('expired-fake-token');

      vi.spyOn(authService, 'getProfile').mockRejectedValueOnce(
        new ApiError(401, 'Could not validate credentials')
      );

      const isValid = await authStore.initSession();
      expect(isValid).toBe(false);
      expect(authStore.token).toBeNull();
      expect(authStore.user).toBeNull();
      expect(sessionStorage.getItem('ros_sothat_token')).toBeNull();
    });
  });

  // -------------------------------------------------------------
  // 6. Functional Workflow: 404 Sector Not Found Page
  // -------------------------------------------------------------
  describe('Workflow: 404 Sector Not Found', () => {
    it('renders tactical 404 error page with navigation link', () => {
      const wrapper = mount(NotFoundPage, {
        global: {
          plugins: [pinia, router]
        }
      });

      expect(wrapper.find('.error-code').text()).toBe('404');
      expect(wrapper.find('.error-title').text()).toBe('COORDINATES NOT FOUND');
      expect(wrapper.find('.btn-primary').text()).toContain('Return To Home Sector');
    });
  });
});
