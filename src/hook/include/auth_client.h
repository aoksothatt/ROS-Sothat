//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: auth_client.h
//
// Purpose: Authentication client coordinating login REST calls, password wiping, and session key calculation.
//

#ifndef ROSSOTHAT_AUTH_CLIENT_H
#define ROSSOTHAT_AUTH_CLIENT_H

#import <Foundation/Foundation.h>
#import "config_manager.h"

NS_ASSUME_NONNULL_BEGIN

typedef void (^ROSSothatAuthCompletion)(BOOL success, uint32_t sessionKey, NSString * _Nullable errorMessage);
typedef void (^ROSSothatRegisterCompletion)(BOOL success, NSString * _Nullable errorMessage);

@interface ROSSothatAuthClient : NSObject

@property (nonatomic, strong) ROSSothatConfig *config;

- (instancetype)initWithConfig:(ROSSothatConfig *)config;

/**
 * Authenticates with the private ROS Sothatt Legacy Mobile Auth Service.
 * Ephemeral request payload; credentials are not retained beyond request dispatch.
 */
- (void)loginWithUsername:(NSString *)username
                 password:(NSString *)password
               completion:(ROSSothatAuthCompletion)completion;

/**
 * Registers a new player account on the private ROS Sothatt backend.
 */
- (void)registerWithUsername:(NSString *)username
                    password:(NSString *)password
             confirmPassword:(NSString *)confirmPassword
                  inviteCode:(nullable NSString *)inviteCode
                  completion:(ROSSothatRegisterCompletion)completion;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_AUTH_CLIENT_H
