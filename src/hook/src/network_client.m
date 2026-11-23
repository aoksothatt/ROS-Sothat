//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: network_client.m
//
// Purpose: Asynchronous HTTP transport client using NSURLSession with timeout safeguards.
//

#import "network_client.h"
#import "logging_manager.h"

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
        [self createSession];
    }
    return self;
}

- (void)createSession {
    NSURLSessionConfiguration *config = [NSURLSessionConfiguration defaultSessionConfiguration];
    config.requestCachePolicy = NSURLRequestReloadIgnoringLocalCacheData;
    if (@available(iOS 11.0, *)) {
        config.waitsForConnectivity = YES;
    }
    config.allowsCellularAccess = NO;
    config.timeoutIntervalForRequest = 15.0;
    config.timeoutIntervalForResource = 30.0;
    _session = [NSURLSession sessionWithConfiguration:config];
}

- (void)resetSession {
    if (_session) {
        [_session finishTasksAndInvalidate];
    }
    [self createSession];
    [ROSSothatLogger logInfo:@"[NetworkClient] Session reset; fresh connection pool ready"];
}

- (void)postJSON:(NSDictionary *)jsonDict
           toURL:(NSURL *)url
         timeout:(NSTimeInterval)timeout
      completion:(ROSSothatHTTPCompletion)completion {
    NSError *error = nil;
    NSData *bodyData = [NSJSONSerialization dataWithJSONObject:jsonDict options:0 error:&error];
    if (error) {
        [ROSSothatLogger logError:@"[NetworkClient] JSON serialization failed: %@", [error localizedDescription]];
        if (completion) completion(nil, 0, error);
        return;
    }

    NSTimeInterval effectiveTimeout = (timeout > 0.0) ? timeout : 15.0;
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    request.HTTPMethod = @"POST";
    request.timeoutInterval = effectiveTimeout;
    [request setValue:@"application/json; charset=utf-8" forHTTPHeaderField:@"Content-Type"];
    [request setValue:@"application/json" forHTTPHeaderField:@"Accept"];
    request.HTTPBody = bodyData;

    [ROSSothatLogger logInfo:@"[NetworkClient] POST %@ (payload: %lu bytes, timeout: %.1fs)",
     [url absoluteString], (unsigned long)[bodyData length], effectiveTimeout];

    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *taskError) {
        NSInteger statusCode = 0;
        if ([response isKindOfClass:[NSHTTPURLResponse class]]) {
            statusCode = ((NSHTTPURLResponse *)response).statusCode;
        }
        if (taskError) {
            NSError *underlying = taskError.userInfo[NSUnderlyingErrorKey];
            if (underlying) {
                [ROSSothatLogger logError:@"[NetworkClient] POST %@ failed — Domain: %@, Code: %ld, Desc: %@, Underlying: [%@ %ld: %@]",
                 [url absoluteString], taskError.domain, (long)taskError.code, [taskError localizedDescription],
                 underlying.domain, (long)underlying.code, [underlying localizedDescription]];
            } else {
                [ROSSothatLogger logError:@"[NetworkClient] POST %@ failed — Domain: %@, Code: %ld, Desc: %@",
                 [url absoluteString], taskError.domain, (long)taskError.code, [taskError localizedDescription]];
            }
        } else {
            [ROSSothatLogger logInfo:@"[NetworkClient] POST %@ finished (HTTP %ld, %lu bytes)",
             [url absoluteString], (long)statusCode, (unsigned long)[data length]];
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
        if (taskError) {
            NSError *underlying = taskError.userInfo[NSUnderlyingErrorKey];
            if (underlying) {
                [ROSSothatLogger logError:@"[NetworkClient] GET %@ failed — Domain: %@, Code: %ld, Desc: %@, Underlying: [%@ %ld: %@]",
                 [url absoluteString], taskError.domain, (long)taskError.code, [taskError localizedDescription],
                 underlying.domain, (long)underlying.code, [underlying localizedDescription]];
            } else {
                [ROSSothatLogger logError:@"[NetworkClient] GET %@ failed — Domain: %@, Code: %ld, Desc: %@",
                 [url absoluteString], taskError.domain, (long)taskError.code, [taskError localizedDescription]];
            }
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
