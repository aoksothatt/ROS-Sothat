<script setup lang="ts">
import { ref, onUnmounted } from 'vue';
import { RouterLink, useRouter, useRoute } from 'vue-router';
import { authService } from '@/services/auth';
import { useAuthStore } from '@/stores/auth';
import { apiRequest, ApiError } from '@/services/api';
import OtpInput from '@/components/OtpInput.vue';
import type { TokenResponseData } from '@/types/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

// Login mode: 'otp' (player email) or 'admin' (username/password)
const loginMode = ref<'otp' | 'admin'>('otp');

// Email OTP State
const email = ref('');
const otpCode = ref('');
const step = ref<'email' | 'verify'>('email');
const maskedEmail = ref('');

// Admin Password State
const adminUsername = ref('');
const adminPassword = ref('');

// Status & UX State
const loading = ref(false);
const errorMessage = ref('');
const infoMessage = ref('');
const cooldown = ref(0);
let cooldownTimer: any = null;

function startCooldown(seconds: number) {
  cooldown.value = seconds;
  if (cooldownTimer) clearInterval(cooldownTimer);
  cooldownTimer = setInterval(() => {
    if (cooldown.value > 0) {
      cooldown.value -= 1;
    } else {
      clearInterval(cooldownTimer);
      cooldownTimer = null;
    }
  }, 1000);
}

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer);
});

async function handleRequestLoginOTP() {
  errorMessage.value = '';
  infoMessage.value = '';

  const cleanEmail = email.value.trim().toLowerCase();
  if (!cleanEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
    errorMessage.value = 'Please enter a valid email address.';
    return;
  }

  loading.value = true;
  try {
    const res = await authService.requestOTP({
      email: cleanEmail,
      purpose: 'login'
    });
    maskedEmail.value = res.masked_email;
    infoMessage.value = res.message || 'Verification code sent if email is registered.';
    startCooldown(res.cooldown_seconds || 60);
    step.value = 'verify';
  } catch (err: any) {
    if (err instanceof ApiError) {
      errorMessage.value = err.message;
      if (err.retryAfter) {
        startCooldown(err.retryAfter);
      }
    } else {
      errorMessage.value = 'Unable to connect to login service. Please verify server status.';
    }
  } finally {
    loading.value = false;
  }
}

async function handleVerifyLoginOTP() {
  errorMessage.value = '';
  infoMessage.value = '';

  if (otpCode.value.length !== 6 || !/^[0-9]{6}$/.test(otpCode.value)) {
    errorMessage.value = 'Please enter the complete 6-digit numeric verification code.';
    return;
  }

  loading.value = true;
  try {
    const cleanEmail = email.value.trim().toLowerCase();
    const tokenData = await authService.verifyOTP({
      email: cleanEmail,
      code: otpCode.value.trim(),
      purpose: 'login'
    });

    authStore.setSession(tokenData.access_token);
    await authStore.initSession();

    const redirectPath = (route.query.redirect as string) || '/dashboard';
    router.push(redirectPath);
  } catch (err: any) {
    if (err instanceof ApiError) {
      errorMessage.value = err.message;
    } else {
      errorMessage.value = 'Failed to verify code. Please try again.';
    }
  } finally {
    loading.value = false;
  }
}

async function handleAdminPasswordLogin() {
  errorMessage.value = '';
  infoMessage.value = '';

  if (!adminUsername.value.trim() || !adminPassword.value) {
    errorMessage.value = 'Please enter username and password.';
    return;
  }

  loading.value = true;
  try {
    const tokenData = await apiRequest<TokenResponseData>('/api/v1/account/login', {
      method: 'POST',
      body: JSON.stringify({
        username: adminUsername.value.trim(),
        password: adminPassword.value
      })
    });

    authStore.setSession(tokenData.access_token);
    await authStore.initSession();

    const redirectPath = (route.query.redirect as string) || '/dashboard';
    router.push(redirectPath);
  } catch (err: any) {
    if (err instanceof ApiError) {
      errorMessage.value = err.message;
    } else {
      errorMessage.value = 'Admin authentication failed.';
    }
  } finally {
    loading.value = false;
  }
}

function handleBackToEmail() {
  step.value = 'email';
  otpCode.value = '';
  errorMessage.value = '';
}
</script>

