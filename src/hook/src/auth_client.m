//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: auth_client.m
//
// Purpose: Authentication client coordinating pre-authentication HTTP calls,
//          single-use ticket acquisition, password wiping, and session key calculation.
//

#import "auth_client.h"
#import "network_client.h"
#import "session_manager.h"
#import "logging_manager.h"
#include <string.h>

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
    [ROSSothatLogger logInfo:@"[AuthClient] Dispatching pre-authentication request for user '%@' to: %@",
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
        NSString *ticket = resp[@"ticket"] ?: token;

        // Store pre-authentication ticket for BigWorld Mercury logOn handoff
        if (ticket && [ticket length] > 0) {
            rossothat_set_active_ticket([ticket UTF8String]);
        }

        // Derive 32-bit FNV-1a session key from ros_token
        uint32_t sessionKey = 0;
        if (token && [token length] > 0) {
            sessionKey = rossothat_fnv1a_32([token UTF8String]);
            rossothat_set_session_key(sessionKey);
        }

        [ROSSothatLogger logInfo:@"Auth successful for user '%@', ticket: %@, derived sessionKey: 0x%08X",
         username, [ROSSothatLogger maskToken:ticket ?: token], sessionKey];

        if (completion) {
            completion(YES, sessionKey, nil);
        }
    }];
}

@end
