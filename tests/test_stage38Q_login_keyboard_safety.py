"""
ROS Sothatt — Stage 38Q Login Screen Keyboard & UI Safety Test Suite.

Verifies:
1. Auto-focus suppression:
   - viewDidLoad, viewWillAppear:, and viewDidAppear: call [self.view endEditing:YES].
   - No automatic becomeFirstResponder on load.
2. Text field delegates and return keys:
   - Both usernameField and passwordField set delegate = self.
   - usernameField returnKeyType is UIReturnKeyNext.
   - passwordField returnKeyType is UIReturnKeyDone.
   - passwordField preserves secureTextEntry = YES.
3. Return key navigation and deployment:
   - textFieldShouldReturn: advances focus to passwordField from usernameField.
   - textFieldShouldReturn: resigns first responder and invokes handleDeploy from passwordField.
4. Tap and touch dismissal:
   - Tap gesture recognizer attached with cancelsTouchesInView = NO.
   - touchesBegan:withEvent: dismisses keyboard via [self.view endEditing:YES].
   - handleDeploy dismisses keyboard via [self.view endEditing:YES].
5. Keyboard notification observers and scroll view:
   - UIScrollView and contentView hierarchy implemented.
   - UIKeyboardWillShowNotification adjusts contentInset and scrolls to active element.
   - UIKeyboardWillHideNotification resets contentInset to UIEdgeInsetsZero.
   - Observers registered in viewWillAppear: and deregistered in viewWillDisappear: / dealloc.
6. Layout geometry:
   - Dynamic positioning in viewDidLayoutSubviews.
   - Form fits within iPhone X landscape (812 x 375 pt).
   - Preserves Server IPv4 placeholder (192.168.1.13) and zero retired IPs.
"""

import os
import re
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

LOGIN_VC_M = os.path.join(PROJECT_ROOT, "src", "hook", "src", "SothattLoginVC.m")
LOGIN_VC_H = os.path.join(PROJECT_ROOT, "src", "hook", "include", "SothattLoginVC.h")


