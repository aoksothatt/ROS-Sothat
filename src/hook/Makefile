# ROS Sothatt — Clean-Room iOS Hook Makefile
# Target: Mach-O ARM64 Dynamic Library (rosauthhook.dylib)

CC = xcrun -sdk iphoneos clang
ARCH = arm64
MIN_IOS = 16.0
ISYSROOT = $(shell xcrun -sdk iphoneos --show-sdk-path 2>/dev/null)

COMMON_FLAGS = -arch $(ARCH) \
               -miphoneos-version-min=$(MIN_IOS) \
               -isysroot $(ISYSROOT)

CFLAGS = $(COMMON_FLAGS) \
         -O2 \
         -fobjc-arc \
         -Wall \
         -Wextra \
         -I./include \
         -fvisibility=hidden

LDFLAGS = -shared \
          -install_name @executable_path/rosauthhook.dylib \
          -framework Foundation \
          -framework UIKit \
          -framework Security \
          -framework CoreGraphics \
          -framework QuartzCore \
          -lobjc

SRCS = src/rossothathook.m \
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

TARGET = rosauthhook.dylib

all: $(TARGET)

$(TARGET): $(SRCS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^

clean:
	rm -f $(TARGET)

.PHONY: all clean
