//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: network_client.h
//
// Purpose: Asynchronous HTTP transport client using NSURLSession with timeout safeguards.
//

#ifndef ROSSOTHAT_NETWORK_CLIENT_H
#define ROSSOTHAT_NETWORK_CLIENT_H

#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

typedef void (^ROSSothatHTTPCompletion)(NSData * _Nullable data, NSInteger statusCode, NSError * _Nullable error);

@interface ROSSothatNetworkClient : NSObject

+ (instancetype)sharedClient;

- (void)resetSession;

- (void)postJSON:(NSDictionary *)jsonDict
           toURL:(NSURL *)url
         timeout:(NSTimeInterval)timeout
      completion:(ROSSothatHTTPCompletion)completion;

- (void)getStringFromURL:(NSURL *)url
                 timeout:(NSTimeInterval)timeout
              completion:(void (^)(NSString * _Nullable text, NSInteger statusCode, NSError * _Nullable error))completion;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_NETWORK_CLIENT_H
