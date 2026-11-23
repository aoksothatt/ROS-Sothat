//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: session_manager.h
//
// Purpose: Deterministic 32-bit FNV-1a session-key derivation and atomic memory storage.
//

#ifndef ROSSOTHAT_SESSION_MANAGER_H
#define ROSSOTHAT_SESSION_MANAGER_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define FNV1A_32_OFFSET_BASIS 0x811C9DC5U
#define FNV1A_32_PRIME        0x01000193U

/**
 * Computes the 32-bit FNV-1a hash over a null-terminated UTF-8 string token.
 * Matches bit-for-bit with backend legacy_mobile_auth_service.py and rosauthhook.dylib disassembly.
 */
uint32_t rossothat_fnv1a_32(const char *token);

/**
 * Computes the 32-bit FNV-1a hash over an arbitrary byte buffer.
 */
uint32_t rossothat_fnv1a_32_buf(const uint8_t *data, size_t length);

/**
 * Atomically stores the derived 32-bit sessionKey.
 */
void rossothat_set_session_key(uint32_t key);

/**
 * Atomically retrieves the active 32-bit sessionKey.
 */
uint32_t rossothat_get_session_key(void);

/**
 * Clears and zeroizes the stored sessionKey.
 */
void rossothat_clear_session_key(void);

// Stage 2: Native BigWorld Login Credentials & State Tracking
#define ROSSOTHAT_LOGIN_STATE_IDLE           0
#define ROSSOTHAT_LOGIN_STATE_AUTHENTICATING 1
#define ROSSOTHAT_LOGIN_STATE_AUTHENTICATED  2
#define ROSSOTHAT_LOGIN_STATE_FAILED         3

/**
 * Stores active credentials captured from SothattLoginVC in memory.
 */
void rossothat_set_active_credentials(const char *username, const char *password);

/**
 * Retrieves the active username (copies up to max_len - 1 characters).
 */
void rossothat_get_active_username(char *out_username, size_t max_len);

/**
 * Retrieves the active password (copies up to max_len - 1 characters).
 */
void rossothat_get_active_password(char *out_password, size_t max_len);

/**
 * Securely zeroizes and clears stored username and password from memory.
 */
void rossothat_clear_active_credentials(void);

/**
 * Updates the native login state.
 */
void rossothat_set_login_state(int state);

/**
 * Retrieves the current native login state.
 */
int rossothat_get_login_state(void);

// Stage 3: Secure Pre-Authentication Single-Use Ticket Bridge

/**
 * Stores the active pre-authentication ticket in memory.
 */
void rossothat_set_active_ticket(const char *ticket);

/**
 * Retrieves the active pre-authentication ticket (copies up to max_len - 1 characters).
 */
void rossothat_get_active_ticket(char *out_ticket, size_t max_len);

/**
 * Securely zeroizes and clears stored pre-authentication ticket from memory.
 */
void rossothat_clear_active_ticket(void);

#ifdef __cplusplus
}
#endif

#endif // ROSSOTHAT_SESSION_MANAGER_H
