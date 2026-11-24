//
// ROS Sothatt — Clean-Room iOS Hook Architecture
// Source: SothattLoginVC.m
//
// Purpose: Cinematic military battle-royale login interface providing compact centered panel,
//          Sign In / Create Account tabs, automatic server discovery, and private backend integration.
//

#import "SothattLoginVC.h"
#import "auth_client.h"
#import "discovery_client.h"
#import "network_client.h"
#import "rossothathook.h"
#import "error_handler.h"
#import "logging_manager.h"
#import "baseapp_hook.h"
#import "session_manager.h"

static NSString *const kRememberMeKey = @"ROSSothatRememberMe";
static NSString *const kSavedUsernameKey = @"ROSSothatSavedUsername";

typedef NS_ENUM(NSInteger, ROSLoginTab) {
    ROSLoginTabSignIn = 0,
    ROSLoginTabCreateAccount = 1
};

@interface SothattLoginVC () <UITextFieldDelegate>

// Background & Overlay
@property (nonatomic, strong) UIImageView *backgroundImageView;
@property (nonatomic, strong) UIView *darkScrimView;

// Scroll & Panel Container
@property (nonatomic, strong) UIScrollView *scrollView;
@property (nonatomic, strong) UIView *panelView;

// Top Quick Action Bar
@property (nonatomic, strong) UIView *topBarView;
@property (nonatomic, strong) UIButton *noticeButton;
@property (nonatomic, strong) UIButton *repairButton;
@property (nonatomic, strong) UIButton *languageButton;
@property (nonatomic, strong) UIButton *logoutButton;

// Panel Header
@property (nonatomic, strong) UILabel *titleLabel;
@property (nonatomic, strong) UILabel *subLabel;

// Tab Selector
@property (nonatomic, strong) UIView *tabBarContainer;
@property (nonatomic, strong) UIButton *signInTabButton;
@property (nonatomic, strong) UIButton *createAccountTabButton;
@property (nonatomic, strong) UIView *tabIndicatorView;
@property (nonatomic, assign) ROSLoginTab activeTab;

// Form Container Views
@property (nonatomic, strong) UIView *signInFormView;
@property (nonatomic, strong) UIView *createAccountFormView;

// Sign In Controls
@property (nonatomic, strong) UITextField *usernameField;
@property (nonatomic, strong) UITextField *passwordField;
@property (nonatomic, strong) UIButton *serverStatusButton;
@property (nonatomic, strong) UIButton *rememberMeButton;
@property (nonatomic, strong) UIButton *forgotPasswordButton;
@property (nonatomic, strong) UIButton *signInButton;
@property (nonatomic, strong) UIButton *deployButton;

// Create Account Controls
@property (nonatomic, strong) UITextField *regUsernameField;
@property (nonatomic, strong) UITextField *regPasswordField;
@property (nonatomic, strong) UITextField *regConfirmPasswordField;
@property (nonatomic, strong) UITextField *regInviteCodeField;
@property (nonatomic, strong) UIButton *createAccountButton;

// Feedback & Loading
@property (nonatomic, strong) UIActivityIndicatorView *spinner;
@property (nonatomic, strong) UILabel *statusLabel;

// Footer
@property (nonatomic, strong) UILabel *footerLabel;
@property (nonatomic, strong) UILabel *versionLabel;

// Logic Clients
@property (nonatomic, strong) ROSSothatAuthClient *authClient;
@property (nonatomic, assign) BOOL rememberMeEnabled;
@property (nonatomic, assign) BOOL isDiscovering;

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
    self.view.backgroundColor = [UIColor blackColor];
    self.modalPresentationStyle = UIModalPresentationFullScreen;

    _authClient = [[ROSSothatAuthClient alloc] initWithConfig:self.config];
    _activeTab = ROSLoginTabSignIn;
    _rememberMeEnabled = [[NSUserDefaults standardUserDefaults] boolForKey:kRememberMeKey];

    [self setupUI];
    [self loadSavedCredentials];
    [self.view endEditing:YES];

    // Trigger automatic background private server discovery
    [self startAutoDiscovery];
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

#pragma mark - UI Setup

- (void)setupUI {
    // 1. Cinematic Background Image (from existing ROS game bundle assets)
    _backgroundImageView = [[UIImageView alloc] initWithFrame:self.view.bounds];
    _backgroundImageView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    _backgroundImageView.contentMode = UIViewContentModeScaleAspectFill;
    _backgroundImageView.clipsToBounds = YES;

    UIImage *bgImage = [UIImage imageNamed:@"2436x1125"] ?:
                       [UIImage imageNamed:@"LaunchImage-1100-Landscape-2436h"] ?:
                       [UIImage imageNamed:@"2688x1242"] ?:
                       [UIImage imageNamed:@"LaunchImage"];
    if (bgImage) {
        _backgroundImageView.image = bgImage;
    } else {
        _backgroundImageView.backgroundColor = [UIColor colorWithRed:0.06 green:0.07 blue:0.09 alpha:1.0];
    }
    [self.view addSubview:_backgroundImageView];

    // 2. Dark Cinematic Battlefield Scrim Overlay
    _darkScrimView = [[UIView alloc] initWithFrame:self.view.bounds];
    _darkScrimView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    _darkScrimView.backgroundColor = [UIColor colorWithWhite:0.0 alpha:0.58];
    [self.view addSubview:_darkScrimView];

    // 3. Scroll View for Keyboard Avoidance
    _scrollView = [[UIScrollView alloc] initWithFrame:self.view.bounds];
    _scrollView.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    _scrollView.alwaysBounceVertical = YES;
    _scrollView.showsVerticalScrollIndicator = NO;
    _scrollView.showsHorizontalScrollIndicator = NO;
    _scrollView.keyboardDismissMode = UIScrollViewKeyboardDismissModeInteractive;
    if (@available(iOS 11.0, *)) {
        _scrollView.contentInsetAdjustmentBehavior = UIScrollViewContentInsetAdjustmentNever;
    }

    UITapGestureRecognizer *tap = [[UITapGestureRecognizer alloc] initWithTarget:self action:@selector(dismissKeyboard)];
    tap.cancelsTouchesInView = NO;
    [_scrollView addGestureRecognizer:tap];
    [self.view addSubview:_scrollView];

    // 4. Top Quick Action Bar (Notice, Repair, Language, Log Out)
    [self setupTopBar];

    // 5. Compact Centered Login Panel
    [self setupCenteredPanel];
}

