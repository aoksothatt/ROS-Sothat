//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: config_manager.h
//
// Purpose: Dynamic JSON configuration loader and schema validator for Documents/ros_server.json.
//

#ifndef ROSSOTHAT_CONFIG_MANAGER_H
#define ROSSOTHAT_CONFIG_MANAGER_H

#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface ROSSothatConfig : NSObject

@property (nonatomic, assign, readonly) NSInteger version;
@property (nonatomic, copy, readonly) NSString *serverHost;
@property (nonatomic, assign, readonly) NSInteger authPort;
@property (nonatomic, assign, readonly) NSInteger discoveryPort;
@property (nonatomic, assign, readonly) NSInteger discoveryHttpsPort;
@property (nonatomic, assign, readonly) NSInteger baseappPort;
@property (nonatomic, assign, readonly) NSInteger cellappPort;
@property (nonatomic, copy, readonly) NSString *authPath;
@property (nonatomic, copy, readonly) NSString *discoveryPath;
@property (nonatomic, assign, readonly) NSTimeInterval timeoutSeconds;
@property (nonatomic, assign, readonly) BOOL tlsEnabled;

+ (instancetype)defaultConfig;
+ (nullable instancetype)configFromJSONData:(NSData *)data error:(NSError **)error;
+ (nullable instancetype)loadFromDocumentsDirectory:(NSError **)error;
+ (BOOL)saveToDocumentsDirectory:(ROSSothatConfig *)config error:(NSError **)error;

- (NSURL *)authURL;
- (NSURL *)discoveryURL;
- (BOOL)isLoopback;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_CONFIG_MANAGER_H
