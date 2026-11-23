//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: auth_client.m
//
// Purpose: Native Objective-C iOS Login Bridge using RSA-1024 PKCS#1 v1.5 Encrypted
//          BigWorld Mercury wire protocol over native POSIX BSD sockets (UDP & TCP).
//

#import "auth_client.h"
#import "session_manager.h"
#import "logging_manager.h"
#import <Security/Security.h>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <string.h>
#include <sys/select.h>
#include <sys/time.h>

#define BW_LOGIN_REPLY_MIN_SUCCESS_LEN 21
#define BW_LOGIN_MAX_RECV_BUF 4096
#define RSA_1024_MAX_PLAINTEXT_LEN 117
#define RSA_1024_CIPHERTEXT_LEN 128
#define BW_ENCRYPTED_PACKET_LEN 129

// Matched 1024-bit RSA Public Key PKCS#1 DER (Bit-for-bit verified with loginapp_privkey.json)
static const unsigned char kLoginAppPublicKeyPKCS1[140] = {
    0x30, 0x81, 0x89, 0x02, 0x81, 0x81, 0x00, 0xca, 0xca, 0x39, 0xf8, 0xc2, 0xa2, 0x6f, 0x38, 0xe5,
    0xbd, 0xee, 0x04, 0x28, 0x83, 0x73, 0x81, 0x04, 0x83, 0x4d, 0xbb, 0x6a, 0x98, 0x53, 0x71, 0x85,
    0x7a, 0xab, 0xd8, 0xe0, 0xa2, 0xe9, 0xaf, 0x26, 0xf4, 0x8b, 0x91, 0x44, 0x47, 0x26, 0xcd, 0xdb,
    0xf2, 0x40, 0x5c, 0x0b, 0x2b, 0x84, 0x50, 0x3d, 0x1a, 0x0f, 0x30, 0x79, 0x9a, 0x0f, 0xbf, 0x2b,
    0xcc, 0xb0, 0x66, 0xc2, 0xc5, 0x6b, 0xc9, 0x02, 0x2f, 0x66, 0x72, 0x1a, 0x1c, 0x21, 0x0e, 0xac,
    0x3e, 0xbc, 0xe9, 0x9c, 0x60, 0xf4, 0x8f, 0x6a, 0x10, 0x9c, 0x7d, 0xda, 0xad, 0x2a, 0xe3, 0xe2,
    0x5a, 0x36, 0x45, 0xda, 0x07, 0x0e, 0x41, 0x4e, 0x6b, 0x7e, 0xcb, 0xb4, 0xff, 0x2d, 0x79, 0xcc,
    0xf2, 0x94, 0xc8, 0x46, 0x39, 0x62, 0xa5, 0xa0, 0x0b, 0x0e, 0xba, 0xb5, 0xe2, 0xf7, 0x31, 0xa9,
    0xf1, 0x1f, 0x83, 0x71, 0x88, 0x39, 0xf7, 0x02, 0x03, 0x01, 0x00, 0x01
};

static SecKeyRef get_loginapp_public_key(void) {
    static SecKeyRef s_keyRef = NULL;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        NSData *keyData = [NSData dataWithBytes:kLoginAppPublicKeyPKCS1 length:sizeof(kLoginAppPublicKeyPKCS1)];
        NSDictionary *attrs = @{
            (__bridge id)kSecAttrKeyType: (__bridge id)kSecAttrKeyTypeRSA,
            (__bridge id)kSecAttrKeyClass: (__bridge id)kSecAttrKeyClassPublic,
            (__bridge id)kSecAttrKeySizeInBits: @(1024)
        };
        CFErrorRef error = NULL;
        s_keyRef = SecKeyCreateWithData((__bridge CFDataRef)keyData, (__bridge CFDictionaryRef)attrs, &error);
        if (error) {
            [ROSSothatLogger logError:@"[NativeAuthBridge] SecKeyCreateWithData error: %@", (__bridge NSError *)error];
            CFRelease(error);
        }
    });
    return s_keyRef;
}

static NSData *pack_bw_string(NSString *str) {
    if (!str) return [NSData dataWithBytes:"\0" length:1];
    NSData *utf8 = [str dataUsingEncoding:NSUTF8StringEncoding];
    if (!utf8) utf8 = [NSData data];
    NSUInteger len = [utf8 length];
    NSMutableData *packed = [NSMutableData data];
    if (len < 255) {
        uint8_t l8 = (uint8_t)len;
        [packed appendBytes:&l8 length:1];
    } else {
        uint8_t marker = 255;
        uint16_t l16 = (uint16_t)len;
        [packed appendBytes:&marker length:1];
        [packed appendBytes:&l16 length:2]; // little-endian
    }
    [packed appendData:utf8];
    return packed;
}

