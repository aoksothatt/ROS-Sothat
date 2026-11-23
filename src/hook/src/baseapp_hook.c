//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: baseapp_hook.c
//
// Purpose: POSIX UDP socket interposition and 24-byte BaseApp handshake stamping at Byte Offset 11.
//

#include "baseapp_hook.h"
#include "session_manager.h"
#include "fishhook.h"
#include <string.h>
#include <netinet/in.h>
#include <arpa/inet.h>

// Original system function pointers
static ssize_t (*orig_sendto)(int, const void *, size_t, int, const struct sockaddr *, socklen_t) = NULL;
static ssize_t (*orig_recvfrom)(int, void *, size_t, int, struct sockaddr *, socklen_t *) = NULL;
static int (*orig_connect)(int, const struct sockaddr *, socklen_t) = NULL;

static uint16_t s_target_baseapp_port = 20014;
static uint32_t s_target_disc_ip = 0;      // 172.65.54.209
static uint32_t s_redirect_disc_ip = 0;    // redirected host IP
static uint16_t s_redirect_disc_port = 0;  // redirected https port

bool rossothat_is_baseapp_login_packet(const uint8_t *buffer, size_t length) {
    if (!buffer || length < BASEAPP_DATAGRAM_LEN) {
        return false;
    }

    // Byte 0: Mercury Flag HAS_REQUESTS (0x01)
    if (buffer[0] != MERCURY_FLAG_HAS_REQUESTS) {
        return false;
    }
    // Byte 3: BaseAppExtInterface::baseAppLogin = 11 (0x0B)
    if (buffer[3] != MSG_BASEAPP_LOGIN_LEGACY) {
        return false;
    }
    // Byte 19: Sub-message length = 20 (0x14)
    if (buffer[19] != 0x14) {
        return false;
    }
    // Byte 22: Sub-interface version = 2 (0x02)
    if (buffer[22] != 0x02) {
        return false;
    }

    return true;
}

bool rossothat_stamp_baseapp_handshake(uint8_t *buffer, size_t length, uint32_t session_key) {
    if (!buffer || length < BASEAPP_DATAGRAM_LEN) {
        return false;
    }

    // Stamped 32-bit sessionKey at verified BYTE OFFSET 11 (little-endian)
    buffer[BASEAPP_SESSION_KEY_OFFSET + 0] = (uint8_t)(session_key & 0xFF);
    buffer[BASEAPP_SESSION_KEY_OFFSET + 1] = (uint8_t)((session_key >> 8) & 0xFF);
    buffer[BASEAPP_SESSION_KEY_OFFSET + 2] = (uint8_t)((session_key >> 16) & 0xFF);
    buffer[BASEAPP_SESSION_KEY_OFFSET + 3] = (uint8_t)((session_key >> 24) & 0xFF);

    return true;
}

static ssize_t sothat_hook_sendto(int socket,
                                  const void *buffer,
                                  size_t length,
                                  int flags,
                                  const struct sockaddr *dest_addr,
                                  socklen_t dest_len) {
    if (buffer && length >= BASEAPP_DATAGRAM_LEN && dest_addr) {
        uint16_t dest_port = 0;
        if (dest_addr->sa_family == AF_INET) {
            const struct sockaddr_in *sin = (const struct sockaddr_in *)dest_addr;
            dest_port = ntohs(sin->sin_port);
        }

        // Check if destination port matches configured BaseApp port
        if (dest_port == s_target_baseapp_port || s_target_baseapp_port == 0) {
            if (rossothat_is_baseapp_login_packet((const uint8_t *)buffer, length)) {
                uint32_t session_key = rossothat_get_session_key();
                if (session_key != 0) {
                    // Create stack copy to avoid mutating original engine buffer in-place
                    uint8_t modified_datagram[BASEAPP_DATAGRAM_LEN];
                    memcpy(modified_datagram, buffer, BASEAPP_DATAGRAM_LEN);
                    rossothat_stamp_baseapp_handshake(modified_datagram, BASEAPP_DATAGRAM_LEN, session_key);

                    return orig_sendto(socket, modified_datagram, BASEAPP_DATAGRAM_LEN, flags, dest_addr, dest_len);
                }
            }
        }
    }

    return orig_sendto(socket, buffer, length, flags, dest_addr, dest_len);
}

static ssize_t sothat_hook_recvfrom(int socket,
                                    void *buffer,
                                    size_t length,
                                    int flags,
                                    struct sockaddr *address,
                                    socklen_t *address_len) {
    return orig_recvfrom(socket, buffer, length, flags, address, address_len);
}

static int sothat_hook_connect(int socket, const struct sockaddr *address, socklen_t address_len) {
    if (address && address_len >= sizeof(struct sockaddr_in) && address->sa_family == AF_INET) {
        const struct sockaddr_in *sin = (const struct sockaddr_in *)address;
        if (sin->sin_port == htons(443) && sin->sin_addr.s_addr == s_target_disc_ip) {
            struct sockaddr_in sin_mod;
            memcpy(&sin_mod, sin, sizeof(struct sockaddr_in));
            sin_mod.sin_addr.s_addr = s_redirect_disc_ip;
            sin_mod.sin_port = htons(s_redirect_disc_port);
            return orig_connect(socket, (const struct sockaddr *)&sin_mod, sizeof(sin_mod));
        }
    }
    return orig_connect(socket, address, address_len);
}

int rossothat_install_socket_hooks(uint16_t target_baseapp_port) {
    s_target_baseapp_port = target_baseapp_port;

    struct rebinding rebindings[] = {
        {"sendto", sothat_hook_sendto, (void **)&orig_sendto},
        {"recvfrom", sothat_hook_recvfrom, (void **)&orig_recvfrom}
    };

    return rebind_symbols(rebindings, 2);
}

int rossothat_install_connect_hook(const char *target_host, uint16_t target_https_port) {
    s_target_disc_ip = inet_addr("172.65.54.209");
    s_redirect_disc_ip = inet_addr(target_host ? target_host : "192.168.1.7");
    s_redirect_disc_port = target_https_port ? target_https_port : 50443;

    struct rebinding rebind_connect[] = {
        {"connect", sothat_hook_connect, (void **)&orig_connect}
    };

    return rebind_symbols(rebind_connect, 1);
}

void rossothat_update_target_host(const char *target_host) {
    if (target_host && strlen(target_host) > 0) {
        s_redirect_disc_ip = inet_addr(target_host);
    }
}

void rossothat_probe_local_network(const char *target_ip) {
    if (!target_ip || strlen(target_ip) == 0) return;
    int probe_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (probe_sock >= 0) {
        struct sockaddr_in probe_addr;
        memset(&probe_addr, 0, sizeof(probe_addr));
        probe_addr.sin_family = AF_INET;
        probe_addr.sin_port = htons(20014);
        probe_addr.sin_addr.s_addr = inet_addr(target_ip);
        // Connect on UDP socket binds default destination in kernel without transmitting packets.
        // On iOS 14-16, this safely and reliably invokes the Local Network privacy evaluation (Apple TN3179).
        connect(probe_sock, (struct sockaddr *)&probe_addr, sizeof(probe_addr));
        close(probe_sock);
    }
}