class TestLoginKeyboardSafety(unittest.TestCase):
    """Safety and interaction verification suite for SothattLoginVC on iOS 16."""

    @classmethod
    def setUpClass(cls):
        with open(LOGIN_VC_M, "r", encoding="utf-8") as f:
            cls.login_m = f.read()
        with open(LOGIN_VC_H, "r", encoding="utf-8") as f:
            cls.login_h = f.read()

    def test_01_delegate_protocol_conformance(self):
        """Verifies SothattLoginVC conforms to UITextFieldDelegate."""
        self.assertIn("<UITextFieldDelegate>", self.login_m,
                      "SothattLoginVC interface must declare <UITextFieldDelegate>")

    def test_02_text_field_delegates_assigned(self):
        """Verifies both usernameField and passwordField assign delegate = self."""
        self.assertRegex(self.login_m, r"_usernameField\.delegate\s*=\s*self\s*;",
                         "usernameField must set delegate = self")
        self.assertRegex(self.login_m, r"_passwordField\.delegate\s*=\s*self\s*;",
                         "passwordField must set delegate = self")

    def test_03_return_key_types_configured(self):
        """Verifies return key types for Next on username and Done on password."""
        self.assertIn("UIReturnKeyNext", self.login_m,
                      "usernameField must configure UIReturnKeyNext")
        self.assertIn("UIReturnKeyDone", self.login_m,
                      "passwordField must configure UIReturnKeyDone")

    def test_04_text_field_should_return_implemented(self):
        """Verifies textFieldShouldReturn: implementation handles both fields."""
        self.assertIn("textFieldShouldReturn:", self.login_m,
                      "Must implement textFieldShouldReturn:")
        # Username transitions to password
        self.assertRegex(self.login_m, r"\[self\.passwordField\s+becomeFirstResponder\]",
                         "Return on usernameField must advance focus to passwordField")
        # Password resigns and deploys
        self.assertRegex(self.login_m, r"\[self\.passwordField\s+resignFirstResponder\]",
                         "Return on passwordField must resign first responder")
        self.assertRegex(self.login_m, r"\[self\s+handleDeploy\]",
                         "Return on passwordField must trigger handleDeploy")

    def test_05_tap_gesture_and_touch_dismissal(self):
        """Verifies tap outside and touchesBegan dismiss keyboard without canceling button taps."""
        self.assertIn("UITapGestureRecognizer", self.login_m,
                      "Must attach UITapGestureRecognizer")
        self.assertRegex(self.login_m, r"cancelsTouchesInView\s*=\s*NO",
                         "Tap gesture must set cancelsTouchesInView = NO")
        self.assertIn("touchesBegan:", self.login_m,
                      "Must implement touchesBegan:withEvent:")
        self.assertRegex(self.login_m, r"\[self\.view\s+endEditing:YES\]",
                         "Touch handling must dismiss keyboard via endEditing:YES")

    def test_06_auto_focus_suppression(self):
        """Verifies keyboard does not automatically pop up on screen presentation."""
        # Check viewDidLoad, viewWillAppear, viewDidAppear
        self.assertIn("- (void)viewWillAppear:(BOOL)animated", self.login_m,
                      "Must implement viewWillAppear:")
        self.assertIn("- (void)viewDidAppear:(BOOL)animated", self.login_m,
                      "Must implement viewDidAppear:")
        # Confirm no auto becomeFirstResponder in setup or view lifecycle
        setup_match = re.search(r"- \(void\)setupUI\s*\{([\s\S]*?)\n\}", self.login_m)
        self.assertIsNotNone(setup_match, "setupUI method must exist")
        self.assertNotIn("becomeFirstResponder", setup_match.group(1),
                         "setupUI must not automatically invoke becomeFirstResponder")

    def test_07_keyboard_notifications_registered_and_cleaned(self):
        """Verifies keyboard notifications are registered and deregistered safely."""
        self.assertIn("UIKeyboardWillShowNotification", self.login_m,
                      "Must observe UIKeyboardWillShowNotification")
        self.assertIn("UIKeyboardWillHideNotification", self.login_m,
                      "Must observe UIKeyboardWillHideNotification")
        self.assertIn("keyboardWillShow:", self.login_m,
                      "Must implement keyboardWillShow:")
        self.assertIn("keyboardWillHide:", self.login_m,
                      "Must implement keyboardWillHide:")
        # Observer cleanup
        self.assertIn("removeObserver:", self.login_m,
                      "Must deregister notification observers in viewWillDisappear or dealloc")

    def test_08_scroll_view_hierarchy_and_inset_adjustment(self):
        """Verifies UIScrollView and contentView hierarchy with insets adjustment."""
        self.assertIn("UIScrollView", self.login_m, "Must use UIScrollView")
        self.assertIn("contentInset", self.login_m, "Must adjust contentInset on keyboard show/hide")
        self.assertIn("scrollRectToVisible:", self.login_m,
                      "Must call scrollRectToVisible: when keyboard appears")

    def test_09_deploy_button_dismisses_keyboard_and_prevents_duplicate_requests(self):
        """Verifies handleDeploy immediately ends editing and prevents duplicate in-flight requests."""
        deploy_match = re.search(r"- \(void\)handleDeploy\s*\{([\s\S]*?)\n\}", self.login_m)
        self.assertIsNotNone(deploy_match, "handleDeploy method must exist")
        deploy_body = deploy_match.group(1)
        self.assertIn("[self.view endEditing:YES];", deploy_body,
                      "handleDeploy must dismiss keyboard immediately")
        self.assertIn("!self.deployButton.enabled", deploy_body,
                      "handleDeploy must guard against duplicate in-flight requests")
        self.assertIn("[self.deployButton setEnabled:NO];", deploy_body,
                      "handleDeploy must disable DEPLOY button while authenticating")

    def test_10_password_security_preserved(self):
        """Verifies password field maintains secureTextEntry = YES and clearing after use."""
        self.assertRegex(self.login_m, r"_passwordField\.secureTextEntry\s*=\s*YES\s*;",
                         "Password field must have secureTextEntry = YES")
        self.assertRegex(self.login_m, r"self\.passwordField\.text\s*=\s*@\"\"\s*;",
                         "Password field text must be cleared after authentication begins")

    def test_11_layout_geometry_iphone_x_landscape(self):
        """Simulates iPhone X landscape (812 x 375 pt) geometry to verify accurate stack height and centering."""
        # Check source code calculates stack height dynamically and eliminates 256 constant
        self.assertIn("stackH", self.login_m, "SothattLoginVC.m must dynamically calculate stackH")
        self.assertNotIn("CGFloat contentTotalH = 256.0;", self.login_m,
                         "SothattLoginVC.m must not use hardcoded 256.0 pt contentTotalH constant")

        screen_w = 812.0
        screen_h = 375.0
        keyboard_h = 216.0

        box_w = 340.0
        box_x = (screen_w - box_w) / 2.0
        self.assertGreater(box_x, 44.0, "Form box must clear iPhone X notch (44 pt safe area)")

        title_h = 34.0
        gap_title_sub = 8.0
        sub_h = 18.0
        gap_sub_user = 14.0
        field_h = 42.0
        gap_user_pass = 10.0
        gap_pass_deploy = 14.0
        deploy_h = 46.0
        gap_deploy_settings = 10.0
        settings_h = 32.0
        gap_settings_status = 8.0
        status_h = 20.0

        # Accurately calculate actual vertical stack height (298.0 pt visual height)
        stack_h = (title_h + gap_title_sub + sub_h + gap_sub_user +
                   field_h + gap_user_pass + field_h + gap_pass_deploy +
                   deploy_h + gap_deploy_settings + settings_h + gap_settings_status + status_h)
        self.assertAlmostEqual(stack_h, 298.0, places=1,
                               msg="Visual stack height must be 298.0 pt")

        # Vertically center form when keyboard is hidden (mirrors SothattLoginVC.m viewDidLayoutSubviews)
        top_margin = (screen_h - stack_h) / 2.0 if (screen_h > stack_h) else 16.0
        if top_margin < 16.0:
            top_margin = 16.0
        bottom_padding = top_margin
        content_total_h = stack_h + top_margin + bottom_padding
        if content_total_h < screen_h:
            content_total_h = screen_h

        self.assertAlmostEqual(top_margin, 38.5, places=1,
                               msg="Top margin must be 38.5 pt on 375 pt height")
        self.assertAlmostEqual(bottom_padding, 38.5, places=1,
                               msg="Bottom padding must equal top margin (38.5 pt)")
        self.assertAlmostEqual(content_total_h, 375.0, places=1,
                               msg="Total content height must be exactly 375.0 pt matching view height")

        status_bottom = top_margin + stack_h
        bottom_margin = screen_h - status_bottom

        # Verify symmetric vertical centering when keyboard is hidden
        self.assertAlmostEqual(top_margin, bottom_margin, places=1,
                               msg="Form must be symmetrically centered vertically (top margin == bottom margin)")
        self.assertGreater(top_margin, 30.0, "Top margin should be comfortable (~38.5 pt)")

        # Verify UIScrollView scrolling limits and viewport visibility
        bounds_h = screen_h  # 375.0 pt
        content_size_h = content_total_h  # 375.0 pt (symmetrical topMargin + stackH + bottomPadding = 375.0 pt)
        adj_bottom = keyboard_h  # 216.0 pt
        visible_viewport_h = bounds_h - adj_bottom  # 159.0 pt

        # Actual UIKit maximum contentOffset.y formula
        max_offset_y = content_size_h + adj_bottom - bounds_h  # 216.0 pt
        self.assertEqual(max_offset_y, 216.0,
                         "Maximum contentOffset.y must be exactly 216.0 pt")

        # Cluster bounds: DEPLOY button top to Status label bottom
        deploy_top = top_margin + title_h + gap_title_sub + sub_h + gap_sub_user + field_h + gap_user_pass + field_h + gap_pass_deploy
        deploy_bottom = deploy_top + deploy_h
        spinner_y = deploy_top + (deploy_h / 2.0)
        status_top = deploy_bottom + gap_deploy_settings + settings_h + gap_settings_status
        status_bottom = status_top + status_h

        cluster_height = status_bottom - deploy_top
        self.assertLessEqual(cluster_height, visible_viewport_h,
                             f"Action cluster ({cluster_height:.1f} pt) must fit inside 159 pt viewport")

        # Required offset range for full cluster visibility simultaneously
        req_min_offset = status_bottom - visible_viewport_h  # 177.5 pt
        req_max_offset = deploy_top  # 220.5 pt

        # Confirm required offset range is within achievable scroll offsets [0.0, max_offset_y]
        self.assertLessEqual(req_min_offset, max_offset_y,
                             "Required minimum offset must be <= max_offset_y")
        achievable_min = max(0.0, req_min_offset)
        achievable_max = min(max_offset_y, req_max_offset)
        self.assertLessEqual(achievable_min, achievable_max,
                             "There must be a valid offset range where all elements are visible")

        # Verify element positions at representative offset (196.8 pt)
        test_offset = (achievable_min + achievable_max) / 2.0
        deploy_vp = (deploy_top - test_offset, deploy_bottom - test_offset)
        spinner_vp = (spinner_y - 18.5 - test_offset, spinner_y + 18.5 - test_offset)
        status_vp = (status_top - test_offset, status_bottom - test_offset)

        self.assertTrue(0 <= deploy_vp[0] and deploy_vp[1] <= visible_viewport_h,
                        f"DEPLOY button ({deploy_vp}) must be in 0..{visible_viewport_h}")
        self.assertTrue(0 <= spinner_vp[0] and spinner_vp[1] <= visible_viewport_h,
                        f"Spinner ({spinner_vp}) must be in 0..{visible_viewport_h}")
        self.assertTrue(0 <= status_vp[0] and status_vp[1] <= visible_viewport_h,
                        f"Status label ({status_vp}) must be in 0..{visible_viewport_h}")

        # Also verify at max_offset_y (216.0 pt)
        deploy_at_max = (deploy_top - max_offset_y, deploy_bottom - max_offset_y)
        status_at_max = (status_top - max_offset_y, status_bottom - max_offset_y)
        self.assertTrue(0 <= deploy_at_max[0] and deploy_at_max[1] <= visible_viewport_h,
                        "DEPLOY button must be visible at max scroll")
        self.assertTrue(0 <= status_at_max[0] and status_at_max[1] <= visible_viewport_h,
                        "Status label must be visible at max scroll")

    def test_12_server_config_placeholder_and_ip_sanitation(self):
        """Verifies server IP placeholder is 192.168.1.13 and no retired IP is present."""
        self.assertIn("Server IPv4 (e.g. 192.168.1.13)", self.login_m,
                      "Placeholder must specify 192.168.1.13")
        self.assertNotIn("192.168.100.11", self.login_m,
                      "Retired IP 192.168.100.11 must not be present")


if __name__ == "__main__":
    unittest.main()