- (void)setupTopBar {
    _topBarView = [[UIView alloc] init];
    _topBarView.backgroundColor = [UIColor clearColor];
    [_scrollView addSubview:_topBarView];

    _noticeButton = [self createTopBarButtonWithTitle:@"Notice" action:@selector(handleNotice)];
    _repairButton = [self createTopBarButtonWithTitle:@"Repair" action:@selector(handleRepair)];
    _languageButton = [self createTopBarButtonWithTitle:@"EN" action:@selector(handleLanguage)];
    _logoutButton = [self createTopBarButtonWithTitle:@"Log Out" action:@selector(handleLogout)];

    [_topBarView addSubview:_noticeButton];
    [_topBarView addSubview:_repairButton];
    [_topBarView addSubview:_languageButton];
    [_topBarView addSubview:_logoutButton];
}

- (UIButton *)createTopBarButtonWithTitle:(NSString *)title action:(SEL)action {
    UIButton *btn = [UIButton buttonWithType:UIButtonTypeSystem];
    [btn setTitle:title forState:UIControlStateNormal];
    [btn setTitleColor:[UIColor colorWithWhite:0.85 alpha:1.0] forState:UIControlStateNormal];
    btn.backgroundColor = [UIColor colorWithRed:0.12 green:0.14 blue:0.18 alpha:0.85];
    btn.layer.borderColor = [UIColor colorWithRed:0.75 green:0.62 blue:0.25 alpha:0.6].CGColor;
    btn.layer.borderWidth = 0.8;
    btn.layer.cornerRadius = 5.0;
    btn.titleLabel.font = [UIFont boldSystemFontOfSize:11];
    [btn addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];
    return btn;
}

