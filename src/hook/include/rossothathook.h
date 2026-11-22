//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: rossothathook.h
//
// Purpose: Primary entry point, lifecycle coordinator, and dynamic library exports
// for the side-by-side ROS Sothatt client integration (net.roslegacy.sothatt).
//

#ifndef ROSSOTHATHOOK_H
#define ROSSOTHATHOOK_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Version metadata
#define ROSSOTHAT_HOOK_VERSION_MAJOR 1
#define ROSSOTHAT_HOOK_VERSION_MINOR 0
#define ROSSOTHAT_HOOK_VERSION_PATCH 0
#define ROSSOTHAT_HOOK_VERSION_STRING "1.0.0"

// Standardized ports
#define ROSSOTHAT_DEFAULT_AUTH_PORT      20080
#define ROSSOTHAT_DEFAULT_DISCOVERY_PORT 50010
#define ROSSOTHAT_DEFAULT_BASEAPP_PORT   20014
#define ROSSOTHAT_DEFAULT_CELLAPP_PORT   20002

// Dynamic library exported symbols (ABI compatibility with client dyld loader)
__attribute__((visibility("default"))) void ros_apply_ticket(void);
__attribute__((visibility("default"))) void ros_set_ticket(void);

// Internal lifecycle control
void rossothat_hook_initialize(void);
void rossothat_hook_shutdown(void);

#ifdef __cplusplus
}
#endif

#endif // ROSSOTHATHOOK_H
