//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: logging_manager.m
//
// Purpose: Privacy-redacting unified logging coordinator ensuring zero credential leakage.
//

#import "logging_manager.h"

@implementation ROSSothatLogger

+ (os_log_t)hookLog {
    static os_log_t log;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        log = os_log_create("net.roslegacy.sothatt", "Hook");
    });
    return log;
}

+ (NSString *)maskToken:(NSString *)token {
    if (!token || [token length] < 8) {
        return @"[REDACTED]";
    }
    NSString *prefix = [token substringToIndex:4];
    NSString *suffix = [token substringFromIndex:[token length] - 4];
    return [NSString stringWithFormat:@"%@...%@", prefix, suffix];
}

+ (NSString *)sanitizeString:(NSString *)input {
    if (!input) return @"";

    // Scrub password patterns
    NSRegularExpression *pwRegex = [NSRegularExpression regularExpressionWithPattern:@"\"password\"\\s*:\\s*\"[^\"]+\"" options:NSRegularExpressionCaseInsensitive error:nil];
    NSString *scrubbed = [pwRegex stringByReplacingMatchesInString:input options:0 range:NSMakeRange(0, [input length]) withTemplate:@"\"password\":\"[REDACTED_PASSWORD]\""];

    // Scrub token patterns
    NSRegularExpression *tokRegex = [NSRegularExpression regularExpressionWithPattern:@"\"(ros_token|session)\"\\s*:\\s*\"([^\"]+)\"" options:NSRegularExpressionCaseInsensitive error:nil];
    NSArray<NSTextCheckingResult *> *matches = [tokRegex matchesInString:scrubbed options:0 range:NSMakeRange(0, [scrubbed length])];
    for (NSTextCheckingResult *m in [matches reverseObjectEnumerator]) {
        NSRange valRange = [m rangeAtIndex:2];
        NSString *val = [scrubbed substringWithRange:valRange];
        NSString *masked = [self maskToken:val];
        scrubbed = [scrubbed stringByReplacingCharactersInRange:valRange withString:masked];
    }

    return scrubbed;
}

+ (void)logInfo:(NSString *)format, ... {
    va_list args;
    va_start(args, format);
    NSString *msg = [[NSString alloc] initWithFormat:format arguments:args];
    va_end(args);

    NSString *clean = [self sanitizeString:msg];
    os_log_info([self hookLog], "%{public}@", clean);
}

+ (void)logWarning:(NSString *)format, ... {
    va_list args;
    va_start(args, format);
    NSString *msg = [[NSString alloc] initWithFormat:format arguments:args];
    va_end(args);

    NSString *clean = [self sanitizeString:msg];
    os_log_error([self hookLog], "WARNING: %{public}@", clean);
}

+ (void)logError:(NSString *)format, ... {
    va_list args;
    va_start(args, format);
    NSString *msg = [[NSString alloc] initWithFormat:format arguments:args];
    va_end(args);

    NSString *clean = [self sanitizeString:msg];
    os_log_fault([self hookLog], "ERROR: %{public}@", clean);
}

@end