static NSMutableData *build_logon_params_clear(NSString *username, NSString *password) {
    NSMutableData *payload = [NSMutableData data];
    [payload appendData:pack_bw_string(username)];
    [payload appendData:pack_bw_string(password)];
    // encryption_key length prefix (0 bytes clearstream session key mode)
    uint8_t zeroKey = 0;
    [payload appendBytes:&zeroKey length:1];
    return payload;
}

static NSData *encrypt_logon_params(NSData *clearPayload) {
    if (!clearPayload || [clearPayload length] == 0) {
        return nil;
    }
    if ([clearPayload length] > RSA_1024_MAX_PLAINTEXT_LEN) {
        [ROSSothatLogger logError:@"[NativeAuthBridge] Payload exceeds RSA-1024 PKCS#1 maximum (%lu > %d)",
         (unsigned long)[clearPayload length], RSA_1024_MAX_PLAINTEXT_LEN];
        return nil;
    }

    SecKeyRef keyRef = get_loginapp_public_key();
    if (!keyRef) {
        [ROSSothatLogger logError:@"[NativeAuthBridge] SecKeyRef is NULL — cannot encrypt credentials"];
        return nil;
    }

    CFErrorRef error = NULL;
    CFDataRef cipherData = SecKeyCreateEncryptedData(keyRef, kSecKeyAlgorithmRSAEncryptionPKCS1, (__bridge CFDataRef)clearPayload, &error);
    if (!cipherData || error) {
        if (error) {
            [ROSSothatLogger logError:@"[NativeAuthBridge] SecKeyCreateEncryptedData failed: %@", (__bridge NSError *)error];
            CFRelease(error);
        }
        return nil;
    }

    NSData *cipher = (__bridge_transfer NSData *)cipherData;
    if ([cipher length] != RSA_1024_CIPHERTEXT_LEN) {
        [ROSSothatLogger logError:@"[NativeAuthBridge] Unexpected RSA ciphertext length (%lu != %d)",
         (unsigned long)[cipher length], RSA_1024_CIPHERTEXT_LEN];
        return nil;
    }

    // BigWorld wire framing: 128 < 255 -> single byte length prefix 0x80 (128 in decimal)
    NSMutableData *wirePacket = [NSMutableData dataWithCapacity:BW_ENCRYPTED_PACKET_LEN];
    uint8_t lenPrefix = (uint8_t)[cipher length]; // 0x80
    [wirePacket appendBytes:&lenPrefix length:1];
    [wirePacket appendData:cipher];

    return wirePacket;
}

@implementation ROSSothatAuthClient

- (instancetype)initWithConfig:(ROSSothatConfig *)config {
    self = [super init];
    if (self) {
        _config = config ?: [ROSSothatConfig defaultConfig];
    }
    return self;
}

