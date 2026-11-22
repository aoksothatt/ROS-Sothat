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

@interface ROSSothatDiscoveryClient : NSObject

@property (nonatomic, strong, readonly) ROSSothatConfig *config;

- (instancetype)initWithConfig:(ROSSothatConfig *)config;

- (void)fetchServerListWithCompletion:(ROSSothatDiscoveryCompletion)completion;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_DISCOVERY_CLIENT_H
