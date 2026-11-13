import { apiRequest } from '@/services/api';
import type {
  AdminDashboardSummary,
  AdminPlayerListResponse,
  AdminPlayerDetail,
  AdminPlayerSummary,
  AdminAuditLogListResponse,
  CatalogItem,
  DiamondMutationPayload,
  InventoryGrantPayload,
  InventoryRemovePayload,
  SuspendPayload,
  ReactivatePayload
} from '@/types/admin';

export const adminService = {
  /**
   * Fetch aggregate administrative overview and recent activity.
   */
  async getSummary(token: string): Promise<AdminDashboardSummary> {
    return apiRequest<AdminDashboardSummary>('/api/v1/admin/dashboard/summary', {
      method: 'GET'
    }, token);
  },

  /**
   * Search and paginate player accounts with character info.
   */
  async listPlayers(
    token: string,
    params: { q?: string; is_banned?: boolean; limit?: number; offset?: number } = {}
  ): Promise<AdminPlayerListResponse> {
    const searchParams = new URLSearchParams();
    if (params.q) searchParams.append('q', params.q.trim());
    if (params.is_banned !== undefined) searchParams.append('is_banned', String(params.is_banned));
    if (params.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params.offset !== undefined) searchParams.append('offset', String(params.offset));

    const qs = searchParams.toString();
    const endpoint = `/api/v1/admin/players${qs ? `?${qs}` : ''}`;
    return apiRequest<AdminPlayerListResponse>(endpoint, {
      method: 'GET'
    }, token);
  },

  /**
   * Fetch comprehensive player details by account ID or GID.
   */
  async getPlayerDetail(
    token: string,
    playerId: number,
    lookup?: 'account' | 'gid'
  ): Promise<AdminPlayerDetail> {
    const qs = lookup ? `?lookup=${lookup}` : '';
    return apiRequest<AdminPlayerDetail>(`/api/v1/admin/players/${playerId}${qs}`, {
      method: 'GET'
    }, token);
  },

  /**
   * Suspend a player account.
   */
  async suspendPlayer(
    token: string,
    playerId: number,
    payload: SuspendPayload
  ): Promise<AdminPlayerSummary> {
    return apiRequest<AdminPlayerSummary>(`/api/v1/admin/players/${playerId}/suspend`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },

  /**
   * Reactivate a suspended player account.
   */
  async reactivatePlayer(
    token: string,
    playerId: number,
    payload: ReactivatePayload
  ): Promise<AdminPlayerSummary> {
    return apiRequest<AdminPlayerSummary>(`/api/v1/admin/players/${playerId}/reactivate`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },

  /**
   * Grant diamonds to a player's character.
   */
  async grantDiamonds(
    token: string,
    playerId: number,
    payload: DiamondMutationPayload
  ): Promise<any> {
    return apiRequest(`/api/v1/admin/players/${playerId}/diamonds/grant`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },

  /**
   * Deduct diamonds from a player's character.
   */
  async deductDiamonds(
    token: string,
    playerId: number,
    payload: DiamondMutationPayload
  ): Promise<any> {
    return apiRequest(`/api/v1/admin/players/${playerId}/diamonds/deduct`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },

  /**
   * Retrieve player diamond history.
   */
  async getDiamondHistory(
    token: string,
    playerId: number,
    limit: number = 50,
    offset: number = 0
  ): Promise<any> {
    return apiRequest(`/api/v1/admin/players/${playerId}/diamonds/history?limit=${limit}&offset=${offset}`, {
      method: 'GET'
    }, token);
  },

  /**
   * List catalog items for inventory granting.
   */
  async listCatalogItems(
    token: string,
    params: { item_type?: string; is_active?: boolean; limit?: number; offset?: number } = {}
  ): Promise<CatalogItem[]> {
    const searchParams = new URLSearchParams();
    if (params.item_type) searchParams.append('item_type', params.item_type);
    if (params.is_active !== undefined) searchParams.append('is_active', String(params.is_active));
    if (params.limit) searchParams.append('limit', String(params.limit));
    if (params.offset) searchParams.append('offset', String(params.offset));

    const qs = searchParams.toString();
    const endpoint = `/api/v1/admin/items${qs ? `?${qs}` : ''}`;
    return apiRequest<CatalogItem[]>(endpoint, {
      method: 'GET'
    }, token);
  },

  /**
   * Grant an item to a player's character.
   */
  async grantInventory(
    token: string,
    playerId: number,
    payload: InventoryGrantPayload
  ): Promise<any> {
    return apiRequest(`/api/v1/admin/players/${playerId}/inventory/grant`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },

  /**
   * Remove an item from a player's character.
   */
  async removeInventory(
    token: string,
    playerId: number,
    payload: InventoryRemovePayload
  ): Promise<any> {
    return apiRequest(`/api/v1/admin/players/${playerId}/inventory/remove`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }, token);
  },

  /**
   * Retrieve administrative audit logs.
   */
  async listAuditLogs(
    token: string,
    params: { admin_id?: number; target_id?: number; action_type?: string; limit?: number; offset?: number } = {}
  ): Promise<AdminAuditLogListResponse> {
    const searchParams = new URLSearchParams();
    if (params.admin_id !== undefined) searchParams.append('admin_id', String(params.admin_id));
    if (params.target_id !== undefined) searchParams.append('target_id', String(params.target_id));
    if (params.action_type) searchParams.append('action_type', params.action_type);
    if (params.limit !== undefined) searchParams.append('limit', String(params.limit));
    if (params.offset !== undefined) searchParams.append('offset', String(params.offset));

    const qs = searchParams.toString();
    const endpoint = `/api/v1/admin/audit-logs${qs ? `?${qs}` : ''}`;
    return apiRequest<AdminAuditLogListResponse>(endpoint, {
      method: 'GET'
    }, token);
  }
};
