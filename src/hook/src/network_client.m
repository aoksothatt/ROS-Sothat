//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: network_client.m
//
// Purpose: Asynchronous HTTP transport client using NSURLSession with timeout safeguards.
//

#import "network_client.h"

@interface ROSSothatNetworkClient ()
@property (nonatomic, strong) NSURLSession *session;
@end

@implementation ROSSothatNetworkClient

+ (instancetype)sharedClient {
    static ROSSothatNetworkClient *client;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        client = [[ROSSothatNetworkClient alloc] init];
    });
    return client;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        NSURLSessionConfiguration *config = [NSURLSessionConfiguration ephemeralSessionConfiguration];
        config.requestCachePolicy = NSURLRequestReloadIgnoringLocalCacheData;
        _session = [NSURLSession sessionWithConfiguration:config];
    }
    return self;
}

- (void)postJSON:(NSDictionary *)jsonDict
           toURL:(NSURL *)url
         timeout:(NSTimeInterval)timeout
      completion:(ROSSothatHTTPCompletion)completion {
    NSError *error = nil;
    NSData *bodyData = [NSJSONSerialization dataWithJSONObject:jsonDict options:0 error:&error];
    if (error) {
        if (completion) completion(nil, 0, error);
        return;
    }

    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    request.HTTPMethod = @"POST";
    request.timeoutInterval = timeout;
    [request setValue:@"application/json; charset=utf-8" forHTTPHeaderField:@"Content-Type"];
    [request setValue:@"application/json" forHTTPHeaderField:@"Accept"];
    request.HTTPBody = bodyData;

    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *taskError) {
        NSInteger statusCode = 0;
        if ([response isKindOfClass:[NSHTTPURLResponse class]]) {
            statusCode = ((NSHTTPURLResponse *)response).statusCode;
        }
        if (completion) {
            completion(data, statusCode, taskError);
        }
    }];
    [task resume];
}

- (void)getStringFromURL:(NSURL *)url
                 timeout:(NSTimeInterval)timeout
              completion:(void (^)(NSString * _Nullable text, NSInteger statusCode, NSError * _Nullable error))completion {
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    request.HTTPMethod = @"GET";
    request.timeoutInterval = timeout;
    [request setValue:@"text/plain, */*" forHTTPHeaderField:@"Accept"];

    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *taskError) {
        NSInteger statusCode = 0;
        NSString *text = nil;
        if ([response isKindOfClass:[NSHTTPURLResponse class]]) {
            statusCode = ((NSHTTPURLResponse *)response).statusCode;
        }
        if (data) {
            text = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
        }
        if (completion) {
            completion(text, statusCode, taskError);
        }
    }];
    [task resume];
}

@end
