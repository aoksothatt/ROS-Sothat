//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: baseapp_hook.h
//
// Purpose: POSIX UDP socket interposition and 24-byte BaseApp handshake stamping at Byte Offset 11.
//

#ifndef ROSSOTHAT_BASEAPP_HOOK_H
#define ROSSOTHAT_BASEAPP_HOOK_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <sys/socket.h>

#ifdef __cplusplus
extern "C" {
#endif

// Verified Protocol Constants
#define MERCURY_FLAG_HAS_REQUESTS 0x01
#define MSG_BASEAPP_LOGIN_LEGACY  0x0B
#define BASEAPP_DATAGRAM_LEN      24
#define BASEAPP_SESSION_KEY_OFFSET 11

/**
 * Validates whether an outgoing UDP datagram buffer matches the genuine ROS Legacy 24-byte login signature.
 */
bool rossothat_is_baseapp_login_packet(const uint8_t *buffer, size_t length);

/**
 * Injects the derived 32-bit sessionKey at verified Byte Offset 11 in a 24-byte datagram buffer.
 * Returns true if stamping succeeded.
 */
bool rossothat_stamp_baseapp_handshake(uint8_t *buffer, size_t length, uint32_t session_key);

/**
 * Installs POSIX sendto and recvfrom hooks via fishhook.
 */
int rossothat_install_socket_hooks(uint16_t target_baseapp_port);

/**
 * Installs POSIX connect hook via fishhook to redirect discovery (172.65.54.209:443)
 * to the private ROS Sothatt HTTPS discovery listener.
 */
int rossothat_install_connect_hook(const char *target_host, uint16_t target_https_port);

/**
 * Dynamically updates the redirected discovery HTTPS host IP without re-hooking symbols.
 */
void rossothat_update_target_host(const char *target_host);

/**
 * Proactively triggers the iOS Local Network privacy evaluation via a non-blocking
 * UDP connect probe as recommended in Apple Technical Note TN3179.
 */
void rossothat_probe_local_network(const char *target_ip);

#ifdef __cplusplus
}
#endif

#endif // ROSSOTHAT_BASEAPP_HOOK_H
