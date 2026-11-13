<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { playerService } from '@/services/player';
import type { CharacterProfile } from '@/types/dashboard';
import DashboardLayout from '@/components/dashboard/DashboardLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const character = ref<CharacterProfile | null>(null);
const loading = ref(true);
const errorMessage = ref('');
const successMessage = ref('');

// Form state for creating a character if none exists
const newNickname = ref('');
const newCharType = ref(0);
const creating = ref(false);

async function loadProfile() {
  if (!authStore.token) return;
  loading.value = true;
  errorMessage.value = '';
  try {
    character.value = await playerService.getMyCharacter(authStore.token);
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to load player character profile.';
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadProfile();
});

async function handleCreateCharacter() {
  if (!newNickname.value.trim()) {
    errorMessage.value = 'Please provide an in-game callsign.';
    return;
  }
  if (!authStore.token) return;

  creating.value = true;
  errorMessage.value = '';
  try {
    const created = await playerService.createCharacter(
      authStore.token,
      newNickname.value.trim(),
      newCharType.value
    );
    character.value = created;
    successMessage.value = `Character profile '${created.nickname}' provisioned successfully!`;
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to create character profile.';
  } finally {
    creating.value = false;
  }
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return 'Never';
  try {
    return new Date(iso).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return iso;
  }
}
</script>

<template>
  <DashboardLayout
    title="Operator Profile"
    subtitle="Personal military dossier, character assignment, and equipped loadout."
  >
    <div v-if="loading">
      <LoadingState message="Retrieving operator credentials and character dossier..." />
    </div>

    <div v-else class="profile-content fade-in">
      <div v-if="errorMessage" class="alert alert-danger" role="alert">
        {{ errorMessage }}
      </div>
      <div v-if="successMessage" class="alert alert-info" role="status">
        {{ successMessage }}
      </div>

      <!-- If character does not exist, show character creation onboarding -->
      <div v-if="!character" class="card onboarding-card">
        <EmptyState
          icon="🎖️"
          title="NO CHARACTER PROVISIONED"
          description="Your account is active, but you have not yet deployed an in-game character to the island. Assign your tactical callsign below to initialize your character."
        >
          <template #action>
            <form @submit.prevent="handleCreateCharacter" class="create-char-form">
              <div class="form-group">
                <label for="char-nickname" class="form-label">In-Game Callsign / Nickname</label>
                <input
                  id="char-nickname"
                  v-model="newNickname"
                  type="text"
                  required
                  class="form-input"
                  placeholder="e.g. ShadowViper"
                  maxlength="24"
                  :disabled="creating"
                />
              </div>

              <div class="form-group">
                <label class="form-label">Operative Model / Gender</label>
                <div class="char-type-selector">
                  <label class="radio-label">
                    <input type="radio" v-model="newCharType" :value="0" :disabled="creating" />
                    <span>Male Operative (Type 0)</span>
                  </label>
                  <label class="radio-label">
                    <input type="radio" v-model="newCharType" :value="1" :disabled="creating" />
                    <span>Female Operative (Type 1)</span>
                  </label>
                </div>
              </div>

              <button type="submit" class="btn btn-primary" :disabled="creating">
                <span v-if="creating">PROVISIONING DOSSIER...</span>
                <span v-else>INITIALIZE CHARACTER DOSSIER</span>
              </button>
            </form>
          </template>
        </EmptyState>
      </div>

      <!-- If character exists, render full character dossier -->
      <div v-else class="dossier-grid">
        <!-- Card 1: Identity & Level Banner -->
        <div class="card character-dossier-card">
          <div class="dossier-header">
            <div class="dossier-avatar">
              <span>{{ character.nickname.slice(0, 2).toUpperCase() }}</span>
            </div>
            <div class="dossier-title-wrap">
              <span class="badge">CALLSIGN IDENTIFIER</span>
              <h2 class="char-title">{{ character.nickname }}</h2>
              <span class="char-gid">GID #{{ character.gid }} • {{ character.char_type === 0 ? 'Male' : 'Female' }} Operative</span>
            </div>
          </div>

          <div class="level-progress-wrap">
            <div class="level-header">
              <span class="level-badge">LEVEL {{ character.level }}</span>
              <span class="exp-text">{{ character.exp }} / 1,000 EXP</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" :style="{ width: `${Math.min((character.exp / 1000) * 100, 100)}%` }"></div>
            </div>
          </div>

          <div class="dossier-currency-row">
            <div class="dossier-curr">
              <span class="curr-icon">💎</span>
              <div class="curr-col">
                <span class="curr-amount gold">{{ character.diamonds.toLocaleString() }}</span>
                <span class="curr-name">Diamonds</span>
              </div>
            </div>
            <div class="dossier-curr">
              <span class="curr-icon">🪙</span>
              <div class="curr-col">
                <span class="curr-amount">{{ character.gold.toLocaleString() }}</span>
                <span class="curr-name">Island Gold</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Card 2: Account Security Dossier -->
        <div class="card account-meta-card">
          <h3 class="card-section-title">ACCOUNT TELEMETRY</h3>
          <ul class="meta-list">
            <li class="meta-row">
              <span class="m-label">Account GID:</span>
              <span class="m-val">#{{ authStore.user?.id }}</span>
            </li>
            <li class="meta-row">
              <span class="m-label">Platform Role:</span>
              <span class="m-val badge" :class="{ 'badge-dev': authStore.user?.role === 'admin' }">
                {{ authStore.user?.role.toUpperCase() }}
              </span>
            </li>
            <li class="meta-row">
              <span class="m-label">Linked Email:</span>
              <span class="m-val">{{ authStore.user?.email || 'None' }}</span>
            </li>
            <li class="meta-row">
              <span class="m-label">Registered On:</span>
              <span class="m-val">{{ formatDate(character.created_at) }}</span>
            </li>
            <li class="meta-row">
              <span class="m-label">Last Synchronized:</span>
              <span class="m-val">{{ formatDate(character.updated_at) }}</span>
            </li>
            <li class="meta-row">
              <span class="m-label">Enforcement Status:</span>
              <span class="m-val success">GOOD STANDING</span>
            </li>
          </ul>
        </div>

        <!-- Card 3: Equipped Cosmetic Loadout -->
        <div class="card loadout-card">
          <h3 class="card-section-title">EQUIPPED APPEARANCES & LOADOUT</h3>
          <div class="loadout-grid">
            <div class="loadout-slot">
              <span class="slot-title">Active Weapon Skin</span>
              <span class="slot-value" :class="character.appearances.active_weapon_skin ? 'gold' : ''">
                {{ character.appearances.active_weapon_skin ? `Skin #${character.appearances.active_weapon_skin}` : 'Default Standard Skin' }}
              </span>
            </div>
            <div class="loadout-slot">
              <span class="slot-title">Equipped Clothing Items</span>
              <div class="clothing-tags">
                <span
                  v-for="clothId in character.appearances.equipped_clothing"
                  :key="clothId"
                  class="clothing-tag"
                >
                  Item #{{ clothId }}
                </span>
                <span v-if="character.appearances.equipped_clothing.length === 0" class="empty-note">
                  Standard Training Uniform
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Card 4: Gameplay Settings Preview -->
        <div class="card settings-preview-card">
          <h3 class="card-section-title">CONTROL & VISUAL CONFIGURATION</h3>
          <div class="settings-grid">
            <div class="setting-item">
              <span class="s-label">Control Mode</span>
              <span class="s-val">Mode {{ character.settings.control_mode || 1 }}</span>
            </div>
            <div class="setting-item">
              <span class="s-label">Field of View (FOV)</span>
              <span class="s-val">{{ character.settings.fov || 75 }}°</span>
            </div>
            <div class="setting-item">
              <span class="s-label">Gyroscope Aiming</span>
              <span class="s-val">{{ character.settings.gyroscope ? 'ENABLED' : 'DISABLED' }}</span>
            </div>
            <div class="setting-item">
              <span class="s-label">General Aim Sensitivity</span>
              <span class="s-val">{{ character.settings.sensitivity?.general || 100 }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </DashboardLayout>
</template>

<style scoped>
.profile-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.onboarding-card {
  padding: 2rem;
}

.create-char-form {
  max-width: 400px;
  margin: 1.5rem auto 0;
  text-align: left;
}

.char-type-selector {
  display: flex;
  gap: 1.5rem;
  margin-top: 0.5rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-primary);
  cursor: pointer;
}

