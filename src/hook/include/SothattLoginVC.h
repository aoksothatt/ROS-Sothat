//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Header: SothattLoginVC.h
//
// Purpose: Native UIKit login dialog providing private account authentication and server IP configuration.
//

#ifndef ROSSOTHAT_LOGIN_VC_H
#define ROSSOTHAT_LOGIN_VC_H

#import <UIKit/UIKit.h>
#import "config_manager.h"

NS_ASSUME_NONNULL_BEGIN

typedef void (^ROSSothatLoginSuccessHandler)(uint32_t sessionKey);

@interface SothattLoginVC : UIViewController

@property (nonatomic, strong) ROSSothatConfig *config;
@property (nonatomic, copy, nullable) ROSSothatLoginSuccessHandler onLoginSuccess;

+ (instancetype)viewControllerWithConfig:(ROSSothatConfig *)config;

@end

NS_ASSUME_NONNULL_END

#endif // ROSSOTHAT_LOGIN_VC_H
