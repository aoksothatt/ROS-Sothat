export interface CharacterStats {
  total_matches: number;
  total_wins: number;
  total_kills: number;
  damage_dealt: number;
}

export interface CharacterAppearances {
  equipped_clothing: number[];
  unlocked_items: number[];
  active_weapon_skin: number;
}

export interface CharacterSettings {
  control_mode: number;
  fov: number;
  gyroscope: boolean;
  sensitivity: {
    general: number;
    aim: number;
    scope2x: number;
    [key: string]: number;
  };
}

export interface CharacterProfile {
  gid: number;
  account_id: number;
  nickname: string;
  char_type: number; // 0: Male, 1: Female
  level: number;
  exp: number;
  gold: number;
  diamonds: number;
  appearances: CharacterAppearances;
  settings: CharacterSettings;
  stats: CharacterStats;
  created_at: string;
  updated_at: string;
}

export interface CatalogItem {
  id: number;
  item_code: string;
  name: string;
  description: string;
  item_type: string;
  icon: string | null;
  stackable: boolean;
  max_stack: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryItem {
  id: number;
  character_gid: number;
  item_id: number;
  quantity: number;
  created_at: string;
  updated_at: string;
  item?: CatalogItem;
}

export interface CharacterInventoryResponse {
  character_gid: number;
  total_items: number;
  items: InventoryItem[];
}

export interface DiamondTransaction {
  id: number;
  character_gid: number;
  admin_account_id: number;
  operation_type: 'GRANT' | 'DEDUCT';
  amount: number;
  balance_before: number;
  balance_after: number;
  idempotency_key: string;
  reason: string;
  created_at: string;
}

export interface DiamondHistoryResponse {
  character_gid: number;
  current_balance: number;
  total_transactions: number;
  transactions: DiamondTransaction[];
}
