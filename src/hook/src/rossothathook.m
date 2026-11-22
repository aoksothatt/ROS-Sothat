//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: rossothathook.m
//
// Purpose: Primary entry point, dyld constructor, UniSDK method swizzling, and socket hook registration.
//

#import "rossothathook.h"
#import "config_manager.h"
#import "baseapp_hook.h"
#import "logging_manager.h"
#import "SothattLoginVC.h"
#import <objc/runtime.h>
#import <UIKit/UIKit.h>

// Exported ABI stubs for dyld / dlsym compatibility
__attribute__((visibility("default"))) void ros_apply_ticket(void) {
    [ROSSothatLogger logInfo:@"ABI Stub called: ros_apply_ticket()"];
}

__attribute__((visibility("default"))) void ros_set_ticket(void) {
    [ROSSothatLogger logInfo:@"ABI Stub called: ros_set_ticket()"];
}

// Forward declarations for NetEase UniSDK interposition
static void (*orig_ntLogin)(id, SEL) = NULL;

@interface ROSSothatHookCoordinator : NSObject
@property (nonatomic, strong) ROSSothatConfig *config;
+ (instancetype)sharedCoordinator;
- (void)handleNtLoginWithTarget:(id)target selector:(SEL)selector;
@end

@implementation ROSSothatHookCoordinator

+ (instancetype)sharedCoordinator {
    static ROSSothatHookCoordinator *coord;
    static dispatch_once_t onceToken;
    dispatch_once(&onceToken, ^{
        coord = [[ROSSothatHookCoordinator alloc] init];
    });
    return coord;
}

- (instancetype)init {
    self = [super init];
    if (self) {
        _config = [ROSSothatConfig loadFromDocumentsDirectory:nil];
    }
    return self;
}

- (void)handleNtLoginWithTarget:(id)target selector:(SEL)selector {
    [ROSSothatLogger logInfo:@"Intercepted NtSdkBase::ntLogin() — Suppressing NetEase UniSDK dialog"];

    dispatch_async(dispatch_get_main_queue(), ^{
        UIViewController *root = [UIApplication sharedApplication].keyWindow.rootViewController;
        while (root.presentedViewController) {
            root = root.presentedViewController;
        }

        if (!root) {
            [ROSSothatLogger logError:@"Cannot present SothattLoginVC: rootViewController is nil"];
            return;
        }

        SothattLoginVC *loginVC = [SothattLoginVC viewControllerWithConfig:self.config];
        loginVC.onLoginSuccess = ^(uint32_t sessionKey) {
            [ROSSothatLogger logInfo:@"Login success callback: sessionKey=0x%08X. Posting NT_NOTIFICATION_LOGIN {state=0}", sessionKey];

            // Post NetEase UniSDK notification to signal Python engine that login succeeded
            NSDictionary *notifyDict = @{@"login_state": @(0), @"channel": @"sothatt"};
            [[NSNotificationCenter defaultCenter] postNotificationName:@"NT_NOTIFICATION_LOGIN"
                                                                object:target
                                                              userInfo:notifyDict];
        };

        [root presentViewController:loginVC animated:YES completion:nil];
    });
}

@end

static void sothat_swizzled_ntLogin(id self, SEL _cmd) {
    [[ROSSothatHookCoordinator sharedCoordinator] handleNtLoginWithTarget:self selector:_cmd];
}

void rossothat_hook_initialize(void) {
    [ROSSothatLogger logInfo:@"=========================================================="];
    [ROSSothatLogger logInfo:@" ROS SOTHATT CLEAN-ROOM HOOK v%s INITIALIZING", ROSSOTHAT_HOOK_VERSION_STRING];
    [ROSSothatLogger logInfo:@"=========================================================="];

    ROSSothatConfig *config = [ROSSothatConfig loadFromDocumentsDirectory:nil];
    [ROSSothatLogger logInfo:@"Loaded server config: host=%@, auth=%ld, disc=%ld, baseapp=%ld",
     config.serverHost, (long)config.authPort, (long)config.discoveryPort, (long)config.baseappPort];

    // 1. Install POSIX sendto / recvfrom socket hooks
    int hookRes = rossothat_install_socket_hooks((uint16_t)config.baseappPort);
    if (hookRes == 0) {
        [ROSSothatLogger logInfo:@"POSIX UDP sendto/recvfrom hooks successfully installed"];
    } else {
        [ROSSothatLogger logError:@"Failed to install POSIX socket hooks (error %d)", hookRes];
    }

    // 2. Install POSIX connect hook for discovery HTTPS redirection
    uint16_t httpsPort = (uint16_t)(config.discoveryHttpsPort > 0 ? config.discoveryHttpsPort : 50443);
    int connRes = rossothat_install_connect_hook([config.serverHost UTF8String], httpsPort);
    if (connRes == 0) {
        [ROSSothatLogger logInfo:@"POSIX connect hook installed: 172.65.54.209:443 -> %@:%u",
         config.serverHost, httpsPort];
    } else {
        [ROSSothatLogger logError:@"Failed to install POSIX connect hook (error %d)", connRes];
    }

    // 3. Swizzle NetEase UniSDK NtSdkBase::ntLogin
    Class ntSdkClass = objc_getClass("NtSdkBase");
    if (ntSdkClass) {
        SEL loginSel = sel_registerName("ntLogin");
        Method loginMethod = class_getInstanceMethod(ntSdkClass, loginSel);
        if (loginMethod) {
            orig_ntLogin = (void (*)(id, SEL))method_getImplementation(loginMethod);
            method_setImplementation(loginMethod, (IMP)sothat_swizzled_ntLogin);
            [ROSSothatLogger logInfo:@"Successfully swizzled NtSdkBase::ntLogin()"];
        } else {
            [ROSSothatLogger logWarning:@"NtSdkBase found, but ntLogin selector not present"];
        }
    } else {
        [ROSSothatLogger logInfo:@"NtSdkBase class not yet loaded; runtime dynamic swizzling armed"];
    }
}

void rossothat_hook_shutdown(void) {
    [ROSSothatLogger logInfo:@"ROS Sothatt hook shutting down"];
    rossothat_clear_session_key();
}

// Dyld initialization constructor (called automatically at library load)
__attribute__((constructor))
static void rossothat_entry(void) {
    rossothat_hook_initialize();
}