- (void)setupCenteredPanel {
    // Compact Centered Charcoal Panel with Thin Gold Border
    _panelView = [[UIView alloc] init];
    _panelView.backgroundColor = [UIColor colorWithRed:0.08 green:0.09 blue:0.12 alpha:0.92];
    _panelView.layer.borderColor = [UIColor colorWithRed:0.85 green:0.70 blue:0.22 alpha:0.90].CGColor; // Gold border
    _panelView.layer.borderWidth = 1.5;
    _panelView.layer.cornerRadius = 10.0;
    _panelView.layer.shadowColor = [UIColor blackColor].CGColor;
    _panelView.layer.shadowOffset = CGSizeMake(0, 4);
    _panelView.layer.shadowOpacity = 0.5;
    _panelView.layer.shadowRadius = 8.0;
    [_scrollView addSubview:_panelView];

    // Header Title: ROS SOTHATT
    _titleLabel = [[UILabel alloc] init];
    _titleLabel.text = @"ROS SOTHATT";
    _titleLabel.textColor = [UIColor colorWithRed:1.0 green:0.82 blue:0.25 alpha:1.0]; // Bright Gold
    _titleLabel.font = [UIFont boldSystemFontOfSize:22];
    _titleLabel.textAlignment = NSTextAlignmentCenter;
    [_panelView addSubview:_titleLabel];

    // Subtitle: PRIVATE SERVER
    _subLabel = [[UILabel alloc] init];
    _subLabel.text = @"PRIVATE SERVER — TEST USE ONLY";
    _subLabel.textColor = [UIColor colorWithRed:0.75 green:0.75 blue:0.80 alpha:0.85];
    _subLabel.font = [UIFont systemFontOfSize:10 weight:UIFontWeightMedium];
    _subLabel.textAlignment = NSTextAlignmentCenter;
    [_panelView addSubview:_subLabel];

    // Tab Bar Container
    _tabBarContainer = [[UIView alloc] init];
    _tabBarContainer.backgroundColor = [UIColor colorWithWhite:0.05 alpha:0.8];
    _tabBarContainer.layer.cornerRadius = 6.0;
    [_panelView addSubview:_tabBarContainer];

    // Sign In Tab Button
    _signInTabButton = [UIButton buttonWithType:UIButtonTypeCustom];
    [_signInTabButton setTitle:@"Sign In" forState:UIControlStateNormal];
    [_signInTabButton setTitleColor:[UIColor colorWithRed:1.0 green:0.82 blue:0.25 alpha:1.0] forState:UIControlStateNormal];
    _signInTabButton.titleLabel.font = [UIFont boldSystemFontOfSize:14];
    [_signInTabButton addTarget:self action:@selector(selectSignInTab) forControlEvents:UIControlEventTouchUpInside];
    [_tabBarContainer addSubview:_signInTabButton];

    // Create Account Tab Button
    _createAccountTabButton = [UIButton buttonWithType:UIButtonTypeCustom];
    [_createAccountTabButton setTitle:@"Create Account" forState:UIControlStateNormal];
    [_createAccountTabButton setTitleColor:[UIColor lightGrayColor] forState:UIControlStateNormal];
    _createAccountTabButton.titleLabel.font = [UIFont systemFontOfSize:14];
    [_createAccountTabButton addTarget:self action:@selector(selectCreateAccountTab) forControlEvents:UIControlEventTouchUpInside];
    [_tabBarContainer addSubview:_createAccountTabButton];

    // Gold Tab Indicator
    _tabIndicatorView = [[UIView alloc] init];
    _tabIndicatorView.backgroundColor = [UIColor colorWithRed:1.0 green:0.82 blue:0.25 alpha:1.0];
    [_tabBarContainer addSubview:_tabIndicatorView];

    // Form Container Views
    _signInFormView = [[UIView alloc] init];
    [_panelView addSubview:_signInFormView];

    _createAccountFormView = [[UIView alloc] init];
    _createAccountFormView.hidden = YES;
    [_panelView addSubview:_createAccountFormView];

    // Setup Sign In Fields
    [self setupSignInForm];

    // Setup Create Account Fields
    [self setupCreateAccountForm];

    // Status Feedback Label
    _statusLabel = [[UILabel alloc] init];
    _statusLabel.textColor = [UIColor colorWithRed:1.0 green:0.85 blue:0.3 alpha:1.0];
    _statusLabel.font = [UIFont systemFontOfSize:12];
    _statusLabel.textAlignment = NSTextAlignmentCenter;
    _statusLabel.numberOfLines = 2;
    [_panelView addSubview:_statusLabel];

    // Activity Spinner
    _spinner = [[UIActivityIndicatorView alloc] initWithActivityIndicatorStyle:UIActivityIndicatorViewStyleMedium];
    _spinner.color = [UIColor colorWithRed:1.0 green:0.82 blue:0.25 alpha:1.0];
    _spinner.hidesWhenStopped = YES;
    [_panelView addSubview:_spinner];

    // Footer
    _footerLabel = [[UILabel alloc] init];
    _footerLabel.text = @"PRIVATE SERVER — FOR TEST USE ONLY";
    _footerLabel.textColor = [UIColor colorWithWhite:0.5 alpha:1.0];
    _footerLabel.font = [UIFont systemFontOfSize:9];
    _footerLabel.textAlignment = NSTextAlignmentCenter;
    [_panelView addSubview:_footerLabel];

    _versionLabel = [[UILabel alloc] init];
    _versionLabel.text = @"ROS Sothatt iOS v7.0 (Phone Hotspot & LAN)";
    _versionLabel.textColor = [UIColor colorWithWhite:0.4 alpha:1.0];
    _versionLabel.font = [UIFont systemFontOfSize:8];
    _versionLabel.textAlignment = NSTextAlignmentCenter;
    [_panelView addSubview:_versionLabel];
}

- (void)setupSignInForm {
    // Username Field
    _usernameField = [self createStyledTextFieldWithPlaceholder:@"Account Username"];
    _usernameField.delegate = self;
    _usernameField.returnKeyType = UIReturnKeyNext;
    [_signInFormView addSubview:_usernameField];

    // Password Field
    _passwordField = [self createStyledTextFieldWithPlaceholder:@"Password"];
    _passwordField.delegate = self;
    _passwordField.secureTextEntry = YES;
    _passwordField.returnKeyType = UIReturnKeyDone;
    [_signInFormView addSubview:_passwordField];

    // Server Selection & Status Button
    _serverStatusButton = [UIButton buttonWithType:UIButtonTypeSystem];
    NSString *host = self.config.serverHost ?: @"172.20.10.2";
    [_serverStatusButton setTitle:[NSString stringWithFormat:@"● Server: %@:%ld (Online)", host, (long)self.config.authPort] forState:UIControlStateNormal];
    [_serverStatusButton setTitleColor:[UIColor colorWithRed:0.4 green:0.85 blue:0.4 alpha:1.0] forState:UIControlStateNormal];
    _serverStatusButton.titleLabel.font = [UIFont systemFontOfSize:11];
    _serverStatusButton.backgroundColor = [UIColor colorWithWhite:0.12 alpha:0.6];
    _serverStatusButton.layer.cornerRadius = 4.0;
    [_serverStatusButton addTarget:self action:@selector(handleSettings) forControlEvents:UIControlEventTouchUpInside];
    [_signInFormView addSubview:_serverStatusButton];

    // Remember Me Checkbox Button
    _rememberMeButton = [UIButton buttonWithType:UIButtonTypeCustom];
    [self updateRememberMeButtonAppearance];
    [_rememberMeButton addTarget:self action:@selector(toggleRememberMe) forControlEvents:UIControlEventTouchUpInside];
    [_signInFormView addSubview:_rememberMeButton];

    // Forgot Password Button
    _forgotPasswordButton = [UIButton buttonWithType:UIButtonTypeSystem];
    [_forgotPasswordButton setTitle:@"Forgot Password?" forState:UIControlStateNormal];
    [_forgotPasswordButton setTitleColor:[UIColor colorWithWhite:0.7 alpha:1.0] forState:UIControlStateNormal];
    _forgotPasswordButton.titleLabel.font = [UIFont systemFontOfSize:11];
    [_forgotPasswordButton addTarget:self action:@selector(handleForgotPassword) forControlEvents:UIControlEventTouchUpInside];
    [_signInFormView addSubview:_forgotPasswordButton];

    // Prominent SIGN IN Button
    _signInButton = [UIButton buttonWithType:UIButtonTypeSystem];
    _deployButton = _signInButton;
    [_signInButton setTitle:@"SIGN IN" forState:UIControlStateNormal];
    [_signInButton setTitleColor:[UIColor blackColor] forState:UIControlStateNormal];
    _signInButton.backgroundColor = [UIColor colorWithRed:0.95 green:0.78 blue:0.22 alpha:1.0]; // Rich Gold
    _signInButton.titleLabel.font = [UIFont boldSystemFontOfSize:15];
    _signInButton.layer.cornerRadius = 6.0;
    [_signInButton addTarget:self action:@selector(handleDeploy) forControlEvents:UIControlEventTouchUpInside];
    [_signInFormView addSubview:_signInButton];
}

