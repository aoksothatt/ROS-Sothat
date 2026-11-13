<script setup lang="ts">
import { ref } from 'vue';
import AdminSidebar from './AdminSidebar.vue';
import AdminHeader from './AdminHeader.vue';

defineProps<{
  title: string;
  subtitle?: string;
}>();

const mobileSidebarOpen = ref(false);

function toggleSidebar() {
  mobileSidebarOpen.value = !mobileSidebarOpen.value;
}

function closeSidebar() {
  mobileSidebarOpen.value = false;
}
</script>

<template>
  <div class="admin-shell">
    <!-- Backdrop for mobile drawer -->
    <div
      v-if="mobileSidebarOpen"
      class="sidebar-backdrop"
      @click="closeSidebar"
    ></div>

    <AdminSidebar
      :mobile-open="mobileSidebarOpen"
      @close="closeSidebar"
    />

    <main class="admin-main-content">
      <div class="admin-inner-container">
        <AdminHeader
          :title="title"
          :subtitle="subtitle"
          @toggle-sidebar="toggleSidebar"
        />

        <div class="admin-body">
          <slot></slot>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.admin-shell {
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

.admin-main-content {
  flex: 1;
  padding: 0 2rem 3rem 2rem;
  overflow-y: auto;
  max-width: 100%;
}

.admin-inner-container {
  max-width: 1200px;
  margin: 0 auto;
}

@media (max-width: 900px) {
  .admin-main-content {
    padding: 0 1rem 2.5rem 1rem;
  }
}
</style>
