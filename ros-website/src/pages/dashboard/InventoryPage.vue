<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { playerService } from '@/services/player';
import type { CharacterProfile, CharacterInventoryResponse } from '@/types/dashboard';
import DashboardLayout from '@/components/dashboard/DashboardLayout.vue';
import LoadingState from '@/components/dashboard/LoadingState.vue';
import EmptyState from '@/components/dashboard/EmptyState.vue';

const authStore = useAuthStore();
const character = ref<CharacterProfile | null>(null);
const inventoryData = ref<CharacterInventoryResponse | null>(null);
const loading = ref(true);
const errorMessage = ref('');
const activeCategory = ref<string>('ALL');

const categories = [
  { id: 'ALL', label: 'All Items' },
  { id: 'WEAPON_SKIN', label: 'Weapons & Skins' },
  { id: 'CLOTHING', label: 'Clothing & Gear' },
  { id: 'CONSUMABLE', label: 'Consumables & Supplies' }
];

onMounted(async () => {
  if (!authStore.token) return;
  loading.value = true;
  errorMessage.value = '';
  try {
    character.value = await playerService.getMyCharacter(authStore.token);
    if (character.value) {
      inventoryData.value = await playerService.getMyInventory(authStore.token, 100, 0);
    }
  } catch (err: any) {
    errorMessage.value = err.message || 'Failed to retrieve tactical armory inventory.';
  } finally {
    loading.value = false;
  }
});

const filteredItems = computed(() => {
  if (!inventoryData.value || !inventoryData.value.items) return [];
  if (activeCategory.value === 'ALL') {
    return inventoryData.value.items;
  }
  return inventoryData.value.items.filter(
    (inv) => inv.item?.item_type === activeCategory.value
  );
});

function getItemIcon(itemType?: string) {
  switch (itemType) {
    case 'WEAPON_SKIN':
      return '🔫';
    case 'CLOTHING':
      return '🦺';
    case 'CONSUMABLE':
      return '🧪';
    default:
      return '📦';
  }
}
</script>

<template>
  <DashboardLayout
    title="Tactical Armory & Inventory"
    subtitle="Personal item inventory, equipment slots, and skin configurations."
  >
    <div v-if="loading">
      <LoadingState message="Scanning personal island supply locker and inventory..." />
    </div>

    <div v-else class="inventory-content fade-in">
      <div v-if="errorMessage" class="alert alert-danger" role="alert">
        {{ errorMessage }}
      </div>

      <!-- If character does not exist -->
      <div v-if="!character" class="card">
        <EmptyState
          icon="🎒"
          title="ARMORY UNINITIALIZED"
          description="You must deploy a character profile before accessing personal storage. Visit the Profile page to initialize your character."
        />
      </div>

      <template v-else>
        <!-- Filter Bar & Summary Header -->
        <div class="card inventory-toolbar">
          <div class="category-filters">
            <button
              v-for="cat in categories"
              :key="cat.id"
              class="filter-pill"
              :class="{ active: activeCategory === cat.id }"
              @click="activeCategory = cat.id"
            >
              {{ cat.label }}
            </button>
          </div>

          <div class="inventory-status-pill">
            <span class="status-label">Items Stored:</span>
            <span class="status-num">{{ inventoryData ? inventoryData.total_items : 0 }}</span>
          </div>
        </div>

        <!-- Empty Inventory State -->
        <div v-if="filteredItems.length === 0" class="card empty-inventory-wrapper">
          <EmptyState
            icon="🎒"
            title="INVENTORY LOCKER EMPTY"
            :description="activeCategory === 'ALL'
              ? 'Your tactical supply locker currently contains zero items. Items acquired through survival matches, rewards, and official airdrops will appear here.'
              : `No items found matching the selected category '${activeCategory}'.`"
          />
        </div>

        <!-- Inventory Grid -->
        <div v-else class="inventory-grid">
          <div
            v-for="inv in filteredItems"
            :key="inv.id"
            class="card item-card"
          >
            <div class="item-card-header">
              <span class="item-type-badge badge">{{ inv.item?.item_type || 'ITEM' }}</span>
              <span class="quantity-badge">x{{ inv.quantity }}</span>
            </div>

            <div class="item-visual">
              <div class="item-glyph">{{ getItemIcon(inv.item?.item_type) }}</div>
            </div>

            <div class="item-body">
              <h4 class="item-name">{{ inv.item?.name || `Item #${inv.item_id}` }}</h4>
              <span class="item-code mono">{{ inv.item?.item_code || 'CODE_UNKNOWN' }}</span>
              <p class="item-description">
                {{ inv.item?.description || 'Standard tactical supply equipment.' }}
              </p>
            </div>

            <div class="item-footer">
              <span class="stack-info" v-if="inv.item?.stackable">
                Stackable (Max: {{ inv.item.max_stack }})
              </span>
              <span class="stack-info" v-else>Unique Slot</span>
            </div>
          </div>
        </div>

        <!-- Read-Only Notice -->
        <div class="card policy-notice-card">
          <span class="notice-icon">🔒</span>
          <div class="notice-text">
            <strong>Locker Security Enforcement:</strong> Items cannot be spawned, duplicated, or removed through web endpoints. All inventory records are scoped strictly to your authenticated character.
          </div>
        </div>
      </template>
    </div>
  </DashboardLayout>
</template>

<style scoped>
.inventory-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.inventory-toolbar {
  padding: 1rem 1.25rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.category-filters {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.filter-pill {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 0.4rem 0.85rem;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-transform: uppercase;
}

.filter-pill:hover {
  background-color: var(--bg-card);
  color: var(--text-primary);
}

.filter-pill.active {
  background-color: var(--bg-card);
  border-color: var(--accent-gold);
  color: var(--accent-gold);
}

.inventory-status-pill {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.status-label {
  color: var(--text-secondary);
}

.status-num {
  font-family: var(--font-mono);
  font-weight: 800;
  color: var(--accent-gold);
}

.inventory-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 1.25rem;
}

.item-card {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  transition: transform 0.2s ease, border-color 0.2s ease;
  background: linear-gradient(180deg, var(--bg-card) 0%, #111A24 100%);
}

.item-card:hover {
  transform: translateY(-2px);
  border-color: rgba(215, 168, 75, 0.4);
}

.item-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quantity-badge {
  background-color: rgba(215, 168, 75, 0.15);
  border: 1px solid rgba(215, 168, 75, 0.3);
  color: var(--accent-gold);
  font-size: 0.75rem;
  font-family: var(--font-mono);
  font-weight: 800;
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
}

.item-visual {
  height: 110px;
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.item-glyph {
  font-size: 3rem;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.5));
}

.item-body {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  flex: 1;
}

.item-name {
  font-size: 1rem;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0;
}

.item-code {
  font-size: 0.75rem;
  color: var(--accent-gold);
}

.item-description {
  font-size: 0.8rem;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 0;
}

.item-footer {
  padding-top: 0.75rem;
  border-top: 1px solid var(--border-color);
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.policy-notice-card {
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  background-color: rgba(38, 52, 66, 0.4);
  border: 1px solid var(--border-color);
}

.notice-icon {
  font-size: 1.4rem;
}

.notice-text {
  font-size: 0.85rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.notice-text strong {
  color: var(--text-primary);
}
</style>
