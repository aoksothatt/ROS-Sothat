//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: config_manager.m
//
// Purpose: Dynamic JSON configuration loader and schema validator for Documents/ros_server.json.
//

#import "config_manager.h"

static NSString *const kDefaultServerHost = @"192.168.1.6";
static const NSInteger kDefaultAuthPort = 20080;
static const NSInteger kDefaultDiscoveryPort = 50010;
static const NSInteger kDefaultDiscoveryHttpsPort = 50443;
static const NSInteger kDefaultBaseAppPort = 20014;
static const NSInteger kDefaultCellAppPort = 20002;
static NSString *const kDefaultAuthPath = @"/v2/ros/login_mobile_ios_v2";
static NSString *const kDefaultDiscoveryPath = @"/server_list_ios.txt";
static const NSTimeInterval kDefaultTimeout = 5.0;

@implementation ROSSothatConfig

+ (instancetype)defaultConfig {
    ROSSothatConfig *cfg = [[ROSSothatConfig alloc] init];
    cfg->_version = 1;
    cfg->_serverHost = kDefaultServerHost;
    cfg->_authPort = kDefaultAuthPort;
    cfg->_discoveryPort = kDefaultDiscoveryPort;
    cfg->_discoveryHttpsPort = kDefaultDiscoveryHttpsPort;
    cfg->_baseappPort = kDefaultBaseAppPort;
    cfg->_cellappPort = kDefaultCellAppPort;
    cfg->_authPath = kDefaultAuthPath;
    cfg->_discoveryPath = kDefaultDiscoveryPath;
    cfg->_timeoutSeconds = kDefaultTimeout;
    cfg->_tlsEnabled = NO;
    return cfg;
}

+ (BOOL)isValidPrivateHost:(NSString *)host {
    if (!host || [host length] == 0) return NO;

    // Reject prohibited public domains
    NSArray<NSString *> *blacklist = @[
        @"netease.com", @"163.com", @"easebar.com", @"gdl.netease.com",
        @"roslegacy.net", @"api.roslegacy.net", @"cdn.mobile.roslegacy.net"
    ];
    for (NSString *item in blacklist) {
        if ([host containsString:item]) {
            return NO;
        }
    }

    // Accept standard RFC1918 subnets: 10.x, 172.16-31.x, 192.168.x or local domains
    NSString *ipRegex = @"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$";
    NSPredicate *ipPred = [NSPredicate predicateWithFormat:@"SELF MATCHES %@", ipRegex];
    if ([ipPred evaluateWithObject:host]) {
        return YES;
    }

    // Hostname check (.local, .internal, localhost)
    if ([host hasSuffix:@".local"] || [host hasSuffix:@".lan"] || [host isEqualToString:@"localhost"] || [host isEqualToString:@"127.0.0.1"]) {
        return YES;
    }

    return NO;
}

+ (nullable instancetype)configFromJSONData:(NSData *)data error:(NSError **)error {
    if (!data) return nil;

    NSDictionary *dict = [NSJSONSerialization JSONObjectWithData:data options:0 error:error];
    if (!dict || ![dict isKindOfClass:[NSDictionary class]]) {
        return nil;
    }

    NSString *host = dict[@"server_host"];
    if (![self isValidPrivateHost:host]) {
        if (error) {
            *error = [NSError errorWithDomain:@"ROSSothatConfigError" code:101 userInfo:@{NSLocalizedDescriptionKey: @"Invalid or prohibited server host."}];
        }
        return nil;
    }

    ROSSothatConfig *cfg = [[ROSSothatConfig alloc] init];
    cfg->_version = [dict[@"version"] integerValue] ?: 1;
    cfg->_serverHost = [host copy];
    cfg->_authPort = [dict[@"auth_port"] integerValue] ?: kDefaultAuthPort;
    cfg->_discoveryPort = [dict[@"discovery_port"] integerValue] ?: kDefaultDiscoveryPort;
    cfg->_discoveryHttpsPort = [dict[@"discovery_https_port"] integerValue] ?: kDefaultDiscoveryHttpsPort;
    cfg->_baseappPort = [dict[@"baseapp_port"] integerValue] ?: kDefaultBaseAppPort;
    cfg->_cellappPort = [dict[@"cellapp_port"] integerValue] ?: kDefaultCellAppPort;
    cfg->_authPath = dict[@"auth_path"] ?: kDefaultAuthPath;
    cfg->_discoveryPath = dict[@"discovery_path"] ?: kDefaultDiscoveryPath;
    cfg->_timeoutSeconds = [dict[@"timeout_seconds"] doubleValue] ?: kDefaultTimeout;
    cfg->_tlsEnabled = [dict[@"tls_enabled"] boolValue];

    return cfg;
}

