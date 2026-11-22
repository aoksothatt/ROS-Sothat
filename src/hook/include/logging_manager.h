//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: logging_manager.h
//
// Purpose: Privacy-redacting unified logging coordinator ensuring zero credential leakage.
//

#ifndef ROSSOTHAT_LOGGING_MANAGER_H
#define ROSSOTHAT_LOGGING_MANAGER_H

#import <Foundation/Foundation.h>
#import <os/log.h>

NS_ASSUME_NONNULL_BEGIN

@interface ROSSothatLogger : NSObject

+ (os_log_t)hookLog;
+ (void)logInfo:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);
+ (void)logWarning:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);
+ (void)logError:(NSString *)format, ... NS_FORMAT_FUNCTION(1, 2);

+ (NSString *)sanitizeString:(NSString *)input;
+ (NSString *)maskToken:(NSString *)token;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_LOGGING_MANAGER_H
