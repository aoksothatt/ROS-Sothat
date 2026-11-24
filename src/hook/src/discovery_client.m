//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: discovery_client.m
//
// Purpose: Server discovery parser extracting BaseApp UDP endpoint from authentic 10-token response.
//

#import "discovery_client.h"
#import "network_client.h"
#import "logging_manager.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

@implementation ROSSothatServerEntry

+ (nullable instancetype)parseLegacyLine:(NSString *)line {
    NSString *trimmed = [line stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
    if ([trimmed length] == 0 || [trimmed hasPrefix:@"#"]) {
        return nil;
    }

    NSArray<NSString *> *tokens = [trimmed componentsSeparatedByString:@" "];
    if ([tokens count] != 10) {
        return nil;
    }

    ROSSothatServerEntry *entry = [[ROSSothatServerEntry alloc] init];
    entry->_zone = tokens[0];
    entry->_numberSt = [tokens[1] integerValue];
    entry->_netSt = [tokens[2] integerValue];
    entry->_serverSt = [tokens[3] integerValue];
    entry->_name = tokens[4];
    entry->_oriName = tokens[5];

    NSString *telEp = tokens[6];
    NSArray *parts = [telEp componentsSeparatedByString:@":"];
    if ([parts count] == 2) {
        entry->_telHost = parts[0];
        entry->_telPort = [parts[1] integerValue];
    } else {
        entry->_telHost = telEp;
        entry->_telPort = 20014;
    }

    entry->_hostID = [tokens[9] integerValue];
    return entry;
}

@end

@implementation ROSSothatDiscoveryClient

- (instancetype)initWithConfig:(ROSSothatConfig *)config {
    self = [super init];
    if (self) {
        _config = config ?: [ROSSothatConfig defaultConfig];
    }
    return self;
}

- (void)fetchServerListWithCompletion:(ROSSothatDiscoveryCompletion)completion {
    NSURL *url = [self.config discoveryURL];
    [ROSSothatLogger logInfo:@"Fetching server list from %@", [url absoluteString]];

    [[ROSSothatNetworkClient sharedClient] getStringFromURL:url timeout:self.config.timeoutSeconds completion:^(NSString *text, NSInteger statusCode, NSError *error) {
        if (error) {
            [ROSSothatLogger logError:@"Discovery network error: %@", [error localizedDescription]];
            if (completion) completion(nil, nil, error);
            return;
        }

        if (statusCode != 200 || !text) {
            [ROSSothatLogger logError:@"Discovery server returned HTTP %ld", (long)statusCode];
            NSError *httpErr = [NSError errorWithDomain:@"ROSSothatDiscoveryError" code:statusCode userInfo:@{NSLocalizedDescriptionKey: [NSString stringWithFormat:@"Discovery HTTP %ld", (long)statusCode]}];
            if (completion) completion(nil, nil, httpErr);
            return;
        }

        NSMutableArray<ROSSothatServerEntry *> *servers = [NSMutableArray array];
        NSString *detectedTrailer = nil;

        NSArray<NSString *> *lines = [text componentsSeparatedByCharactersInSet:[NSCharacterSet newlineCharacterSet]];
        for (NSString *line in lines) {
            NSString *trimmed = [line stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
            if ([trimmed hasPrefix:@"#network="]) {
                detectedTrailer = [trimmed substringFromIndex:9];
                continue;
            }
            ROSSothatServerEntry *entry = [ROSSothatServerEntry parseLegacyLine:trimmed];
            if (entry) {
                [servers addObject:entry];
            }
        }

        [ROSSothatLogger logInfo:@"Discovery parsed %lu server entries, trailer: %@", (unsigned long)[servers count], detectedTrailer ?: @"none"];
        if (completion) {
            completion(servers, detectedTrailer, nil);
        }
    }];
}

+ (void)discoverServerWithCurrentConfig:(nullable ROSSothatConfig *)config
                             completion:(ROSSothatAutoDiscoveryCompletion)completion {
    ROSSothatConfig *activeConfig = config ?: [ROSSothatConfig loadFromDocumentsDirectory:nil];
    if (!activeConfig) activeConfig = [ROSSothatConfig defaultConfig];

    [ROSSothatLogger logInfo:@"[AutoDiscovery] Starting multi-tier private server discovery..."];

    __block BOOL isCompleted = NO;
    __block NSLock *completionLock = [[NSLock alloc] init];

    void (^finish)(ROSSothatConfig *, NSString *) = ^(ROSSothatConfig *resCfg, NSString *desc) {
        [completionLock lock];
        if (isCompleted) {
            [completionLock unlock];
            return;
        }
        isCompleted = YES;
        [completionLock unlock];

        [ROSSothatLogger logInfo:@"[AutoDiscovery] SUCCESS: %@", desc];
        if (resCfg) {
            [ROSSothatConfig saveToDocumentsDirectory:resCfg error:nil];
        }
        dispatch_async(dispatch_get_main_queue(), ^{
            if (completion) {
                completion(resCfg, desc);
            }
        });
    };

    // Helper to probe a specific host via HTTP discovery endpoint
    void (^probeHost)(NSString *, void (^)(BOOL, ROSSothatConfig *)) = ^(NSString *host, void (^probeDone)(BOOL, ROSSothatConfig *)) {
        if (!host || [host length] == 0) {
            if (probeDone) probeDone(NO, nil);
            return;
        }
        NSURL *url = [NSURL URLWithString:[NSString stringWithFormat:@"http://%@:50010/v2/ros/discovery.json", host]];
        NSMutableURLRequest *req = [NSMutableURLRequest requestWithURL:url
                                                           cachePolicy:NSURLRequestReloadIgnoringLocalCacheData
                                                       timeoutInterval:0.8];
        req.HTTPMethod = @"GET";

        NSURLSessionConfiguration *sessionCfg = [NSURLSessionConfiguration ephemeralSessionConfiguration];
        sessionCfg.timeoutIntervalForRequest = 0.8;
        sessionCfg.timeoutIntervalForResource = 0.8;
        NSURLSession *session = [NSURLSession sessionWithConfiguration:sessionCfg];

        [[session dataTaskWithRequest:req completionHandler:^(NSData *data, NSURLResponse *response, NSError *error) {
            [session finishTasksAndInvalidate];
            if (!error && data && [(NSHTTPURLResponse *)response statusCode] == 200) {
                NSError *jsonErr = nil;
                NSDictionary *dict = [NSJSONSerialization JSONObjectWithData:data options:0 error:&jsonErr];
                if (!jsonErr && [dict isKindOfClass:[NSDictionary class]]) {
                    ROSSothatConfig *cfg = [ROSSothatConfig configFromJSONData:data error:nil];
                    if (cfg) {
                        if (probeDone) probeDone(YES, cfg);
                        return;
                    }
                }
            }
            if (probeDone) probeDone(NO, nil);
        }] resume];
    };

    // Tier 1: Try preferred mDNS hostname 'ros-sothatt.local'
    probeHost(@"ros-sothatt.local", ^(BOOL success, ROSSothatConfig *resCfg) {
        if (success && resCfg) {
            finish(resCfg, [NSString stringWithFormat:@"mDNS 'ros-sothatt.local' online -> %@", resCfg.serverHost]);
        }
    });

    // Tier 2: Try current configured host (if not 192.168.1.6 or obsolete)
    if (activeConfig.serverHost &&
        ![activeConfig.serverHost isEqualToString:@"192.168.1.6"] &&
        ![activeConfig.serverHost isEqualToString:@"192.168.1.9"]) {
        probeHost(activeConfig.serverHost, ^(BOOL success, ROSSothatConfig *resCfg) {
            if (success && resCfg) {
                finish(resCfg, [NSString stringWithFormat:@"Configured server %@ online", resCfg.serverHost]);
            }
        });
    }

    // Tier 3: Try confirmed phone hotspot server IP 172.20.10.2
    probeHost(@"172.20.10.2", ^(BOOL success, ROSSothatConfig *resCfg) {
        if (success && resCfg) {
            finish(resCfg, @"Phone Hotspot server 172.20.10.2 online");
        }
    });

    // Tier 4: UDP Broadcast Discovery on Port 50010
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        int sock = socket(AF_INET, SOCK_DGRAM, 0);
        if (sock >= 0) {
            int bcast = 1;
            setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &bcast, sizeof(bcast));
            struct timeval tv;
            tv.tv_sec = 0;
            tv.tv_usec = 800000; // 800ms
            setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

            const char *probeMsg = "ROSSOTHATT_DISCOVER_V1";
            struct sockaddr_in bcastAddr;
            memset(&bcastAddr, 0, sizeof(bcastAddr));
            bcastAddr.sin_family = AF_INET;
            bcastAddr.sin_port = htons(50010);
            bcastAddr.sin_addr.s_addr = inet_addr("255.255.255.255");
            sendto(sock, probeMsg, strlen(probeMsg), 0, (struct sockaddr *)&bcastAddr, sizeof(bcastAddr));

            bcastAddr.sin_addr.s_addr = inet_addr("172.20.10.15");
            sendto(sock, probeMsg, strlen(probeMsg), 0, (struct sockaddr *)&bcastAddr, sizeof(bcastAddr));

            char buf[2048] = {0};
            struct sockaddr_in fromAddr;
            socklen_t fromLen = sizeof(fromAddr);
            ssize_t n = recvfrom(sock, buf, sizeof(buf) - 1, 0, (struct sockaddr *)&fromAddr, &fromLen);
            close(sock);

            if (n > 0) {
                buf[n] = '\0';
                NSData *recvData = [NSData dataWithBytes:buf length:(NSUInteger)n];
                ROSSothatConfig *udpCfg = [ROSSothatConfig configFromJSONData:recvData error:nil];
                if (udpCfg) {
                    char senderIP[INET_ADDRSTRLEN] = {0};
                    inet_ntop(AF_INET, &fromAddr.sin_addr, senderIP, sizeof(senderIP));
                    finish(udpCfg, [NSString stringWithFormat:@"UDP Discovery Beacon from %s -> %@", senderIP, udpCfg.serverHost]);
                }
            }
        }
    });

    // Tier 5: Subnet sweep around active hotspot address (172.20.10.1 to 172.20.10.14)
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.3 * NSEC_PER_SEC)), dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        [completionLock lock];
        BOOL alreadyDone = isCompleted;
        [completionLock unlock];
        if (alreadyDone) return;

        for (int i = 1; i <= 14; i++) {
            NSString *ip = [NSString stringWithFormat:@"172.20.10.%d", i];
            probeHost(ip, ^(BOOL success, ROSSothatConfig *resCfg) {
                if (success && resCfg) {
                    finish(resCfg, [NSString stringWithFormat:@"Subnet probe found server at %@", ip]);
                }
            });
        }
    });

    // Tier 6: Safety Fallback Timeout (1.8s)
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(1.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        [completionLock lock];
        BOOL alreadyDone = isCompleted;
        [completionLock unlock];
        if (!alreadyDone) {
            finish(activeConfig, [NSString stringWithFormat:@"Discovery fallback to %@", activeConfig.serverHost]);
        }
    });
}

@end
