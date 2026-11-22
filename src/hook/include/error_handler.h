//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: error_handler.h
//
// Purpose: Safe UI alert coordinator translating network/auth failures into non-crashing dialogs.
//

#ifndef ROSSOTHAT_ERROR_HANDLER_H
#define ROSSOTHAT_ERROR_HANDLER_H

#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN

@interface ROSSothatErrorHandler : NSObject

+ (void)showAlertWithTitle:(NSString *)title
                   message:(NSString *)message
            fromController:(nullable UIViewController *)presenter;

+ (void)showErrorAlertWithMessage:(NSString *)message;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_ERROR_HANDLER_H
