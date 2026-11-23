//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: SothattLoginVC.m
//
// Purpose: Native UIKit login dialog providing private account authentication and server IP configuration.
//

#import "SothattLoginVC.h"
#import "auth_client.h"
#import "error_handler.h"
#import "logging_manager.h"
#import "baseapp_hook.h"

@interface SothattLoginVC () <UITextFieldDelegate>

@property (nonatomic, strong) UIScrollView *scrollView;
@property (nonatomic, strong) UIView *contentView;
@property (nonatomic, strong) UILabel *titleLabel;
@property (nonatomic, strong) UILabel *subLabel;
@property (nonatomic, strong) UITextField *usernameField;
@property (nonatomic, strong) UITextField *passwordField;
@property (nonatomic, strong) UIButton *deployButton;
@property (nonatomic, strong) UIButton *settingsButton;
@property (nonatomic, strong) UIActivityIndicatorView *spinner;
@property (nonatomic, strong) UILabel *statusLabel;
@property (nonatomic, strong) ROSSothatAuthClient *authClient;

@end

@implementation SothattLoginVC

+ (instancetype)viewControllerWithConfig:(ROSSothatConfig *)config {
    SothattLoginVC *vc = [[SothattLoginVC alloc] init];
    vc.config = config ?: [ROSSothatConfig defaultConfig];
    return vc;
}

- (void)dealloc {
    [[NSNotificationCenter defaultCenter] removeObserver:self];
}

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = [UIColor colorWithWhite:0.08 alpha:0.95];
    self.modalPresentationStyle = UIModalPresentationFullScreen;

    _authClient = [[ROSSothatAuthClient alloc] initWithConfig:self.config];

    [self setupUI];
    [self.view endEditing:YES];
}

- (void)viewWillAppear:(BOOL)animated {
    [super viewWillAppear:animated];
    [self.view endEditing:YES];

    [[NSNotificationCenter defaultCenter] addObserver:self
                                             selector:@selector(keyboardWillShow:)
                                                 name:UIKeyboardWillShowNotification
                                               object:nil];
    [[NSNotificationCenter defaultCenter] addObserver:self
                                             selector:@selector(keyboardWillHide:)
                                                 name:UIKeyboardWillHideNotification
                                               object:nil];
}

- (void)viewDidAppear:(BOOL)animated {
    [super viewDidAppear:animated];
    [self.view endEditing:YES];
}

- (void)viewWillDisappear:(BOOL)animated {
    [super viewWillDisappear:animated];
    [self.view endEditing:YES];

    [[NSNotificationCenter defaultCenter] removeObserver:self
                                                    name:UIKeyboardWillShowNotification
                                                  object:nil];
    [[NSNotificationCenter defaultCenter] removeObserver:self
                                                    name:UIKeyboardWillHideNotification
                                                  object:nil];
}

