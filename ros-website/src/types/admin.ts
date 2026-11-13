export interface AdminAuditLog {
  id: number;
  admin_account_id: number;
  admin_username?: string | null;
  action_type: string;
  target_type: string;
  target_id: number;
  reason: string;
  details: Record<string, any>;
  created_at: string;
}

export interface AdminAuditLogListResponse {
  total: number;
  limit: number;
  offset: number;
  logs: AdminAuditLog[];
}

export interface AdminDashboardSummary {
  total_accounts: number;
  active_accounts: number;
  suspended_accounts: number;
  total_characters: number;
  total_diamonds: number;
  total_inventory_items: number;
  active_lobby_presences: number;
  active_rooms: number;
  queued_matchmaking_tickets: number;
  recent_activity: AdminAuditLog[];
}

export interface AdminPlayerSummary {
  account_id: number;
  username: string;
  email?: string | null;
  role: string;
  is_banned: boolean;
  ban_reason?: string | null;
  created_at: string;
  last_login?: string | null;
  character_gid?: number | null;
  character_nickname?: string | null;
  character_level?: number | null;
  diamonds?: number | null;
}

export interface AdminPlayerListResponse {
  total: number;
  limit: number;
  offset: number;
  players: AdminPlayerSummary[];
}

export interface AdminPlayerDetail {
  account_id: number;
  username: string;
  email?: string | null;
  role: string;
  is_banned: boolean;
  ban_reason?: string | null;
  created_at: string;
  last_login?: string | null;
  character?: {
    gid: number;
    nickname: string;
    char_type: number;
    level: number;
    exp: number;
    gold: number;
    diamonds: number;
    appearances: Record<string, any>;
    settings: Record<string, any>;
    stats: Record<string, any>;
    created_at?: string;
    updated_at?: string;
  } | null;
  inventory_items: Array<{
    id: number;
    item_id: number;
    quantity: number;
    item_name: string;
    item_type: string;
    stackable: boolean;
    max_stack: number;
    is_active: boolean;
  }>;
  recent_diamond_transactions: Array<{
    id: number;
    operation_type: string;
    amount: number;
    balance_before: number;
    balance_after: number;
    reason: string;
    created_at: string;
  }>;
  recent_audit_logs: AdminAuditLog[];
}

export interface CatalogItem {
  id: number;
  item_code: string;
  name: string;
  description: string;
  item_type: string;
  icon?: string | null;
  stackable: boolean;
  max_stack: number;
  is_active: boolean;
}

export interface DiamondMutationPayload {
  amount: number;
  reason: string;
  idempotency_key: string;
}

export interface InventoryGrantPayload {
  item_id: number;
  quantity: number;
  reason: string;
  idempotency_key: string;
}

export interface InventoryRemovePayload {
  item_id: number;
  quantity: number;
  reason: string;
  idempotency_key: string;
}

export interface SuspendPayload {
  reason: string;
}

export interface ReactivatePayload {
  reason: string;
}