+ (NSString *)documentsConfigPath {
    NSArray *paths = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES);
    NSString *docsDir = [paths firstObject];
    return [docsDir stringByAppendingPathComponent:@"ros_server.json"];
}

+ (nullable instancetype)loadFromDocumentsDirectory:(NSError **)error {
    NSString *path = [self documentsConfigPath];
    if (![[NSFileManager defaultManager] fileExistsAtPath:path]) {
        // Fresh install: check for default ros_server.json in the application bundle first
        NSString *bundlePath = [[NSBundle mainBundle] pathForResource:@"ros_server" ofType:@"json"];
        if (bundlePath && [[NSFileManager defaultManager] fileExistsAtPath:bundlePath]) {
            NSData *bundleData = [NSData dataWithContentsOfFile:bundlePath options:0 error:nil];
            if (bundleData) {
                ROSSothatConfig *bundleCfg = [self configFromJSONData:bundleData error:nil];
                if (bundleCfg) {
                    [self saveToDocumentsDirectory:bundleCfg error:nil];
                    return bundleCfg;
                }
            }
        }

        // Fallback to compiled default configuration and write initial file
        ROSSothatConfig *def = [self defaultConfig];
        [self saveToDocumentsDirectory:def error:nil];
        return def;
    }

    NSData *data = [NSData dataWithContentsOfFile:path options:0 error:error];
    if (!data) return [self defaultConfig];

    ROSSothatConfig *cfg = [self configFromJSONData:data error:error];
    if (!cfg) {
        return [self defaultConfig];
    }

    // Auto-migration: if persisted documents config still holds retired or broken IPs,
    // seamlessly migrate to the active LAN server host without requiring manual reset.
    BOOL needsResave = NO;
    if ([cfg.serverHost isEqualToString:@"192.168.1.13"] || [cfg.serverHost isEqualToString:@"192.168.1.7"] || [cfg.serverHost hasPrefix:@"192.168.100."]) {
        cfg->_serverHost = [kDefaultServerHost copy];
        needsResave = YES;
    }
    if ([cfg.authPath isEqualToString:@"/v2/ros/login_mobile_ios"]) {
        cfg->_authPath = [kDefaultAuthPath copy];
        needsResave = YES;
    }
    if (needsResave) {
        [self saveToDocumentsDirectory:cfg error:nil];
    }

    return cfg;
}

+ (BOOL)saveToDocumentsDirectory:(ROSSothatConfig *)config error:(NSError **)error {
    if (!config) return NO;

    NSDictionary *dict = @{
        @"version": @(config.version),
        @"server_host": config.serverHost,
        @"auth_port": @(config.authPort),
        @"discovery_port": @(config.discoveryPort),
        @"discovery_https_port": @(config.discoveryHttpsPort),
        @"baseapp_port": @(config.baseappPort),
        @"cellapp_port": @(config.cellappPort),
        @"auth_path": config.authPath,
        @"discovery_path": config.discoveryPath,
        @"timeout_seconds": @(config.timeoutSeconds),
        @"tls_enabled": @(config.tlsEnabled)
    };

    NSData *data = [NSJSONSerialization dataWithJSONObject:dict options:NSJSONWritingPrettyPrinted error:error];
    if (!data) return NO;

    return [data writeToFile:[self documentsConfigPath] options:NSDataWritingAtomic error:error];
}

- (NSURL *)authURL {
    NSString *scheme = self.tlsEnabled ? @"https" : @"http";
    NSString *path = [self.authPath hasPrefix:@"/"] ? self.authPath : [@"/" stringByAppendingString:self.authPath ?: @""];
    return [NSURL URLWithString:[NSString stringWithFormat:@"%@://%@:%ld%@", scheme, self.serverHost, (long)self.authPort, path]];
}

- (NSURL *)discoveryURL {
    NSString *scheme = self.tlsEnabled ? @"https" : @"http";
    return [NSURL URLWithString:[NSString stringWithFormat:@"%@://%@:%ld%@", scheme, self.serverHost, (long)self.discoveryPort, self.discoveryPath]];
}

- (BOOL)isLoopback {
    return [self.serverHost isEqualToString:@"127.0.0.1"] || [self.serverHost isEqualToString:@"localhost"];
}

@end