- (void)setupUI {
    // Scroll View for landscape keyboard avoidance
    _scrollView = [[UIScrollView alloc] initWithFrame:self.view.bounds];
    _scrollView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    _scrollView.alwaysBounceVertical = YES;
    _scrollView.showsVerticalScrollIndicator = YES;
    _scrollView.showsHorizontalScrollIndicator = NO;
    _scrollView.keyboardDismissMode = UIScrollViewKeyboardDismissModeInteractive;
    if (@available(iOS 11.0, *)) {
        _scrollView.contentInsetAdjustmentBehavior = UIScrollViewContentInsetAdjustmentNever;
    }

    // Tap outside text fields to dismiss keyboard without canceling button taps
    UITapGestureRecognizer *tap = [[UITapGestureRecognizer alloc] initWithTarget:self action:@selector(dismissKeyboard)];
    tap.cancelsTouchesInView = NO;
    [_scrollView addGestureRecognizer:tap];
    [self.view addSubview:_scrollView];

    // Content container view
    _contentView = [[UIView alloc] initWithFrame:self.view.bounds];
    [_scrollView addSubview:_contentView];

    // Brand Title
    _titleLabel = [[UILabel alloc] init];
    _titleLabel.text = @"ROS SOTHATT";
    _titleLabel.textColor = [UIColor colorWithRed:1.0 green:0.8 blue:0.0 alpha:1.0]; // Gold
    _titleLabel.font = [UIFont boldSystemFontOfSize:26];
    _titleLabel.textAlignment = NSTextAlignmentCenter;
    [_contentView addSubview:_titleLabel];

    // Subtitle
    _subLabel = [[UILabel alloc] init];
    _subLabel.text = @"Private Server Client Integration";
    _subLabel.textColor = [UIColor lightGrayColor];
    _subLabel.font = [UIFont systemFontOfSize:13];
    _subLabel.textAlignment = NSTextAlignmentCenter;
    [_contentView addSubview:_subLabel];

    // Username Field
    _usernameField = [[UITextField alloc] init];
    _usernameField.delegate = self;
    _usernameField.placeholder = @"Account Username";
    _usernameField.backgroundColor = [UIColor colorWithWhite:0.18 alpha:1.0];
    _usernameField.textColor = [UIColor whiteColor];
    _usernameField.layer.cornerRadius = 6.0;
    _usernameField.autocapitalizationType = UITextAutocapitalizationTypeNone;
    _usernameField.autocorrectionType = UITextAutocorrectionTypeNo;
    _usernameField.returnKeyType = UIReturnKeyNext;
    _usernameField.clearButtonMode = UITextFieldViewModeWhileEditing;
    _usernameField.leftView = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 12, 42)];
    _usernameField.leftViewMode = UITextFieldViewModeAlways;
    [_contentView addSubview:_usernameField];

    // Password Field
    _passwordField = [[UITextField alloc] init];
    _passwordField.delegate = self;
    _passwordField.placeholder = @"Password";
    _passwordField.backgroundColor = [UIColor colorWithWhite:0.18 alpha:1.0];
    _passwordField.textColor = [UIColor whiteColor];
    _passwordField.layer.cornerRadius = 6.0;
    _passwordField.secureTextEntry = YES;
    _passwordField.autocapitalizationType = UITextAutocapitalizationTypeNone;
    _passwordField.autocorrectionType = UITextAutocorrectionTypeNo;
    _passwordField.returnKeyType = UIReturnKeyDone;
    _passwordField.clearButtonMode = UITextFieldViewModeWhileEditing;
    _passwordField.leftView = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 12, 42)];
    _passwordField.leftViewMode = UITextFieldViewModeAlways;
    [_contentView addSubview:_passwordField];

    // DEPLOY Button
    _deployButton = [UIButton buttonWithType:UIButtonTypeSystem];
    [_deployButton setTitle:@"DEPLOY / CONNECT" forState:UIControlStateNormal];
    [_deployButton setTitleColor:[UIColor blackColor] forState:UIControlStateNormal];
    _deployButton.backgroundColor = [UIColor colorWithRed:1.0 green:0.8 blue:0.0 alpha:1.0];
    _deployButton.titleLabel.font = [UIFont boldSystemFontOfSize:16];
    _deployButton.layer.cornerRadius = 6.0;
    [_deployButton addTarget:self action:@selector(handleDeploy) forControlEvents:UIControlEventTouchUpInside];
    [_contentView addSubview:_deployButton];

    // Settings (Server Config) Button
    _settingsButton = [UIButton buttonWithType:UIButtonTypeSystem];
    [_settingsButton setTitle:[NSString stringWithFormat:@"Server: %@", self.config.serverHost] forState:UIControlStateNormal];
    [_settingsButton setTitleColor:[UIColor lightGrayColor] forState:UIControlStateNormal];
    _settingsButton.titleLabel.font = [UIFont systemFontOfSize:13];
    [_settingsButton addTarget:self action:@selector(handleSettings) forControlEvents:UIControlEventTouchUpInside];
    [_contentView addSubview:_settingsButton];

    // Spinner
    _spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleLarge];
    _spinner.hidesWhenStopped = YES;
    [_contentView addSubview:_spinner];

    // Status Label
    _statusLabel = [[UILabel alloc] init];
    _statusLabel.textColor = [UIColor yellowColor];
    _statusLabel.font = [UIFont systemFontOfSize:13];
    _statusLabel.textAlignment = NSTextAlignmentCenter;
    [_contentView addSubview:_statusLabel];
}

- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];

    CGFloat viewW = self.view.bounds.size.width;
    CGFloat viewH = self.view.bounds.size.height;
    if (viewW <= 0 || viewH <= 0) return;

    self.scrollView.frame = self.view.bounds;

    CGFloat boxW = 340.0;
    if (viewW < boxW + 40.0) {
        boxW = viewW - 40.0;
    }
    CGFloat boxX = (viewW - boxW) / 2.0;

    // Component dimensions and inter-element spacing
    CGFloat titleH = 34.0;
    CGFloat gapTitleSub = 8.0;
    CGFloat subH = 18.0;
    CGFloat gapSubUser = 14.0;
    CGFloat fieldH = 42.0;
    CGFloat gapUserPass = 10.0;
    CGFloat gapPassDeploy = 14.0;
    CGFloat deployH = 46.0;
    CGFloat gapDeploySettings = 10.0;
    CGFloat settingsH = 32.0;
    CGFloat gapSettingsStatus = 8.0;
    CGFloat statusH = 20.0;
    // Accurately calculate actual vertical stack height (298 pt visual height)
    CGFloat stackH = titleH + gapTitleSub + subH + gapSubUser +
                     fieldH + gapUserPass + fieldH + gapPassDeploy +
                     deployH + gapDeploySettings + settingsH + gapSettingsStatus + statusH;

    // Vertically center form when keyboard is hidden
    CGFloat topMargin = (viewH > stackH) ? (viewH - stackH) / 2.0 : 16.0;
    if (topMargin < 16.0) {
        topMargin = 16.0;
    }
    CGFloat bottomPadding = topMargin;
    CGFloat contentTotalH = stackH + topMargin + bottomPadding;

    CGFloat curY = topMargin;

    // Title
    self.titleLabel.frame = CGRectMake(boxX, curY, boxW, titleH);
    curY += titleH + gapTitleSub;

    // Subtitle
    self.subLabel.frame = CGRectMake(boxX, curY, boxW, subH);
    curY += subH + gapSubUser;

    // Username Field
    self.usernameField.frame = CGRectMake(boxX, curY, boxW, fieldH);
    curY += fieldH + gapUserPass;

    // Password Field
    self.passwordField.frame = CGRectMake(boxX, curY, boxW, fieldH);
    curY += fieldH + gapPassDeploy;

    // DEPLOY Button
    self.deployButton.frame = CGRectMake(boxX, curY, boxW, deployH);
    curY += deployH + gapDeploySettings;

    // Settings Button
    self.settingsButton.frame = CGRectMake(boxX, curY, boxW, settingsH);
    curY += settingsH + gapSettingsStatus;

    // Status Label
    self.statusLabel.frame = CGRectMake(boxX, curY, boxW, statusH);
    curY += statusH + bottomPadding;

    // Spinner centered over deploy button
    self.spinner.center = CGPointMake(viewW / 2.0, self.deployButton.center.y);

    CGFloat totalContentH = curY;
    if (totalContentH < viewH) {
        totalContentH = viewH;
    }

    self.contentView.frame = CGRectMake(0, 0, viewW, totalContentH);
    self.scrollView.contentSize = CGSizeMake(viewW, totalContentH);
}

- (void)touchesBegan:(NSSet<UITouch *> *)touches withEvent:(UIEvent *)event {
    [super touchesBegan:touches withEvent:event];
    [self.view endEditing:YES];
}

- (void)dismissKeyboard {
    [self.view endEditing:YES];
}

#pragma mark - Keyboard Notifications

- (void)keyboardWillShow:(NSNotification *)notification {
    NSDictionary *userInfo = notification.userInfo;
    CGRect keyboardFrame = [userInfo[UIKeyboardFrameEndUserInfoKey] CGRectValue];
    CGRect convertedFrame = [self.view convertRect:keyboardFrame fromView:nil];
    CGFloat keyboardHeight = self.view.bounds.size.height - convertedFrame.origin.y;
    if (keyboardHeight < 0) {
        keyboardHeight = 0;
    }

    UIEdgeInsets insets = UIEdgeInsetsMake(0, 0, keyboardHeight, 0);
    NSTimeInterval duration = [userInfo[UIKeyboardAnimationDurationUserInfoKey] doubleValue];
    UIViewAnimationOptions curve = [userInfo[UIKeyboardAnimationCurveUserInfoKey] unsignedIntegerValue] << 16;

    [UIView animateWithDuration:duration delay:0 options:curve animations:^{
        self.scrollView.contentInset = insets;
        self.scrollView.scrollIndicatorInsets = insets;
    } completion:nil];

    // Scroll active field or deploy/status cluster into view
    CGRect targetRect = CGRectUnion(self.deployButton.frame, self.statusLabel.frame);
    if (self.usernameField.isFirstResponder) {
        targetRect = CGRectUnion(self.usernameField.frame, self.passwordField.frame);
    } else if (self.passwordField.isFirstResponder) {
        targetRect = CGRectUnion(self.passwordField.frame, self.deployButton.frame);
    }
    [self.scrollView scrollRectToVisible:targetRect animated:YES];
}

