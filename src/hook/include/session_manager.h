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

#ifdef __cplusplus
}
#endif

#endif // ROSSOTHAT_SESSION_MANAGER_H
