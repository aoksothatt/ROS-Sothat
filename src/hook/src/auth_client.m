//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: auth_client.m
//
// Purpose: Native Objective-C iOS Login Bridge using non-HTTP Mercury wire protocol
//          (BigWorld LogOnParams / LoginReply) over native POSIX BSD sockets.
//

#import "auth_client.h"
#import "session_manager.h"
#import "logging_manager.h"

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

static NSMutableData *build_logon_params(NSString *username, NSString *password) {
    NSMutableData *payload = [NSMutableData data];
    [payload appendData:pack_bw_string(username)];
    [payload appendData:pack_bw_string(password)];
    // encryption_key length prefix (0 bytes)
    uint8_t zeroKey = 0;
    [payload appendBytes:&zeroKey length:1];
    return payload;
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

    [ROSSothatLogger logInfo:@"[NativeAuthBridge] Dispatching native BigWorld login for '%@' to %s:%ld (non-HTTP protocol)",
     username, [host UTF8String], (long)port];

    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        NSMutableData *reqPayload = build_logon_params(username, password);
        const void *reqBytes = [reqPayload bytes];
        size_t reqLen = [reqPayload length];

        uint8_t recvBuf[BW_LOGIN_MAX_RECV_BUF];
        ssize_t receivedBytes = -1;
        BOOL receivedFromUdp = NO;

        // ---------------------------------------------------------------------
        // Phase 1: Native POSIX UDP Protocol (Primary Transport on Port 20013)
        // ---------------------------------------------------------------------
        int udpSock = socket(AF_INET, SOCK_DGRAM, 0);
        if (udpSock >= 0) {
            struct sockaddr_in saddr;
            memset(&saddr, 0, sizeof(saddr));
            saddr.sin_family = AF_INET;
            saddr.sin_port = htons((uint16_t)port);
            saddr.sin_addr.s_addr = inet_addr([host UTF8String]);

            // Up to 3 attempts with 2.0s timeout per attempt
            for (int attempt = 1; attempt <= 3; ++attempt) {
                [ROSSothatLogger logInfo:@"[NativeAuthBridge] UDP attempt %d/3 sending %lu bytes to %s:%ld",
                 attempt, (unsigned long)reqLen, [host UTF8String], (long)port];

                ssize_t sent = sendto(udpSock, reqBytes, reqLen, 0, (struct sockaddr *)&saddr, sizeof(saddr));
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
        // Phase 2: Dual-Stack TCP Stream Fallback (Guaranteed Delivery)
        // ---------------------------------------------------------------------
        if (!receivedFromUdp) {
            [ROSSothatLogger logInfo:@"[NativeAuthBridge] UDP did not receive reply; attempting TCP fallback on %s:%ld",
             [host UTF8String], (long)port];

            int tcpSock = socket(AF_INET, SOCK_STREAM, 0);
            if (tcpSock >= 0) {
                // Set non-blocking for connect timeout
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
                    // Restore blocking mode with socket timeout
                    fcntl(tcpSock, F_SETFL, flags);
                    struct timeval tv = {5, 0};
                    setsockopt(tcpSock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
                    setsockopt(tcpSock, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

                    // Send 2-byte big-endian length prefix + payload
                    uint16_t wireLen = htons((uint16_t)reqLen);
                    write(tcpSock, &wireLen, 2);
                    write(tcpSock, reqBytes, reqLen);

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

        // Scrub request payload from memory
        memset(reqPayload.mutableBytes, 0, reqPayload.length);

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
