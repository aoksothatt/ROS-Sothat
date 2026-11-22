//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: error_handler.m
//
// Purpose: Safe UI alert coordinator translating network/auth failures into non-crashing dialogs.
//

#import "error_handler.h"
#import "logging_manager.h"

@implementation ROSSothatErrorHandler

+ (UIViewController *)topViewController {
    UIViewController *root = [UIApplication sharedApplication].keyWindow.rootViewController;
    while (root.presentedViewController) {
        root = root.presentedViewController;
    }
    return root;
}

+ (void)showAlertWithTitle:(NSString *)title
                   message:(NSString *)message
            fromController:(nullable UIViewController *)presenter {
    dispatch_async(dispatch_get_main_queue(), ^{
        UIViewController *target = presenter ?: [self topViewController];
        if (!target) {
            [ROSSothatLogger logError:@"Unable to present alert: No active view controller."];
            return;
        }

        UIAlertController *alert = [UIAlertController alertControllerWithTitle:title
                                                                       message:message
                                                                preferredStyle:UIAlertControllerStyleAlert];
        UIAlertAction *okAction = [UIAlertAction actionWithTitle:@"OK"
                                                           style:UIAlertActionStyleDefault
                                                         handler:nil];
        [alert addAction:okAction];
        [target presentViewController:alert animated:YES completion:nil];
    });
}

+ (void)showErrorAlertWithMessage:(NSString *)message {
    [self showAlertWithTitle:@"ROS Sothatt" message:message fromController:nil];
}

@end
