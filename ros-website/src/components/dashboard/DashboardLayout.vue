<script setup lang="ts">
import { ref, onMounted, provide } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { playerService } from '@/services/player';
import type { CharacterProfile } from '@/types/dashboard';
import DashboardSidebar from './DashboardSidebar.vue';
import DashboardHeader from './DashboardHeader.vue';

defineProps<{
  title: string;
  subtitle?: string;
}>();

const authStore = useAuthStore();
const mobileSidebarOpen = ref(false);
const character = ref<CharacterProfile | null>(null);
const loadingChar = ref(true);

onMounted(async () => {
  if (authStore.token) {
    try {
      character.value = await playerService.getMyCharacter(authStore.token);
    } catch {
      character.value = null;
    } finally {
      loadingChar.value = false;
    }
  }
});

// Provide character down to child views
provide('characterProfile', character);
provide('loadingCharacter', loadingChar);

function toggleSidebar() {
  mobileSidebarOpen.value = !mobileSidebarOpen.value;
}

function closeSidebar() {
  mobileSidebarOpen.value = false;
}
</script>

<template>
  <div class="dashboard-shell">
    <!-- Backdrop for mobile drawer -->
    <div
      v-if="mobileSidebarOpen"
      class="sidebar-backdrop"
      @click="closeSidebar"
    ></div>

    <DashboardSidebar
      :mobile-open="mobileSidebarOpen"
      @close="closeSidebar"
    />

    <main class="dashboard-main-content">
      <div class="dashboard-inner-container">
        <DashboardHeader
          :title="title"
          :subtitle="subtitle"
          :character="character"
          @toggle-sidebar="toggleSidebar"
        />

        <div class="dashboard-body">
          <slot :character="character" :loading="loadingChar"></slot>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard-shell {
  display: flex;
  min-height: calc(100vh - 70px);
  background-color: var(--bg-primary);
  position: relative;
}

.sidebar-backdrop {
  display: none;
}

@media (max-width: 900px) {
  .sidebar-backdrop {
    display: block;
    position: fixed;
    top: 70px;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.75);
    backdrop-filter: blur(4px);
    z-index: 85;
  }
}

.dashboard-main-content {
  flex: 1;
  padding: 2rem 1.5rem;
  overflow-x: hidden;
}

.dashboard-inner-container {
  max-width: 1200px;
  margin: 0 auto;
}

.dashboard-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
</style>
