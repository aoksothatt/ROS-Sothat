export type OTPPurpose = 'registration' | 'login';

export interface OTPRequestPayload {
  email: string;
  purpose: OTPPurpose;
}

export interface OTPResponseData {
  status: string;
  message: string;
  cooldown_seconds: number;
  masked_email: string;
}

export interface OTPVerifyPayload {
  email: string;
  code: string;
  purpose: OTPPurpose;
  username?: string;
}

export interface TokenResponseData {
  access_token: string;
  token_type: string;
  account_id: number;
  username: string;
}

export interface AccountProfile {
  id: number;
  username: string;
  email: string | null;
  role: string;
  is_banned: boolean;
  created_at: string;
  last_login: string | null;
  has_character: boolean;
}

export interface ApiErrorResponse {
  detail?: string | Array<{ msg: string; loc?: string[] }>;
}