- (void)setupCreateAccountForm {
    _regUsernameField = [self createStyledTextFieldWithPlaceholder:@"New Username (3-32 chars)"];
    _regUsernameField.returnKeyType = UIReturnKeyNext;
    [_createAccountFormView addSubview:_regUsernameField];

    _regPasswordField = [self createStyledTextFieldWithPlaceholder:@"Password (min 4 chars)"];
    _regPasswordField.secureTextEntry = YES;
    _regPasswordField.returnKeyType = UIReturnKeyNext;
    [_createAccountFormView addSubview:_regPasswordField];

    _regConfirmPasswordField = [self createStyledTextFieldWithPlaceholder:@"Confirm Password"];
    _regConfirmPasswordField.secureTextEntry = YES;
    _regConfirmPasswordField.returnKeyType = UIReturnKeyNext;
    [_createAccountFormView addSubview:_regConfirmPasswordField];

    _regInviteCodeField = [self createStyledTextFieldWithPlaceholder:@"Invite Code (optional, e.g. SOTHATT2026)"];
    _regInviteCodeField.returnKeyType = UIReturnKeyDone;
    [_createAccountFormView addSubview:_regInviteCodeField];

    _createAccountButton = [UIButton buttonWithType:UIButtonTypeSystem];
    [_createAccountButton setTitle:@"CREATE ACCOUNT" forState:UIControlStateNormal];
    [_createAccountButton setTitleColor:[UIColor blackColor] forState:UIControlStateNormal];
    _createAccountButton.backgroundColor = [UIColor colorWithRed:0.95 green:0.78 blue:0.22 alpha:1.0];
    _createAccountButton.titleLabel.font = [UIFont boldSystemFontOfSize:15];
    _createAccountButton.layer.cornerRadius = 6.0;
    [_createAccountButton addTarget:self action:@selector(handleCreateAccount) forControlEvents:UIControlEventTouchUpInside];
    [_createAccountFormView addSubview:_createAccountButton];
}

- (UITextField *)createStyledTextFieldWithPlaceholder:(NSString *)placeholder {
    UITextField *field = [[UITextField alloc] init];
    field.delegate = self;
    field.placeholder = placeholder;
    field.backgroundColor = [UIColor colorWithWhite:0.14 alpha:1.0];
    field.textColor = [UIColor whiteColor];
    field.layer.cornerRadius = 5.0;
    field.layer.borderColor = [UIColor colorWithWhite:0.25 alpha:0.8].CGColor;
    field.layer.borderWidth = 0.8;
    field.autocapitalizationType = UITextAutocapitalizationTypeNone;
    field.autocorrectionType = UITextAutocorrectionTypeNo;
    field.clearButtonMode = UITextFieldViewModeWhileEditing;
    field.leftView = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 10, 36)];
    field.leftViewMode = UITextFieldViewModeAlways;
    field.font = [UIFont systemFontOfSize:13];
    return field;
}

#pragma mark - Layout

