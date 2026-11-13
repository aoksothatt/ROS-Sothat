import { apiRequest, ApiError } from '@/services/api';
import type {
  CharacterProfile,
  CharacterInventoryResponse,
  DiamondHistoryResponse
} from '@/types/dashboard';

export const playerService = {
  /**
   * Retrieve the authenticated player's character profile.
   * Returns null if no character has been created yet (HTTP 404).
   */
  async getMyCharacter(token: string): Promise<CharacterProfile | null> {
    try {
      return await apiRequest<CharacterProfile>('/api/v1/player/character', {
        method: 'GET'
      }, token);
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 404) {
        return null;
      }
      throw err;
    }
  },

  /**
   * Provision a new character profile for an account that does not have one yet.
   */
  async createCharacter(
    token: string,
    nickname: string,
    charType: number = 0
  ): Promise<CharacterProfile> {
    return apiRequest<CharacterProfile>('/api/v1/player/character', {
      method: 'POST',
      body: JSON.stringify({
        nickname: nickname.trim(),
        char_type: charType
      })
    }, token);
  },

  /**
   * Retrieve the authenticated player's own inventory items.
   */
  async getMyInventory(
    token: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<CharacterInventoryResponse> {
    return apiRequest<CharacterInventoryResponse>(
      `/api/v1/player/character/inventory?limit=${limit}&offset=${offset}`,
      { method: 'GET' },
      token
    );
  },

  /**
   * Retrieve the authenticated player's own diamond transaction ledger history.
   */
  async getMyDiamondHistory(
    token: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<DiamondHistoryResponse> {
    return apiRequest<DiamondHistoryResponse>(
      `/api/v1/player/character/diamonds/history?limit=${limit}&offset=${offset}`,
      { method: 'GET' },
      token
    );
  }
};