<template>
  <div class="auth-page">
    <div class="container auth-container">
      <div class="card auth-card fade-in">
        <div class="auth-header">
          <span class="badge">TACTICAL AUTHENTICATION</span>
          <h1 class="auth-title">PLAYER LOGIN</h1>
          <p class="auth-subtitle">
            Authenticate to your ROS Sothat private island account.
          </p>
        </div>

        <!-- Mode Toggle -->
        <div class="auth-mode-toggle">
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: loginMode === 'otp' }"
            @click="loginMode = 'otp'; errorMessage = ''; infoMessage = ''"
          >
            Email OTP (Player)
          </button>
          <button
            type="button"
            class="toggle-btn"
            :class="{ active: loginMode === 'admin' }"
            @click="loginMode = 'admin'; errorMessage = ''; infoMessage = ''"
          >
            Admin Password
          </button>
        </div>

        <!-- Alerts -->
        <div v-if="errorMessage" class="alert alert-danger" role="alert">
          {{ errorMessage }}
        </div>
        <div v-if="infoMessage" class="alert alert-info" role="status">
          {{ infoMessage }}
        </div>

        <!-- Mode 1: Email OTP Login -->
        <div v-if="loginMode === 'otp'">
          <!-- Step 1: Email Input -->
          <form v-if="step === 'email'" @submit.prevent="handleRequestLoginOTP" class="auth-form">
            <div class="form-group">
              <label for="login-email" class="form-label">Player Email Address</label>
              <input
                id="login-email"
                v-model="email"
                type="email"
                required
                class="form-input"
                placeholder="e.g. operator@ros-sothat.internal"
                :disabled="loading"
                autocomplete="email"
              />
            </div>

            <button
              type="submit"
              class="btn btn-primary btn-block"
              :disabled="loading || cooldown > 0"
            >
              <span v-if="loading">DISPATCHING CODE...</span>
              <span v-else-if="cooldown > 0">RESEND IN {{ cooldown }}S</span>
              <span v-else>SEND LOGIN CODE</span>
            </button>
          </form>

          <!-- Step 2: OTP Verification -->
          <form v-else @submit.prevent="handleVerifyLoginOTP" class="auth-form">
            <div class="verification-meta">
              <span class="verify-target">Code sent to: <strong>{{ maskedEmail || email }}</strong></span>
              <button type="button" class="btn-text" @click="handleBackToEmail">Change Email</button>
            </div>

            <div class="form-group">
              <label class="form-label" style="text-align: center;">Enter 6-Digit Verification Code</label>
              <OtpInput v-model="otpCode" :disabled="loading" @complete="handleVerifyLoginOTP" />
            </div>

            <button
              type="submit"
              class="btn btn-primary btn-block"
              :disabled="loading || otpCode.length !== 6"
            >
              <span v-if="loading">AUTHENTICATING...</span>
              <span v-else>VERIFY & LOG IN</span>
            </button>

            <div class="resend-row">
              <button
                type="button"
                class="btn-text"
                :disabled="cooldown > 0 || loading"
                @click="handleRequestLoginOTP"
              >
                <span v-if="cooldown > 0">Resend code in {{ cooldown }}s</span>
                <span v-else>Didn't receive code? Resend Code</span>
              </button>
            </div>
          </form>
        </div>

        <!-- Mode 2: Admin Password Login (Preserved) -->
        <div v-else>
          <form @submit.prevent="handleAdminPasswordLogin" class="auth-form">
            <div class="form-group">
              <label for="admin-user" class="form-label">Administrator Username</label>
              <input
                id="admin-user"
                v-model="adminUsername"
                type="text"
                required
                class="form-input"
                placeholder="e.g. chief_admin"
                :disabled="loading"
                autocomplete="username"
              />
            </div>

            <div class="form-group">
              <label for="admin-pass" class="form-label">Password</label>
              <input
                id="admin-pass"
                v-model="adminPassword"
                type="password"
                required
                class="form-input"
                placeholder="••••••••••••"
                :disabled="loading"
                autocomplete="current-password"
              />
            </div>

            <button
              type="submit"
              class="btn btn-primary btn-block"
              :disabled="loading"
            >
              <span v-if="loading">AUTHENTICATING...</span>
              <span v-else>ADMIN LOGIN</span>
            </button>
          </form>
        </div>

        <div class="auth-footer">
          <span>Need an invite?</span>
          <RouterLink to="/register" class="gold-link">Register New Account</RouterLink>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 200px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem 1.5rem;
}

.container {
  max-width: 520px;
  width: 100%;
}

.auth-card {
  padding: 2.5rem;
  border-color: rgba(215, 168, 75, 0.25);
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.4);
}

.auth-header {
  text-align: center;
  margin-bottom: 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.auth-title {
  font-size: 1.75rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.auth-subtitle {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.auth-mode-toggle {
  display: flex;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  padding: 3px;
  margin-bottom: 1.5rem;
}

.toggle-btn {
  flex: 1;
  background: none;
  border: none;
  padding: 0.5rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.2s ease;
}

.toggle-btn.active {
  background-color: var(--bg-card);
  color: var(--accent-gold);
  border: 1px solid var(--border-color);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.auth-form {
  display: flex;
  flex-direction: column;
}

.verification-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 1rem;
  background-color: var(--bg-secondary);
  padding: 0.6rem 0.8rem;
  border-radius: 4px;
}

.btn-text {
  background: none;
  border: none;
  color: var(--accent-gold);
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
  text-decoration: underline;
}

.btn-text:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  text-decoration: none;
}

.resend-row {
  text-align: center;
  margin-top: 1rem;
}

.auth-footer {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.gold-link {
  font-weight: 700;
  color: var(--accent-gold);
}
</style>