- (void)viewDidLayoutSubviews {
    [super viewDidLayoutSubviews];

    CGFloat viewW = self.view.bounds.size.width;
    CGFloat viewH = self.view.bounds.size.height;
    if (viewW <= 0 || viewH <= 0) return;

    self.scrollView.frame = self.view.bounds;
    self.backgroundImageView.frame = self.view.bounds;
    self.darkScrimView.frame = self.view.bounds;

    UIEdgeInsets insets = UIEdgeInsetsZero;
    if (@available(iOS 11.0, *)) {
        insets = self.view.safeAreaInsets;
    }

    // Top Action Bar Layout (Right-aligned pills)
    CGFloat topBarH = 30.0;
    CGFloat topBarY = insets.top + 8.0;
    CGFloat pillW = 60.0;
    CGFloat pillGap = 6.0;
    CGFloat topBarTotalW = (pillW * 4) + (pillGap * 3);
    CGFloat topBarX = viewW - insets.right - topBarTotalW - 12.0;
    if (topBarX < insets.left + 8.0) topBarX = insets.left + 8.0;

    self.topBarView.frame = CGRectMake(topBarX, topBarY, topBarTotalW, topBarH);
    self.noticeButton.frame = CGRectMake(0, 0, pillW, topBarH);
    self.repairButton.frame = CGRectMake(pillW + pillGap, 0, pillW, topBarH);
    self.languageButton.frame = CGRectMake((pillW + pillGap) * 2, 0, pillW, topBarH);
    self.logoutButton.frame = CGRectMake((pillW + pillGap) * 3, 0, pillW, topBarH);

    // Compact Centered Panel Dimensions
    CGFloat panelW = 340.0;
    if (viewW < panelW + 24.0) {
        panelW = viewW - 24.0;
    }
    CGFloat panelH = 390.0;
    CGFloat stackH = panelH;
    (void)stackH;
    CGFloat panelX = (viewW - panelW) / 2.0;
    CGFloat panelY = (viewH - panelH) / 2.0;
    if (panelY < topBarY + topBarH + 8.0) {
        panelY = topBarY + topBarH + 8.0;
    }

    self.panelView.frame = CGRectMake(panelX, panelY, panelW, panelH);

    // Panel Elements
    CGFloat pad = 16.0;
    CGFloat contentW = panelW - (pad * 2);
    CGFloat curY = 14.0;

    // Header Title & Subtitle
    self.titleLabel.frame = CGRectMake(pad, curY, contentW, 26.0);
    curY += 26.0 + 2.0;

    self.subLabel.frame = CGRectMake(pad, curY, contentW, 14.0);
    curY += 14.0 + 10.0;

    // Tab Bar
    CGFloat tabH = 32.0;
    self.tabBarContainer.frame = CGRectMake(pad, curY, contentW, tabH);
    CGFloat halfTabW = contentW / 2.0;
    self.signInTabButton.frame = CGRectMake(0, 0, halfTabW, tabH);
    self.createAccountTabButton.frame = CGRectMake(halfTabW, 0, halfTabW, tabH);

    CGFloat indX = (self.activeTab == ROSLoginTabSignIn) ? 0 : halfTabW;
    self.tabIndicatorView.frame = CGRectMake(indX, tabH - 2.5, halfTabW, 2.5);
    curY += tabH + 12.0;

    // Form Container
    CGFloat formH = 220.0;
    self.signInFormView.frame = CGRectMake(pad, curY, contentW, formH);
    self.createAccountFormView.frame = CGRectMake(pad, curY, contentW, formH);

    // Sign In Form Layout
    CGFloat fieldH = 36.0;
    CGFloat fGap = 8.0;
    CGFloat formY = 0;

    self.usernameField.frame = CGRectMake(0, formY, contentW, fieldH);
    formY += fieldH + fGap;

    self.passwordField.frame = CGRectMake(0, formY, contentW, fieldH);
    formY += fieldH + fGap;

    self.serverStatusButton.frame = CGRectMake(0, formY, contentW, 26.0);
    formY += 26.0 + fGap;

    // Remember Me & Forgot Password Row
    CGFloat rowH = 24.0;
    self.rememberMeButton.frame = CGRectMake(0, formY, 130.0, rowH);
    self.forgotPasswordButton.frame = CGRectMake(contentW - 120.0, formY, 120.0, rowH);
    formY += rowH + 10.0;

    self.signInButton.frame = CGRectMake(0, formY, contentW, 40.0);

    // Create Account Form Layout
    CGFloat regY = 0;
    CGFloat regFieldH = 34.0;
    CGFloat regGap = 6.0;

    self.regUsernameField.frame = CGRectMake(0, regY, contentW, regFieldH);
    regY += regFieldH + regGap;

    self.regPasswordField.frame = CGRectMake(0, regY, contentW, regFieldH);
    regY += regFieldH + regGap;

    self.regConfirmPasswordField.frame = CGRectMake(0, regY, contentW, regFieldH);
    regY += regFieldH + regGap;

    self.regInviteCodeField.frame = CGRectMake(0, regY, contentW, regFieldH);
    regY += regFieldH + 10.0;

    self.createAccountButton.frame = CGRectMake(0, regY, contentW, 40.0);

    // Feedback & Footer inside panel
    CGFloat bottomAreaY = curY + formH + 4.0;
    self.statusLabel.frame = CGRectMake(pad, bottomAreaY, contentW, 26.0);
    self.spinner.center = CGPointMake(panelW / 2.0, bottomAreaY + 13.0);

    self.footerLabel.frame = CGRectMake(pad, panelH - 24.0, contentW, 12.0);
    self.versionLabel.frame = CGRectMake(pad, panelH - 12.0, contentW, 10.0);

    CGFloat totalContentH = panelY + panelH + 20.0;
    if (totalContentH < viewH) totalContentH = viewH;
    self.scrollView.contentSize = CGSizeMake(viewW, totalContentH);
}

#pragma mark - Tab Navigation

- (void)selectSignInTab {
    self.activeTab = ROSLoginTabSignIn;
    self.signInFormView.hidden = NO;
    self.createAccountFormView.hidden = YES;
    self.statusLabel.text = @"";

    [self.signInTabButton setTitleColor:[UIColor colorWithRed:1.0 green:0.82 blue:0.25 alpha:1.0] forState:UIControlStateNormal];
    self.signInTabButton.titleLabel.font = [UIFont boldSystemFontOfSize:14];

    [self.createAccountTabButton setTitleColor:[UIColor lightGrayColor] forState:UIControlStateNormal];
    self.createAccountTabButton.titleLabel.font = [UIFont systemFontOfSize:14];

    [UIView animateWithDuration:0.25 animations:^{
        CGFloat halfW = self.tabBarContainer.bounds.size.width / 2.0;
        self.tabIndicatorView.frame = CGRectMake(0, self.tabBarContainer.bounds.size.height - 2.5, halfW, 2.5);
    }];
    [self.view endEditing:YES];
}

