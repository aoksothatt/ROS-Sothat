//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: session_manager.c
//
// Purpose: Deterministic 32-bit FNV-1a session-key derivation and atomic memory storage.
//

#include "session_manager.h"
#include <string.h>

#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)
#include <stdatomic.h>
static _Atomic uint32_t s_session_key = 0;
#else
static volatile uint32_t s_session_key = 0;
#endif

uint32_t rossothat_fnv1a_32(const char *token) {
    if (!token) {
        return FNV1A_32_OFFSET_BASIS;
    }
    return rossothat_fnv1a_32_buf((const uint8_t *)token, strlen(token));
}

uint32_t rossothat_fnv1a_32_buf(const uint8_t *data, size_t length) {
    uint32_t hash = FNV1A_32_OFFSET_BASIS;
    if (!data) {
        return hash;
    }
    for (size_t i = 0; i < length; ++i) {
        hash ^= (uint32_t)data[i];
        hash *= FNV1A_32_PRIME;
    }
    return hash;
}

void rossothat_set_session_key(uint32_t key) {
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)
    atomic_store_explicit(&s_session_key, key, memory_order_release);
#else
    s_session_key = key;
#endif
}

uint32_t rossothat_get_session_key(void) {
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)
    return atomic_load_explicit(&s_session_key, memory_order_acquire);
#else
    return s_session_key;
#endif
}

void rossothat_clear_session_key(void) {
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)
    atomic_store_explicit(&s_session_key, 0, memory_order_release);
#else
    s_session_key = 0;
#endif
}