- (void)keyboardWillHide:(NSNotification *)notification {
    NSDictionary *userInfo = notification.userInfo;
    NSTimeInterval duration = [userInfo[UIKeyboardAnimationDurationUserInfoKey] doubleValue];
    UIViewAnimationOptions curve = [userInfo[UIKeyboardAnimationCurveUserInfoKey] unsignedIntegerValue] << 16;

    [UIView animateWithDuration:duration delay:0 options:curve animations:^{
        self.scrollView.contentInset = UIEdgeInsetsZero;
        self.scrollView.scrollIndicatorInsets = UIEdgeInsetsZero;
    } completion:nil];
}

#pragma mark - UITextFieldDelegate

- (BOOL)textFieldShouldReturn:(UITextField *)textField {
    if (textField == self.usernameField) {
        [self.passwordField becomeFirstResponder];
    } else if (textField == self.passwordField) {
        [self.passwordField resignFirstResponder];
        [self handleDeploy];
    }
    return YES;
}

- (void)handleDeploy {
    [self.view endEditing:YES];

    // Prevent duplicate or concurrent in-flight authentication requests
    if (!self.deployButton.enabled) {
        return;
    }

    NSString *user = [self.usernameField.text stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];
    NSString *pass = self.passwordField.text;

    if ([user length] == 0 || [pass length] == 0) {
        [ROSSothatErrorHandler showAlertWithTitle:@"Login Required" message:@"Please enter your username and password." fromController:self];
        return;
    }

    [self.deployButton setEnabled:NO];
    [self.spinner startAnimating];
    self.statusLabel.text = @"Authenticating with ROS Sothatt...";

    // Clear password UI field immediately after capturing value
    self.passwordField.text = @"";

    __weak typeof(self) weakSelf = self;
    [self.authClient loginWithUsername:user password:pass completion:^(BOOL success, uint32_t sessionKey, NSString *errorMessage) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf.spinner stopAnimating];
            [weakSelf.deployButton setEnabled:YES];

            if (success) {
                weakSelf.statusLabel.text = @"Success! Entering game...";
                if (weakSelf.onLoginSuccess) {
                    weakSelf.onLoginSuccess(sessionKey);
                }
                [weakSelf dismissViewControllerAnimated:YES completion:nil];
            } else {
                weakSelf.statusLabel.text = @"";
                [ROSSothatErrorHandler showAlertWithTitle:@"Authentication Failed" message:errorMessage ?: @"Unknown error." fromController:weakSelf];
            }
        });
    }];
}

- (void)handleSettings {
    [self.view endEditing:YES];

    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Server Configuration"
                                                                   message:@"Configure private ROS Sothatt backend IP address."
                                                            preferredStyle:UIAlertControllerStyleAlert];

    [alert addTextFieldWithConfigurationHandler:^(UITextField *textField) {
        textField.placeholder = @"Server IPv4 (e.g. 192.168.1.13)";
        textField.text = self.config.serverHost;
        textField.keyboardType = UIKeyboardTypeNumbersAndPunctuation;
    }];

    __weak typeof(self) weakSelf = self;
    UIAlertAction *saveAction = [UIAlertAction actionWithTitle:@"Save & Reload" style:UIAlertActionStyleDefault handler:^(__unused UIAlertAction *action) {
        NSString *newHost = [alert.textFields.firstObject.text stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];
        if ([newHost length] > 0) {
            NSError *err = nil;
            NSDictionary *dict = @{@"server_host": newHost};
            NSData *data = [NSJSONSerialization dataWithJSONObject:dict options:0 error:nil];
            ROSSothatConfig *newCfg = [ROSSothatConfig configFromJSONData:data error:&err];
            if (newCfg) {
                [ROSSothatConfig saveToDocumentsDirectory:newCfg error:nil];
                weakSelf.config = newCfg;
                weakSelf.authClient = [[ROSSothatAuthClient alloc] initWithConfig:newCfg];
                rossothat_update_target_host([newHost UTF8String]);
                rossothat_probe_local_network([newHost UTF8String]);
                [weakSelf.settingsButton setTitle:[NSString stringWithFormat:@"Server: %@", newHost] forState:UIControlStateNormal];
            } else {
                [ROSSothatErrorHandler showAlertWithTitle:@"Invalid IP" message:@"Please enter a valid private IPv4 address." fromController:weakSelf];
            }
        }
    }];

    UIAlertAction *cancelAction = [UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil];
    [alert addAction:saveAction];
    [alert addAction:cancelAction];

    [self presentViewController:alert animated:YES completion:nil];
}

@end