- (void)selectCreateAccountTab {
    self.activeTab = ROSLoginTabCreateAccount;
    self.signInFormView.hidden = YES;
    self.createAccountFormView.hidden = NO;
    self.statusLabel.text = @"";

    [self.createAccountTabButton setTitleColor:[UIColor colorWithRed:1.0 green:0.82 blue:0.25 alpha:1.0] forState:UIControlStateNormal];
    self.createAccountTabButton.titleLabel.font = [UIFont boldSystemFontOfSize:14];

    [self.signInTabButton setTitleColor:[UIColor lightGrayColor] forState:UIControlStateNormal];
    self.signInTabButton.titleLabel.font = [UIFont systemFontOfSize:14];

    [UIView animateWithDuration:0.25 animations:^{
        CGFloat halfW = self.tabBarContainer.bounds.size.width / 2.0;
        self.tabIndicatorView.frame = CGRectMake(halfW, self.tabBarContainer.bounds.size.height - 2.5, halfW, 2.5);
    }];
    [self.view endEditing:YES];
}

#pragma mark - Remember Me & Storage

- (void)updateRememberMeButtonAppearance {
    NSString *check = self.rememberMeEnabled ? @"[✓] Remember Me" : @"[  ] Remember Me";
    [self.rememberMeButton setTitle:check forState:UIControlStateNormal];
    UIColor *color = self.rememberMeEnabled ? [UIColor colorWithRed:1.0 green:0.82 blue:0.25 alpha:1.0] : [UIColor lightGrayColor];
    [self.rememberMeButton setTitleColor:color forState:UIControlStateNormal];
    self.rememberMeButton.titleLabel.font = [UIFont systemFontOfSize:11];
}

- (void)toggleRememberMe {
    self.rememberMeEnabled = !self.rememberMeEnabled;
    [[NSUserDefaults standardUserDefaults] setBool:self.rememberMeEnabled forKey:kRememberMeKey];
    if (!self.rememberMeEnabled) {
        [[NSUserDefaults standardUserDefaults] removeObjectForKey:kSavedUsernameKey];
    }
    [self updateRememberMeButtonAppearance];
}

- (void)loadSavedCredentials {
    if (self.rememberMeEnabled) {
        NSString *savedUser = [[NSUserDefaults standardUserDefaults] stringForKey:kSavedUsernameKey];
        if (savedUser && [savedUser length] > 0) {
            self.usernameField.text = savedUser;
        }
    }
}

#pragma mark - Automatic Discovery

- (void)startAutoDiscovery {
    if (self.isDiscovering) return;
    self.isDiscovering = YES;

    [self.serverStatusButton setTitle:@"○ Discovering Server..." forState:UIControlStateNormal];
    [self.serverStatusButton setTitleColor:[UIColor yellowColor] forState:UIControlStateNormal];

    __weak typeof(self) weakSelf = self;
    [ROSSothatDiscoveryClient discoverServerWithCurrentConfig:self.config completion:^(ROSSothatConfig *discovered, NSString *desc) {
        weakSelf.isDiscovering = NO;
        if (discovered) {
            weakSelf.config = discovered;
            weakSelf.authClient.config = discovered;
            [[ROSSothatHookCoordinator sharedCoordinator] updateConfig:discovered];
            [[ROSSothatNetworkClient sharedClient] resetSession];
            rossothat_update_target_host([discovered.serverHost UTF8String]);
            rossothat_probe_local_network([discovered.serverHost UTF8String]);

            NSString *statusStr = [NSString stringWithFormat:@"● Server: %@:%ld (Online)", discovered.serverHost, (long)discovered.authPort];
            [weakSelf.serverStatusButton setTitle:statusStr forState:UIControlStateNormal];
            [weakSelf.serverStatusButton setTitleColor:[UIColor colorWithRed:0.4 green:0.85 blue:0.4 alpha:1.0] forState:UIControlStateNormal];
            [ROSSothatLogger logInfo:@"[SothattLoginVC] Connected to private server at %@", discovered.serverHost];
        } else {
            NSString *host = weakSelf.config.serverHost ?: @"172.20.10.2";
            [weakSelf.serverStatusButton setTitle:[NSString stringWithFormat:@"● Server: %@:%ld", host, (long)weakSelf.config.authPort] forState:UIControlStateNormal];
            [weakSelf.serverStatusButton setTitleColor:[UIColor lightGrayColor] forState:UIControlStateNormal];
        }
    }];
}

#pragma mark - Authentication & Registration Handlers

- (void)handleDeploy {
    [self.view endEditing:YES];

    if (!self.deployButton.enabled) {
        return;
    }

    NSString *user = [self.usernameField.text stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];
    NSString *pass = self.passwordField.text;

    if ([user length] == 0 || [pass length] == 0) {
        [ROSSothatErrorHandler showAlertWithTitle:@"Login Required" message:@"Please enter your username and password." fromController:self];
        return;
    }

    // Save username if Remember Me enabled
    if (self.rememberMeEnabled) {
        [[NSUserDefaults standardUserDefaults] setObject:user forKey:kSavedUsernameKey];
    }

    [self.deployButton setEnabled:NO];
    [self.spinner startAnimating];
    self.statusLabel.text = @"Authenticating credentials...";

    // Zero out password UI text field immediately for security
    self.passwordField.text = @"";

    rossothat_set_active_credentials([user UTF8String], [pass UTF8String]);
    rossothat_set_login_state(ROSSOTHAT_LOGIN_STATE_AUTHENTICATING);

    [ROSSothatLogger logInfo:@"[NativeLoginBridge] Pre-authenticating player '%@' against auth endpoint...", user];

    __weak typeof(self) weakSelf = self;
    [self.authClient loginWithUsername:user password:pass completion:^(BOOL success, uint32_t sessionKey, NSString *errorMessage) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf.spinner stopAnimating];
            [weakSelf.deployButton setEnabled:YES];

            if (success) {
                rossothat_set_login_state(ROSSOTHAT_LOGIN_STATE_AUTHENTICATED);
                weakSelf.statusLabel.text = @"Success! Entering game lobby...";
                if (weakSelf.onLoginSuccess) {
                    weakSelf.onLoginSuccess(sessionKey);
                }
                [weakSelf dismissViewControllerAnimated:YES completion:nil];
            } else {
                rossothat_set_login_state(ROSSOTHAT_LOGIN_STATE_FAILED);
                rossothat_clear_active_credentials();
                rossothat_clear_active_ticket();
                weakSelf.statusLabel.text = @"";
                [ROSSothatErrorHandler showAlertWithTitle:@"Authentication Failed"
                                                  message:errorMessage ?: @"Invalid username or password."
                                           fromController:weakSelf];
            }
        });
    }];
}