.dossier-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 1.5rem;
}

.character-dossier-card {
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  background: linear-gradient(135deg, var(--bg-card) 0%, #172433 100%);
  border-top: 3px solid var(--accent-gold);
}

.dossier-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.dossier-avatar {
  width: 60px;
  height: 60px;
  background: var(--bg-secondary);
  border: 2px solid var(--accent-gold);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 900;
  font-family: var(--font-mono);
  color: var(--accent-gold);
}

.dossier-title-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.char-title {
  font-size: 1.4rem;
  font-weight: 900;
  letter-spacing: 0.05em;
  margin: 0;
  text-transform: uppercase;
}

.char-gid {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.level-progress-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.level-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.level-badge {
  font-size: 0.75rem;
  font-weight: 800;
  color: var(--accent-gold);
  background-color: rgba(215, 168, 75, 0.15);
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
  letter-spacing: 0.05em;
}

.exp-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.progress-bar-bg {
  width: 100%;
  height: 8px;
  background-color: var(--bg-secondary);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #B58532, var(--accent-gold));
  border-radius: 4px;
}

.dossier-currency-row {
  display: flex;
  gap: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.dossier-curr {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.curr-col {
  display: flex;
  flex-direction: column;
}

.curr-amount {
  font-size: 1.25rem;
  font-weight: 900;
  font-family: var(--font-mono);
}

.curr-amount.gold {
  color: var(--accent-gold);
}

.curr-name {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.account-meta-card, .loadout-card, .settings-preview-card {
  padding: 1.75rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.card-section-title {
  font-size: 0.85rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--text-secondary);
  margin: 0;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 0.5rem;
}

.meta-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.m-label {
  color: var(--text-secondary);
}

.m-val {
  font-family: var(--font-mono);
  font-weight: 600;
}

.m-val.success {
  color: #4CAF50;
  font-weight: 800;
}

.loadout-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.loadout-slot {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  background-color: var(--bg-secondary);
  padding: 0.75rem 1rem;
  border-radius: 4px;
  border: 1px solid var(--border-color);
}

.slot-title {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 700;
}

.slot-value {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-primary);
}

.slot-value.gold {
  color: var(--accent-gold);
}

.clothing-tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.clothing-tag {
  background-color: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--accent-gold);
  font-size: 0.75rem;
  font-family: var(--font-mono);
  padding: 0.2rem 0.5rem;
  border-radius: 3px;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  background-color: var(--bg-secondary);
  padding: 0.75rem;
  border-radius: 4px;
}

.s-label {
  font-size: 0.7rem;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.s-val {
  font-size: 0.85rem;
  font-weight: 700;
  font-family: var(--font-mono);
}
</style>
