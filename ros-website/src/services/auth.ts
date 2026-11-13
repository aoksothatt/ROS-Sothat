import { apiRequest } from '@/services/api';
import type {
  OTPRequestPayload,
  OTPResponseData,
  OTPVerifyPayload,
  TokenResponseData,
  AccountProfile
} from '@/types/auth';

export const authService = {
  /**
   * Request a 6-digit email verification code for registration or login.
   */
  async requestOTP(payload: OTPRequestPayload): Promise<OTPResponseData> {
    return apiRequest<OTPResponseData>('/api/v1/account/otp/request', {
      method: 'POST',
      body: JSON.stringify({
        email: payload.email.trim().toLowerCase(),
        purpose: payload.purpose
      })
    });
  },

  /**
   * Verify the 6-digit code and authenticate / register.
   */
  async verifyOTP(payload: OTPVerifyPayload): Promise<TokenResponseData> {
    const body: Record<string, any> = {
      email: payload.email.trim().toLowerCase(),
      code: payload.code.trim(),
      purpose: payload.purpose
    };

    if (payload.username && payload.username.trim()) {
      body.username = payload.username.trim();
    }

    return apiRequest<TokenResponseData>('/api/v1/account/otp/verify', {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  /**
   * Retrieve current authenticated account profile.
   */
  async getProfile(token: string): Promise<AccountProfile> {
    return apiRequest<AccountProfile>('/api/v1/account/me', {
      method: 'GET'
    }, token);
  }
};