- (void)handleCreateAccount {
    [self.view endEditing:YES];

    if (!self.createAccountButton.enabled) {
        return;
    }

    NSString *user = [self.regUsernameField.text stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];
    NSString *pass = self.regPasswordField.text;
    NSString *confirmPass = self.regConfirmPasswordField.text;
    NSString *invite = [self.regInviteCodeField.text stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];

    if ([user length] < 3) {
        [ROSSothatErrorHandler showAlertWithTitle:@"Invalid Username" message:@"Username must be at least 3 characters long." fromController:self];
        return;
    }
    if ([pass length] < 4) {
        [ROSSothatErrorHandler showAlertWithTitle:@"Invalid Password" message:@"Password must be at least 4 characters long." fromController:self];
        return;
    }
    if (![pass isEqualToString:confirmPass]) {
        [ROSSothatErrorHandler showAlertWithTitle:@"Password Mismatch" message:@"Password and confirmation do not match." fromController:self];
        return;
    }

    [self.createAccountButton setEnabled:NO];
    [self.spinner startAnimating];
    self.statusLabel.text = @"Creating account...";

    // Clear password text fields immediately for security
    self.regPasswordField.text = @"";
    self.regConfirmPasswordField.text = @"";

    __weak typeof(self) weakSelf = self;
    [self.authClient registerWithUsername:user password:pass confirmPassword:confirmPass inviteCode:invite completion:^(BOOL success, NSString *message) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf.spinner stopAnimating];
            [weakSelf.createAccountButton setEnabled:YES];

            if (success) {
                weakSelf.statusLabel.text = @"Account created! Please sign in.";
                [weakSelf selectSignInTab];
                weakSelf.usernameField.text = user;
                [ROSSothatErrorHandler showAlertWithTitle:@"Registration Successful"
                                                  message:@"Account created successfully! You can now sign in."
                                           fromController:weakSelf];
            } else {
                weakSelf.statusLabel.text = @"";
                [ROSSothatErrorHandler showAlertWithTitle:@"Registration Failed"
                                                  message:message ?: @"Could not register account."
                                           fromController:weakSelf];
            }
        });
    }];
}

#pragma mark - Quick Action Bar Handlers

- (void)handleNotice {
    [self.view endEditing:YES];
    NSString *msg = @"ROS SOTHATT PRIVATE SERVER\n\n"
                    @"• Physical iPhone Hotspot & LAN connectivity enabled.\n"
                    @"• Preserves original Rules of Survival battle royale gameplay.\n"
                    @"• Private account authentication & diamond economy active.\n"
                    @"• For private testing and research use only.";
    [ROSSothatErrorHandler showAlertWithTitle:@"Server Notice" message:msg fromController:self];
}

- (void)handleRepair {
    [self.view endEditing:YES];
    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Repair & Re-discover"
                                                                   message:@"Reset local network cache and automatically re-discover the private server over Wi-Fi / Hotspot?"
                                                            preferredStyle:UIAlertControllerStyleAlert];

    __weak typeof(self) weakSelf = self;
    UIAlertAction *repairAction = [UIAlertAction actionWithTitle:@"Repair Now" style:UIAlertActionStyleDestructive handler:^(__unused UIAlertAction *action) {
        weakSelf.statusLabel.text = @"Repairing network configuration...";
        [weakSelf startAutoDiscovery];
    }];
    UIAlertAction *cancelAction = [UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil];

    [alert addAction:repairAction];
    [alert addAction:cancelAction];
    [self presentViewController:alert animated:YES completion:nil];
}

- (void)handleLanguage {
    [self.view endEditing:YES];
    [ROSSothatErrorHandler showAlertWithTitle:@"Language" message:@"Current Language: English\n(Native ROS Sothatt client integration)." fromController:self];
}

- (void)handleLogout {
    [self.view endEditing:YES];
    self.usernameField.text = @"";
    self.passwordField.text = @"";
    rossothat_clear_active_credentials();
    rossothat_clear_active_ticket();
    rossothat_set_login_state(ROSSOTHAT_LOGIN_STATE_IDLE);
    self.statusLabel.text = @"Logged out.";
}

- (void)handleForgotPassword {
    [self.view endEditing:YES];
    NSString *msg = @"Password Recovery:\n\n"
                    @"Please contact your ROS Sothatt server administrator (sothatt_admin) to reset your account password, or use the 'Create Account' tab to register a new player identity.";
    [ROSSothatErrorHandler showAlertWithTitle:@"Password Recovery" message:msg fromController:self];
}

