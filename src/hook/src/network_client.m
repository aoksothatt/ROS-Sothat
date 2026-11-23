//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: network_client.m
//
// Purpose: Asynchronous HTTP transport client using NSURLSession with timeout safeguards.
//

#import "network_client.h"
#import "logging_manager.h"

@interface ROSSothatNetworkClient () <NSURLSessionTaskDelegate>
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
        config.waitsForConnectivity = NO;
    }
    config.allowsCellularAccess = NO;
    config.timeoutIntervalForRequest = 15.0;
    config.timeoutIntervalForResource = 30.0;
    _session = [NSURLSession sessionWithConfiguration:config delegate:self delegateQueue:nil];
}

- (void)resetSession {
    if (_session) {
        [_session finishTasksAndInvalidate];
    }
    [self createSession];
    [ROSSothatLogger logInfo:@"[NetworkClient] Session reset; fresh connection pool ready"];
}

#pragma mark - NSURLSessionTaskDelegate

- (void)URLSession:(NSURLSession *)session taskIsWaitingForConnectivity:(NSURLSessionTask *)task {
    [ROSSothatLogger logWarning:@"[NetworkClient] Task %lu waited for connectivity to %@",
     (unsigned long)task.taskIdentifier, [task.originalRequest.URL absoluteString]];
}

- (void)URLSession:(NSURLSession *)session task:(NSURLSessionTask *)task didFinishCollectingMetrics:(NSURLSessionTaskMetrics *)metrics {
    if (@available(iOS 10.0, *)) {
        NSTimeInterval totalDuration = [metrics.taskInterval duration];
        [ROSSothatLogger logInfo:@"[NetworkClient] Task %lu metrics: totalDuration=%.3fs, txCount=%lu",
         (unsigned long)task.taskIdentifier, totalDuration, (unsigned long)[metrics.transactionMetrics count]];
        for (NSURLSessionTaskTransactionMetrics *tx in metrics.transactionMetrics) {
            NSTimeInterval connectDuration = 0.0;
            if (tx.connectStartDate && tx.connectEndDate) {
                connectDuration = [tx.connectEndDate timeIntervalSinceDate:tx.connectStartDate];
            }
            NSTimeInterval responseDuration = 0.0;
            if (tx.requestStartDate && tx.responseEndDate) {
                responseDuration = [tx.responseEndDate timeIntervalSinceDate:tx.requestStartDate];
            }
            [ROSSothatLogger logInfo:@"[NetworkClient] Task %lu timing: connect=%.3fs, reqResp=%.3fs, local=%@, remote=%@, proto=%@",
             (unsigned long)task.taskIdentifier, connectDuration, responseDuration,
             tx.localAddress ?: @"none", tx.remoteAddress ?: @"none", tx.networkProtocolName ?: @"unknown"];
        }
    }
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

    NSTimeInterval effectiveTimeout = (timeout >= 15.0) ? timeout : 15.0;
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    request.HTTPMethod = @"POST";
    request.timeoutInterval = effectiveTimeout;
    [request setValue:@"application/json; charset=utf-8" forHTTPHeaderField:@"Content-Type"];
    [request setValue:@"application/json" forHTTPHeaderField:@"Accept"];
    request.HTTPBody = bodyData;

    NSDate *requestStartTime = [NSDate date];
    [ROSSothatLogger logInfo:@"[NetworkClient] POST %@ (payload: %lu bytes, timeout: %.1fs, cellular=NO, waitsForConn=NO)",
     [url absoluteString], (unsigned long)[bodyData length], effectiveTimeout];

    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *taskError) {
        NSTimeInterval elapsed = [[NSDate date] timeIntervalSinceDate:requestStartTime];
        NSInteger statusCode = 0;
        if ([response isKindOfClass:[NSHTTPURLResponse class]]) {
            statusCode = ((NSHTTPURLResponse *)response).statusCode;
        }
        if (taskError) {
            NSError *underlying = taskError.userInfo[NSUnderlyingErrorKey];
            if (underlying) {
                [ROSSothatLogger logError:@"[NetworkClient] POST %@ failed after %.3fs — Domain: %@, Code: %ld, Desc: %@, Underlying: [%@ %ld: %@]",
                 [url absoluteString], elapsed, taskError.domain, (long)taskError.code, [taskError localizedDescription],
                 underlying.domain, (long)underlying.code, [underlying localizedDescription]];
            } else {
                [ROSSothatLogger logError:@"[NetworkClient] POST %@ failed after %.3fs — Domain: %@, Code: %ld, Desc: %@",
                 [url absoluteString], elapsed, taskError.domain, (long)taskError.code, [taskError localizedDescription]];
            }
        } else {
            [ROSSothatLogger logInfo:@"[NetworkClient] POST %@ finished after %.3fs (HTTP %ld, %lu bytes)",
             [url absoluteString], elapsed, (long)statusCode, (unsigned long)[data length]];
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
    NSTimeInterval effectiveTimeout = (timeout >= 15.0) ? timeout : 15.0;
    NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:url];
    request.HTTPMethod = @"GET";
    request.timeoutInterval = effectiveTimeout;
    [request setValue:@"text/plain, */*" forHTTPHeaderField:@"Accept"];

    NSDate *startTime = [NSDate date];
    NSURLSessionDataTask *task = [self.session dataTaskWithRequest:request completionHandler:^(NSData *data, NSURLResponse *response, NSError *taskError) {
        NSTimeInterval elapsed = [[NSDate date] timeIntervalSinceDate:startTime];
        NSInteger statusCode = 0;
        NSString *text = nil;
        if ([response isKindOfClass:[NSHTTPURLResponse class]]) {
            statusCode = ((NSHTTPURLResponse *)response).statusCode;
        }
        if (taskError) {
            NSError *underlying = taskError.userInfo[NSUnderlyingErrorKey];
            if (underlying) {
                [ROSSothatLogger logError:@"[NetworkClient] GET %@ failed after %.3fs — Domain: %@, Code: %ld, Desc: %@, Underlying: [%@ %ld: %@]",
                 [url absoluteString], elapsed, taskError.domain, (long)taskError.code, [taskError localizedDescription],
                 underlying.domain, (long)underlying.code, [underlying localizedDescription]];
            } else {
                [ROSSothatLogger logError:@"[NetworkClient] GET %@ failed after %.3fs — Domain: %@, Code: %ld, Desc: %@",
                 [url absoluteString], elapsed, taskError.domain, (long)taskError.code, [taskError localizedDescription]];
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
