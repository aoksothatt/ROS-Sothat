<script setup lang="ts">
import { ref, onUnmounted } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { authService } from '@/services/auth';
import { useAuthStore } from '@/stores/auth';
import { ApiError } from '@/services/api';
import OtpInput from '@/components/OtpInput.vue';

const router = useRouter();
const authStore = useAuthStore();

const email = ref('');
const username = ref('');
const otpCode = ref('');

const step = ref<'email' | 'verify'>('email');
const loading = ref(false);
const errorMessage = ref('');
const infoMessage = ref('');
const maskedEmail = ref('');

// Cooldown timer
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

async function handleRequestOTP() {
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
      purpose: 'registration'
    });
    maskedEmail.value = res.masked_email;
    infoMessage.value = res.message || 'Verification code dispatched to your inbox.';
    startCooldown(res.cooldown_seconds || 60);
    step.value = 'verify';
  } catch (err: any) {
    if (err instanceof ApiError) {
      errorMessage.value = err.message;
      if (err.retryAfter) {
        startCooldown(err.retryAfter);
      }
    } else {
      errorMessage.value = 'An unexpected error occurred. Please check your network connection.';
    }
  } finally {
    loading.value = false;
  }
}

async function handleVerifyOTP() {
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
      purpose: 'registration',
      username: username.value.trim() || undefined
    });

    // Save session in auth store
    authStore.setSession(tokenData.access_token);
    await authStore.initSession();

    router.push({ name: 'dashboard' });
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
          <span class="badge">TACTICAL ACCESS</span>
          <h1 class="auth-title">JOIN ROS SOTHAT</h1>
          <p class="auth-subtitle">
            Private multiplayer community registration for invited players.
          </p>
        </div>

        <!-- Alert notifications -->
        <div v-if="errorMessage" class="alert alert-danger" role="alert">
          {{ errorMessage }}
        </div>
        <div v-if="infoMessage" class="alert alert-info" role="status">
          {{ infoMessage }}
        </div>

        <!-- Step 1: Email Form -->
        <form v-if="step === 'email'" @submit.prevent="handleRequestOTP" class="auth-form">
          <div class="form-group">
            <label for="reg-email" class="form-label">Email Address</label>
            <input
              id="reg-email"
              v-model="email"
              type="email"
              required
              class="form-input"
              placeholder="e.g. operator@ros-sothat.internal"
              :disabled="loading"
              autocomplete="email"
            />
          </div>

          <div class="form-group">
            <label for="reg-username" class="form-label">Chosen Nickname (Optional)</label>
            <input
              id="reg-username"
              v-model="username"
              type="text"
              class="form-input"
              placeholder="e.g. GhostSniper (auto-generated if empty)"
              maxlength="32"
              :disabled="loading"
              autocomplete="username"
            />
          </div>

          <button
            type="submit"
            class="btn btn-primary btn-block"
            :disabled="loading || cooldown > 0"
          >
            <span v-if="loading">DISPATCHING CODE...</span>
            <span v-else-if="cooldown > 0">RESEND IN {{ cooldown }}S</span>
            <span v-else>SEND VERIFICATION CODE</span>
          </button>
        </form>

        <!-- Step 2: OTP Verification Form -->
        <form v-else @submit.prevent="handleVerifyOTP" class="auth-form">
          <div class="verification-meta">
            <span class="verify-target">Code sent to: <strong>{{ maskedEmail || email }}</strong></span>
            <button type="button" class="btn-text" @click="handleBackToEmail">Change Email</button>
          </div>

          <div class="form-group">
            <label class="form-label" style="text-align: center;">Enter 6-Digit Verification Code</label>
            <OtpInput v-model="otpCode" :disabled="loading" @complete="handleVerifyOTP" />
          </div>

          <button
            type="submit"
            class="btn btn-primary btn-block"
            :disabled="loading || otpCode.length !== 6"
          >
            <span v-if="loading">VERIFYING CODE...</span>
            <span v-else>VERIFY & REGISTER ACCOUNT</span>
          </button>

          <div class="resend-row">
            <button
              type="button"
              class="btn-text resend-btn"
              :disabled="cooldown > 0 || loading"
              @click="handleRequestOTP"
            >
              <span v-if="cooldown > 0">Resend code in {{ cooldown }}s</span>
              <span v-else>Didn't receive code? Resend Code</span>
            </button>
          </div>
        </form>

        <div class="auth-footer">
          <span>Already have an account?</span>
          <RouterLink to="/login" class="gold-link">Login with Email OTP</RouterLink>
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
  margin-bottom: 2rem;
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