#pragma mark - Server Settings Dialog

- (void)handleSettings {
    [self.view endEditing:YES];

    UIAlertController *alert = [UIAlertController alertControllerWithTitle:@"Server Configuration"
                                                                   message:@"Configure private ROS Sothatt backend IP address or discover automatically."
                                                            preferredStyle:UIAlertControllerStyleAlert];

    [alert addTextFieldWithConfigurationHandler:^(UITextField *textField) {
        textField.placeholder = @"Server IPv4 (e.g. 192.168.1.6)";
        textField.text = self.config.serverHost;
        textField.keyboardType = UIKeyboardTypeNumbersAndPunctuation;
    }];

    __weak typeof(self) weakSelf = self;
    UIAlertAction *saveAction = [UIAlertAction actionWithTitle:@"Save & Reload" style:UIAlertActionStyleDefault handler:^(__unused UIAlertAction *action) {
        NSString *newHost = [alert.textFields.firstObject.text stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceCharacterSet]];
        if ([newHost length] > 0) {
            NSError *err = nil;
            ROSSothatConfig *current = weakSelf.config ?: [ROSSothatConfig defaultConfig];
            NSDictionary *dict = @{
                @"version": @(current.version),
                @"server_host": newHost,
                @"auth_port": @(current.authPort),
                @"discovery_port": @(current.discoveryPort),
                @"discovery_https_port": @(current.discoveryHttpsPort),
                @"baseapp_port": @(current.baseappPort),
                @"cellapp_port": @(current.cellappPort),
                @"auth_path": current.authPath ?: @"/v2/ros/login_mobile_ios_v2",
                @"discovery_path": current.discoveryPath ?: @"/server_list_ios.txt",
                @"timeout_seconds": @(current.timeoutSeconds),
                @"tls_enabled": @(current.tlsEnabled)
            };
            NSData *data = [NSJSONSerialization dataWithJSONObject:dict options:0 error:nil];
            ROSSothatConfig *newCfg = [ROSSothatConfig configFromJSONData:data error:&err];
            if (newCfg) {
                [ROSSothatConfig saveToDocumentsDirectory:newCfg error:nil];
                weakSelf.config = newCfg;
                weakSelf.authClient = [[ROSSothatAuthClient alloc] initWithConfig:newCfg];
                [[ROSSothatHookCoordinator sharedCoordinator] updateConfig:newCfg];
                [[ROSSothatNetworkClient sharedClient] resetSession];
                rossothat_update_target_host([newHost UTF8String]);
                rossothat_probe_local_network([newHost UTF8String]);
                [weakSelf.serverStatusButton setTitle:[NSString stringWithFormat:@"● Server: %@:%ld (Online)", newHost, (long)newCfg.authPort] forState:UIControlStateNormal];
            } else {
                [ROSSothatErrorHandler showAlertWithTitle:@"Invalid IP" message:@"Please enter a valid private IPv4 address." fromController:weakSelf];
            }
        }
    }];

    UIAlertAction *autoAction = [UIAlertAction actionWithTitle:@"Auto-Discover" style:UIAlertActionStyleDefault handler:^(__unused UIAlertAction *action) {
        [weakSelf startAutoDiscovery];
    }];

    UIAlertAction *cancelAction = [UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil];
    [alert addAction:saveAction];
    [alert addAction:autoAction];
    [alert addAction:cancelAction];

    [self presentViewController:alert animated:YES completion:nil];
}

#pragma mark - Keyboard Handling

- (void)touchesBegan:(NSSet<UITouch *> *)touches withEvent:(UIEvent *)event {
    [super touchesBegan:touches withEvent:event];
    [self.view endEditing:YES];
}

- (void)dismissKeyboard {
    [self.view endEditing:YES];
}

- (void)keyboardWillShow:(NSNotification *)notification {
    NSDictionary *userInfo = notification.userInfo;
    CGRect keyboardFrame = [userInfo[UIKeyboardFrameEndUserInfoKey] CGRectValue];
    CGRect convertedFrame = [self.view convertRect:keyboardFrame fromView:nil];
    CGFloat keyboardHeight = self.view.bounds.size.height - convertedFrame.origin.y;
    if (keyboardHeight < 0) keyboardHeight = 0;

    UIEdgeInsets insets = UIEdgeInsetsMake(0, 0, keyboardHeight, 0);
    NSTimeInterval duration = [userInfo[UIKeyboardAnimationDurationUserInfoKey] doubleValue];
    UIViewAnimationOptions curve = [userInfo[UIKeyboardAnimationCurveUserInfoKey] unsignedIntegerValue] << 16;

    [UIView animateWithDuration:duration delay:0 options:curve animations:^{
        self.scrollView.contentInset = insets;
        self.scrollView.scrollIndicatorInsets = insets;
    } completion:nil];

    // Scroll active field or panel into view
    [self.scrollView scrollRectToVisible:self.panelView.frame animated:YES];
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
    } else if (textField == self.regUsernameField) {
        [self.regPasswordField becomeFirstResponder];
    } else if (textField == self.regPasswordField) {
        [self.regConfirmPasswordField becomeFirstResponder];
    } else if (textField == self.regConfirmPasswordField) {
        [self.regInviteCodeField becomeFirstResponder];
    } else if (textField == self.regInviteCodeField) {
        [self.regInviteCodeField resignFirstResponder];
        [self handleCreateAccount];
    }
    return YES;
}

@end
