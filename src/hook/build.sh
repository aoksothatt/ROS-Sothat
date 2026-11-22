#!/usr/bin/env bash
# ROS Sothatt — Clean-Room iOS Hook Build Script
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "=========================================================="
echo " Building Clean-Room ROS Sothatt iOS Dynamic Library"
echo " Target: rosauthhook.dylib (ARM64 iOS 12.0+)"
echo "=========================================================="

if command -v xcrun &>/dev/null; then
    xcrun -sdk iphoneos clang \
        -arch arm64 \
        -miphoneos-version-min=16.0 \
        -O2 \
        -fobjc-arc \
        -Wall \
        -Wextra \
        -I./include \
        -fvisibility=hidden \
        -shared \
        -install_name @executable_path/rosauthhook.dylib \
        -framework Foundation \
        -framework UIKit \
        -framework Security \
        -framework CoreGraphics \
        -framework QuartzCore \
        -lobjc \
        -o rosauthhook.dylib \
        src/rossothathook.m \
        src/config_manager.m \
        src/network_client.m \
        src/auth_client.m \
        src/session_manager.c \
        src/discovery_client.m \
        src/baseapp_hook.c \
        src/logging_manager.m \
        src/error_handler.m \
        src/fishhook.c \
        src/SothattLoginVC.m

    echo "[+] Build succeeded: rosauthhook.dylib"
    file rosauthhook.dylib
else
    echo "[!] xcrun not detected on this host. Use cross-compiler or compile on macOS runner."
fi
