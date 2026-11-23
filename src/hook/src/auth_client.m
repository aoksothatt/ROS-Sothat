//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: auth_client.m
//
// Purpose: Authentication client coordinating login REST calls, password wiping, and session key calculation.
//

#import "auth_client.h"
#import "network_client.h"
#import "session_manager.h"
#import "logging_manager.h"
#include <string.h>

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

    // Prepare JSON payload (immutable NSString references are scoped strictly to request dispatch)
    NSDictionary *body = @{
        @"username": username,
        @"password": password
    };

    NSURL *url = [self.config authURL];
    [ROSSothatLogger logInfo:@"[AuthClient] Dispatching login request for user '%@' to effective URL: %@",
     username, [url absoluteString]];

    [[ROSSothatNetworkClient sharedClient] postJSON:body toURL:url timeout:self.config.timeoutSeconds completion:^(NSData *data, NSInteger statusCode, NSError *error) {
        if (error) {
            [ROSSothatLogger logError:@"[AuthClient] Network failure for user '%@' to %@ (Domain: %@, Code: %ld): %@",
             username, [url absoluteString], error.domain, (long)error.code, [error localizedDescription]];

            NSString *errorMsg = [NSString stringWithFormat:@"Cannot reach auth server at %@:%ld (code %ld): %@",
                                  self.config.serverHost, (long)self.config.authPort, (long)error.code, [error localizedDescription]];
            if (error.code == -1001) {
                errorMsg = [NSString stringWithFormat:@"Connection timed out reaching %@:%ld after 15s. Check server status and Wi-Fi.",
                            self.config.serverHost, (long)self.config.authPort];
            } else if (error.code == -1009) {
                errorMsg = [NSString stringWithFormat:@"Cannot reach server at %@ (code -1009). Ensure Local Network access is ON in iPhone Settings > ROS Sothatt and device is on Wi-Fi.",
                            self.config.serverHost];
            }
            if (completion) completion(NO, 0, errorMsg);
            return;
        }

        if (statusCode == 401) {
            [ROSSothatLogger logWarning:@"Auth rejected (HTTP 401): Invalid credentials"];
            if (completion) completion(NO, 0, @"Invalid username or password.");
            return;
        }

        if (statusCode == 403) {
            [ROSSothatLogger logWarning:@"Auth rejected (HTTP 403): Account suspended"];
            if (completion) completion(NO, 0, @"Account has been suspended or banned.");
            return;
        }

        if (statusCode != 200 || !data) {
            [ROSSothatLogger logError:@"Auth server returned unexpected status HTTP %ld", (long)statusCode];
            if (completion) completion(NO, 0, [NSString stringWithFormat:@"Server error (HTTP %ld).", (long)statusCode]);
            return;
        }

        NSError *jsonError = nil;
        NSDictionary *resp = [NSJSONSerialization JSONObjectWithData:data options:0 error:&jsonError];
        if (jsonError || ![resp isKindOfClass:[NSDictionary class]]) {
            [ROSSothatLogger logError:@"Failed to parse auth response JSON"];
            if (completion) completion(NO, 0, @"Invalid server response format.");
            return;
        }

        BOOL success = [resp[@"success"] boolValue];
        if (!success) {
            NSString *msg = resp[@"message"] ?: @"Authentication failed.";
            [ROSSothatLogger logWarning:@"Auth rejected by server: %@", msg];
            if (completion) completion(NO, 0, msg);
            return;
        }

        NSString *token = resp[@"ros_token"];
        if (!token || ![token isKindOfClass:[NSString class]] || [token length] == 0) {
            [ROSSothatLogger logError:@"Auth success but missing ros_token"];
            if (completion) completion(NO, 0, @"Server response missing authentication token.");
            return;
        }

        // Derive 32-bit FNV-1a session key from ros_token
        uint32_t sessionKey = rossothat_fnv1a_32([token UTF8String]);
        rossothat_set_session_key(sessionKey);

        [ROSSothatLogger logInfo:@"Auth successful for user '%@', token: %@, derived sessionKey: 0x%08X",
         username, [ROSSothatLogger maskToken:token], sessionKey];

        if (completion) {
            completion(YES, sessionKey, nil);
        }
    }];
}

@end
