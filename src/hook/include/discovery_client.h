//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: discovery_client.h
//
// Purpose: Server discovery parser extracting BaseApp UDP endpoint from authentic 10-token response.
//

#ifndef ROSSOTHAT_DISCOVERY_CLIENT_H
#define ROSSOTHAT_DISCOVERY_CLIENT_H

#import <Foundation/Foundation.h>
#import "config_manager.h"

NS_ASSUME_NONNULL_BEGIN

@interface ROSSothatServerEntry : NSObject

@property (nonatomic, copy, readonly) NSString *zone;
@property (nonatomic, assign, readonly) NSInteger numberSt;
@property (nonatomic, assign, readonly) NSInteger netSt;
@property (nonatomic, assign, readonly) NSInteger serverSt;
@property (nonatomic, copy, readonly) NSString *name;
@property (nonatomic, copy, readonly) NSString *oriName;
@property (nonatomic, copy, readonly) NSString *telHost;
@property (nonatomic, assign, readonly) NSInteger telPort;
@property (nonatomic, assign, readonly) NSInteger hostID;

+ (nullable instancetype)parseLegacyLine:(NSString *)line;

@end

typedef void (^ROSSothatDiscoveryCompletion)(NSArray<ROSSothatServerEntry *> * _Nullable servers, NSString * _Nullable trailer, NSError * _Nullable error);
typedef void (^ROSSothatAutoDiscoveryCompletion)(ROSSothatConfig * _Nullable discoveredConfig, NSString * _Nullable statusDescription);

@interface ROSSothatDiscoveryClient : NSObject

@property (nonatomic, strong, readonly) ROSSothatConfig *config;

- (instancetype)initWithConfig:(ROSSothatConfig *)config;

- (void)fetchServerListWithCompletion:(ROSSothatDiscoveryCompletion)completion;

/**
 * Multi-Tier Automatic Private Server Discovery:
 * Tier 1: Hostname check ('ros-sothatt.local')
 * Tier 2: UDP Broadcast & Unicast beacon query on port 50010
 * Tier 3: Parallel HTTP subnet scan (172.20.10.x / 192.168.x / 10.x)
 * Tier 4: Configured host fallback
 */
+ (void)discoverServerWithCurrentConfig:(nullable ROSSothatConfig *)config
                             completion:(ROSSothatAutoDiscoveryCompletion)completion;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_DISCOVERY_CLIENT_H
