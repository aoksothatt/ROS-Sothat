import { describe, it, expect, beforeEach, vi } from 'vitest';
import { authService } from '@/services/auth';
import { ApiError } from '@/services/api';

describe('authService Unit Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Email validation & OTP request success', async () => {
    const mockResponse = {
      status: 'ok',
      message: 'If this email is valid, a verification code has been sent.',
      cooldown_seconds: 60,
      masked_email: 'p***1@ros-sothat.internal'
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockResponse
    } as any);

    const res = await authService.requestOTP({
      email: 'player1@ros-sothat.internal',
      purpose: 'registration'
    });

    expect(res.status).toBe('ok');
    expect(res.cooldown_seconds).toBe(60);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/v1/account/otp/request',
      expect.objectContaining({ method: 'POST' })
    );
  });

  it('2. OTP verification returns token data', async () => {
    const mockToken = {
      access_token: 'fake.jwt.token',
      token_type: 'bearer',
      account_id: 101,
      username: 'custom_operator'
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockToken
    } as any);

    const res = await authService.verifyOTP({
      email: 'player1@ros-sothat.internal',
      code: '123456',
      purpose: 'registration',
      username: 'custom_operator'
    });

    expect(res.access_token).toBe('fake.jwt.token');
    expect(res.username).toBe('custom_operator');
  });

  it('3. Invalid OTP error handling with attempt reporting', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ detail: 'Invalid verification code. 4 attempt(s) remaining.' })
    } as any);

    await expect(
      authService.verifyOTP({
        email: 'test@example.com',
        code: '000000',
        purpose: 'login'
      })
    ).rejects.toThrow('Invalid verification code. 4 attempt(s) remaining.');
  });

  it('4. Resend cooldown error with Retry-After header parsing', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({
        'content-type': 'application/json',
        'Retry-After': '42'
      }),
      json: async () => ({ detail: 'Please wait 42s before requesting a new verification code.' })
    } as any);

    try {
      await authService.requestOTP({
        email: 'cooldown@example.com',
        purpose: 'registration'
      });
      expect.fail('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(429);
      expect(err.retryAfter).toBe(42);
      expect(err.message).toContain('Please wait 42s');
    }
  });

  it('5. API network failure gracefully surfaced as ApiError', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    try {
      await authService.requestOTP({
        email: 'network@example.com',
        purpose: 'login'
      });
      expect.fail('Should have thrown ApiError');
    } catch (err: any) {
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(0);
      expect(err.message).toContain('Unable to connect to ROS Sothat server');
    }
  });

  it('6. Get profile retrieves authenticated account data', async () => {
    const mockProfile = {
      id: 101,
      username: 'sniper_elite',
      email: 'player@example.com',
      role: 'player',
      is_banned: false,
      created_at: '2026-11-13T12:00:00',
      last_login: '2026-11-13T13:00:00',
      has_character: true
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => mockProfile
    } as any);

    const profile = await authService.getProfile('test.jwt.token');
    expect(profile.username).toBe('sniper_elite');
    expect(profile.role).toBe('player');
    expect(profile.has_character).toBe(true);
  });
});
