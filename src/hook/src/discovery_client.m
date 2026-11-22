//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: discovery_client.m
//
// Purpose: Server discovery parser extracting BaseApp UDP endpoint from authentic 10-token response.
//

#import "discovery_client.h"
#import "network_client.h"
#import "logging_manager.h"

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

@end
