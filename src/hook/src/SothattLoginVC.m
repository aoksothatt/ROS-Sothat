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

@interface SothattLoginVC () <UITextFieldDelegate>

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

- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = [UIColor colorWithWhite:0.08 alpha:0.95];
    self.modalPresentationStyle = UIModalPresentationFullScreen;

    _authClient = [[ROSSothatAuthClient alloc] initWithConfig:self.config];

    [self setupUI];
}

- (void)setupUI {
    CGFloat w = self.view.bounds.size.width;
    CGFloat h = self.view.bounds.size.height;
    CGFloat boxW = 340;
    CGFloat boxX = (w - boxW) / 2.0;

    // Brand Title
    UILabel *titleLabel = [[UILabel alloc] initWithFrame:CGRectMake(boxX, h * 0.18, boxW, 40)];
    titleLabel.text = @"ROS SOTHATT";
    titleLabel.textColor = [UIColor colorWithRed:1.0 green:0.8 blue:0.0 alpha:1.0]; // Gold
    titleLabel.font = [UIFont boldSystemFontOfSize:28];
    titleLabel.textAlignment = NSTextAlignmentCenter;
    [self.view addSubview:titleLabel];

    // Subtitle
    UILabel *subLabel = [[UILabel alloc] initWithFrame:CGRectMake(boxX, h * 0.18 + 42, boxW, 20)];
    subLabel.text = @"Private Server Client Integration";
    subLabel.textColor = [UIColor lightGrayColor];
    subLabel.font = [UIFont systemFontOfSize:14];
    subLabel.textAlignment = NSTextAlignmentCenter;
    [self.view addSubview:subLabel];

    // Username Field
    _usernameField = [[UITextField alloc] initWithFrame:CGRectMake(boxX, h * 0.35, boxW, 44)];
    _usernameField.placeholder = @"Account Username";
    _usernameField.backgroundColor = [UIColor colorWithWhite:0.18 alpha:1.0];
    _usernameField.textColor = [UIColor whiteColor];
    _usernameField.layer.cornerRadius = 6.0;
    _usernameField.autocapitalizationType = UITextAutocapitalizationTypeNone;
    _usernameField.autocorrectionType = UITextAutocorrectionTypeNo;
    _usernameField.leftView = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 12, 44)];
    _usernameField.leftViewMode = UITextFieldViewModeAlways;
    [self.view addSubview:_usernameField];

    // Password Field
    _passwordField = [[UITextField alloc] initWithFrame:CGRectMake(boxX, h * 0.35 + 56, boxW, 44)];
    _passwordField.placeholder = @"Password";
    _passwordField.backgroundColor = [UIColor colorWithWhite:0.18 alpha:1.0];
    _passwordField.textColor = [UIColor whiteColor];
    _passwordField.layer.cornerRadius = 6.0;
    _passwordField.secureTextEntry = YES;
    _passwordField.leftView = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 12, 44)];
    _passwordField.leftViewMode = UITextFieldViewModeAlways;
    [self.view addSubview:_passwordField];

    // DEPLOY Button
    _deployButton = [UIButton buttonWithType:UIButtonTypeSystem];
    _deployButton.frame = CGRectMake(boxX, h * 0.35 + 120, boxW, 48);
    [_deployButton setTitle:@"DEPLOY / CONNECT" forState:UIControlStateNormal];
    [_deployButton setTitleColor:[UIColor blackColor] forState:UIControlStateNormal];
    _deployButton.backgroundColor = [UIColor colorWithRed:1.0 green:0.8 blue:0.0 alpha:1.0];
    _deployButton.titleLabel.font = [UIFont boldSystemFontOfSize:16];
    _deployButton.layer.cornerRadius = 6.0;
    [_deployButton addTarget:self action:@selector(handleDeploy) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:_deployButton];

    // Settings (Server Config) Button
    _settingsButton = [UIButton buttonWithType:UIButtonTypeSystem];
    _settingsButton.frame = CGRectMake(boxX, h * 0.35 + 180, boxW, 36);
    [_settingsButton setTitle:[NSString stringWithFormat:@"Server: %@", self.config.serverHost] forState:UIControlStateNormal];
    [_settingsButton setTitleColor:[UIColor lightGrayColor] forState:UIControlStateNormal];
    _settingsButton.titleLabel.font = [UIFont systemFontOfSize:13];
    [_settingsButton addTarget:self action:@selector(handleSettings) forControlEvents:UIControlEventTouchUpInside];
    [self.view addSubview:_settingsButton];

    // Spinner
    _spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleLarge];
    _spinner.center = CGPointMake(w / 2.0, h * 0.65);
    _spinner.hidesWhenStopped = YES;
    [self.view addSubview:_spinner];

    // Status Label
    _statusLabel = [[UILabel alloc] initWithFrame:CGRectMake(boxX, h * 0.65 + 30, boxW, 25)];
    _statusLabel.textColor = [UIColor yellowColor];
    _statusLabel.font = [UIFont systemFontOfSize:13];
    _statusLabel.textAlignment = NSTextAlignmentCenter;
    [self.view addSubview:_statusLabel];
}

- (void)handleDeploy {
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
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Server Configuration"
                                                                   message:@"Configure private ROS Sothatt backend IP address."
                                                            preferredStyle:UIAlertControllerStyleAlert];

    [alert addTextFieldWithConfigurationHandler:^(UITextField *textField) {
        textField.placeholder = @"Server IPv4 (e.g. 192.168.1.13)";
        textField.text = self.config.serverHost;
        textField.keyboardType = UIKeyboardTypeNumbersAndPunctuation;
    }];

    __weak typeof(self) weakSelf = self;
    UIAlertAction *saveAction = [UIAlertAction actionWithTitle:@"Save & Reload" style:UIAlertActionStyleDefault handler:^(UIAlertAction *action) {
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