- (void)loginWithUsername:(NSString *)username
                 password:(NSString *)password
               completion:(ROSSothatAuthCompletion)completion {
    if (!username || [username length] == 0 || !password || [password length] == 0) {
        if (completion) completion(NO, 0, @"Username and password must not be empty.");
        return;
    }

    NSString *host = self.config.serverHost;
    NSInteger port = self.config.loginPort > 0 ? self.config.loginPort : 20013;

    [ROSSothatLogger logInfo:@"[NativeAuthBridge] Dispatching RSA-1024 encrypted login for '%@' to %s:%ld",
     username, [host UTF8String], (long)port];

    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        // 1. Build and validate cleartext credential buffer
        NSMutableData *clearPayload = build_logon_params_clear(username, password);
        if ([clearPayload length] > RSA_1024_MAX_PLAINTEXT_LEN) {
            memset(clearPayload.mutableBytes, 0, clearPayload.length);
            [ROSSothatLogger logError:@"[NativeAuthBridge] Username and password exceed maximum encrypted block size"];
            if (completion) completion(NO, 0, @"Username or password is too long for encrypted authentication.");
            return;
        }

        // 2. Encrypt credentials using verified RSA-1024 PKCS#1 v1.5 public key
        NSData *encryptedWirePacket = encrypt_logon_params(clearPayload);

        // Immediately scrub cleartext credentials from memory
        memset(clearPayload.mutableBytes, 0, clearPayload.length);

        // Strict security assertion: Never send plaintext if encryption fails
        if (!encryptedWirePacket || [encryptedWirePacket length] != BW_ENCRYPTED_PACKET_LEN) {
            [ROSSothatLogger logError:@"[NativeAuthBridge] Encryption failed. Aborting login without sending plaintext."];
            if (completion) completion(NO, 0, @"Client encryption error: unable to securely encrypt credentials.");
            return;
        }

        const void *wireBytes = [encryptedWirePacket bytes];
        size_t wireLen = [encryptedWirePacket length];

        uint8_t recvBuf[BW_LOGIN_MAX_RECV_BUF];
        ssize_t receivedBytes = -1;
        BOOL receivedFromUdp = NO;

        // ---------------------------------------------------------------------
        // Phase 1: Native POSIX UDP Encrypted Datagram (Port 20013)
        // ---------------------------------------------------------------------
        int udpSock = socket(AF_INET, SOCK_DGRAM, 0);
        if (udpSock >= 0) {
            struct sockaddr_in saddr;
            memset(&saddr, 0, sizeof(saddr));
            saddr.sin_family = AF_INET;
            saddr.sin_port = htons((uint16_t)port);
            saddr.sin_addr.s_addr = inet_addr([host UTF8String]);

            for (int attempt = 1; attempt <= 3; ++attempt) {
                [ROSSothatLogger logInfo:@"[NativeAuthBridge] UDP attempt %d/3 sending encrypted datagram (%lu bytes) to %s:%ld",
                 attempt, (unsigned long)wireLen, [host UTF8String], (long)port];

                ssize_t sent = sendto(udpSock, wireBytes, wireLen, 0, (struct sockaddr *)&saddr, sizeof(saddr));
                if (sent < 0) {
                    [ROSSothatLogger logWarning:@"[NativeAuthBridge] UDP sendto failed (errno: %d: %s)", errno, strerror(errno)];
                    continue;
                }

                fd_set readFds;
                FD_ZERO(&readFds);
                FD_SET(udpSock, &readFds);

                struct timeval tv;
                tv.tv_sec = 2;
                tv.tv_usec = 0;

                int selRes = select(udpSock + 1, &readFds, NULL, NULL, &tv);
                if (selRes > 0 && FD_ISSET(udpSock, &readFds)) {
                    socklen_t slen = sizeof(saddr);
                    ssize_t n = recvfrom(udpSock, recvBuf, sizeof(recvBuf), 0, (struct sockaddr *)&saddr, &slen);
                    if (n > 0) {
                        receivedBytes = n;
                        receivedFromUdp = YES;
                        [ROSSothatLogger logInfo:@"[NativeAuthBridge] UDP received %ld bytes reply from server", (long)n];
                        break;
                    }
                }
            }
            close(udpSock);
        }

        // ---------------------------------------------------------------------
        // Phase 2: Dual-Stack TCP Stream Fallback (Port 20013)
        // ---------------------------------------------------------------------
        if (!receivedFromUdp) {
            [ROSSothatLogger logInfo:@"[NativeAuthBridge] UDP did not receive reply; attempting encrypted TCP fallback on %s:%ld",
             [host UTF8String], (long)port];

            int tcpSock = socket(AF_INET, SOCK_STREAM, 0);
            if (tcpSock >= 0) {
                int flags = fcntl(tcpSock, F_GETFL, 0);
                fcntl(tcpSock, F_SETFL, flags | O_NONBLOCK);

                struct sockaddr_in saddr;
                memset(&saddr, 0, sizeof(saddr));
                saddr.sin_family = AF_INET;
                saddr.sin_port = htons((uint16_t)port);
                saddr.sin_addr.s_addr = inet_addr([host UTF8String]);

                int connRes = connect(tcpSock, (struct sockaddr *)&saddr, sizeof(saddr));
                BOOL connected = NO;
                if (connRes == 0) {
                    connected = YES;
                } else if (errno == EINPROGRESS) {
                    fd_set writeFds;
                    FD_ZERO(&writeFds);
                    FD_SET(tcpSock, &writeFds);
                    struct timeval tv = {3, 0};
                    if (select(tcpSock + 1, NULL, &writeFds, NULL, &tv) > 0) {
                        int sockErr = 0;
                        socklen_t errLen = sizeof(sockErr);
                        getsockopt(tcpSock, SOL_SOCKET, SO_ERROR, &sockErr, &errLen);
                        if (sockErr == 0) {
                            connected = YES;
                        }
                    }
                }

                if (connected) {
                    fcntl(tcpSock, F_SETFL, flags);
                    struct timeval tv = {5, 0};
                    setsockopt(tcpSock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
                    setsockopt(tcpSock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

                    // Send 2-byte big-endian wire length + encrypted payload
                    uint16_t wireLenNet = htons((uint16_t)wireLen);
                    write(tcpSock, &wireLenNet, 2);
                    write(tcpSock, wireBytes, wireLen);

                    // Read 2-byte reply length prefix
                    uint16_t replyLenNet = 0;
                    ssize_t hBytes = read(tcpSock, &replyLenNet, 2);
                    if (hBytes == 2) {
                        uint16_t replyLen = ntohs(replyLenNet);
                        if (replyLen > 0 && replyLen <= sizeof(recvBuf)) {
                            ssize_t totalRead = 0;
                            while (totalRead < replyLen) {
                                ssize_t r = read(tcpSock, recvBuf + totalRead, replyLen - totalRead);
                                if (r <= 0) break;
                                totalRead += r;
                            }
                            if (totalRead == replyLen) {
                                receivedBytes = totalRead;
                                [ROSSothatLogger logInfo:@"[NativeAuthBridge] TCP received %ld bytes reply from server", (long)totalRead];
                            }
                        }
                    }
                }
                close(tcpSock);
            }
        }

        // ---------------------------------------------------------------------
        // Phase 3: Response Decoding (BigWorld LoginReply Specification)
        // ---------------------------------------------------------------------
        if (receivedBytes < 1) {
            NSString *err = [NSString stringWithFormat:@"Cannot reach authentication server at %@:%ld. Check server status and Wi-Fi connection.",
                             host, (long)port];
            [ROSSothatLogger logError:@"[NativeAuthBridge] Connection failed — no reply received from %s:%ld", [host UTF8String], (long)port];
            if (completion) completion(NO, 0, err);
            return;
        }

        uint8_t status = recvBuf[0];

        if (status == 0) {
            // STATUS_LOGGED_ON (Success: exactly 21 bytes)
            if (receivedBytes < BW_LOGIN_REPLY_MIN_SUCCESS_LEN) {
                [ROSSothatLogger logError:@"[NativeAuthBridge] Malformed success reply: length %ld < 21", (long)receivedBytes];
                if (completion) completion(NO, 0, @"Malformed authentication reply from server.");
                return;
            }

            // Bytes 17..20: 32-bit unsigned session_key (little-endian)
            uint32_t sessionKey = 0;
            memcpy(&sessionKey, &recvBuf[17], sizeof(uint32_t));

            // Atomically store session key into hook memory for BaseApp handshake stamping
            rossothat_set_session_key(sessionKey);

            [ROSSothatLogger logInfo:@"[NativeAuthBridge] Auth SUCCESS for user '%@' — sessionKey: 0x%08X",
             username, sessionKey];

            if (completion) completion(YES, sessionKey, nil);
        } else {
            // Failure reply with BigWorld length-prefixed string
            NSString *serverErrMsg = nil;
            if (receivedBytes >= 2) {
                uint8_t sLen = recvBuf[1];
                size_t off = 2;
                if (sLen == 255 && receivedBytes >= 4) {
                    uint16_t extLen = 0;
                    memcpy(&extLen, &recvBuf[2], 2);
                    sLen = extLen;
                    off = 4;
                }
                if (off + sLen <= (size_t)receivedBytes) {
                    serverErrMsg = [[NSString alloc] initWithBytes:&recvBuf[off] length:sLen encoding:NSUTF8StringEncoding];
                }
            }

            NSString *displayErr = serverErrMsg;
            if (!displayErr || [displayErr length] == 0) {
                switch (status) {
                    case 1: displayErr = @"Account does not exist."; break;
                    case 2: displayErr = @"Invalid username or password."; break;
                    case 3: displayErr = @"Account is already logged in elsewhere."; break;
                    case 4: displayErr = @"Malformed authentication packet."; break;
                    case 5: displayErr = @"Internal server database error."; break;
                    case 6: displayErr = @"Account has been suspended or banned."; break;
                    case 7: displayErr = @"Login rate limit exceeded. Please wait a minute."; break;
                    default: displayErr = [NSString stringWithFormat:@"Login rejected by server (code %u).", status]; break;
                }
            }

            [ROSSothatLogger logWarning:@"[NativeAuthBridge] Auth rejected for user '%@' (status %u): %@",
             username, status, displayErr];

            if (completion) completion(NO, 0, displayErr);
        }
    });
}

@end
