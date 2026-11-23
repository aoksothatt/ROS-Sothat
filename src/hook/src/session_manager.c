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

#define CREDENTIAL_MAX_LEN 128
static char s_active_username[CREDENTIAL_MAX_LEN] = {0};
static char s_active_password[CREDENTIAL_MAX_LEN] = {0};
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)
static _Atomic int s_login_state = ROSSOTHAT_LOGIN_STATE_IDLE;
#else
static volatile int s_login_state = ROSSOTHAT_LOGIN_STATE_IDLE;
#endif

void rossothat_set_active_credentials(const char *username, const char *password) {
    rossothat_clear_active_credentials();
    if (username) {
        strncpy(s_active_username, username, CREDENTIAL_MAX_LEN - 1);
        s_active_username[CREDENTIAL_MAX_LEN - 1] = '\0';
    }
    if (password) {
        strncpy(s_active_password, password, CREDENTIAL_MAX_LEN - 1);
        s_active_password[CREDENTIAL_MAX_LEN - 1] = '\0';
    }
}

void rossothat_get_active_username(char *out_username, size_t max_len) {
    if (!out_username || max_len == 0) return;
    strncpy(out_username, s_active_username, max_len - 1);
    out_username[max_len - 1] = '\0';
}

void rossothat_get_active_password(char *out_password, size_t max_len) {
    if (!out_password || max_len == 0) return;
    strncpy(out_password, s_active_password, max_len - 1);
    out_password[max_len - 1] = '\0';
}

void rossothat_clear_active_credentials(void) {
    volatile char *p = s_active_password;
    for (size_t i = 0; i < CREDENTIAL_MAX_LEN; ++i) {
        p[i] = 0;
    }
    memset(s_active_username, 0, CREDENTIAL_MAX_LEN);
}

void rossothat_set_login_state(int state) {
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)
    atomic_store_explicit(&s_login_state, state, memory_order_release);
#else
    s_login_state = state;
#endif
}

int rossothat_get_login_state(void) {
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L && !defined(__STDC_NO_ATOMICS__)
    return atomic_load_explicit(&s_login_state, memory_order_acquire);
#else
    return s_login_state;
#endif
}

#define TICKET_MAX_LEN 128
static char s_active_ticket[TICKET_MAX_LEN] = {0};

void rossothat_set_active_ticket(const char *ticket) {
    rossothat_clear_active_ticket();
    if (ticket) {
        strncpy(s_active_ticket, ticket, TICKET_MAX_LEN - 1);
        s_active_ticket[TICKET_MAX_LEN - 1] = '\0';
    }
}

void rossothat_get_active_ticket(char *out_ticket, size_t max_len) {
    if (!out_ticket || max_len == 0) return;
    strncpy(out_ticket, s_active_ticket, max_len - 1);
    out_ticket[max_len - 1] = '\0';
}

void rossothat_clear_active_ticket(void) {
    volatile char *p = s_active_ticket;
    for (size_t i = 0; i < TICKET_MAX_LEN; ++i) {
        p[i] = 0;
    }
}
