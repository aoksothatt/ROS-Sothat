import SwiftUI

public struct SignInScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Top Navigation Bar
                HStack {
                    Button(action: {
                        if authVM.isOtpStep {
                            authVM.isOtpStep = false
                        } else {
                            launcherVM.navigateTo(.homeDashboard)
                        }
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "chevron.left")
                                .font(.system(size: 12, weight: .bold))
                            Text("BACK")
                                .font(.system(size: 11, weight: .bold))
                                .tracking(1.0)
                        }
                        .foregroundColor(TacticalTheme.gold)
                    }
                    
                    Spacer()
                    
                    Text("OPERATOR ACCESS")
                        .font(.system(size: 11, weight: .bold))
                        .tracking(1.2)
                        .foregroundColor(TacticalTheme.textSecondary)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 14)
                .background(TacticalTheme.bgSecondary)
                .overlay(
                    Rectangle()
                        .frame(height: 1)
                        .foregroundColor(TacticalTheme.border),
                    alignment: .bottom
                )
                
                ScrollView {
                    VStack(spacing: 20) {
                        // Title Area
                        VStack(spacing: 6) {
                            Image(systemName: "lock.shield.fill")
                                .font(.system(size: 28))
                                .foregroundColor(TacticalTheme.gold)
                                .padding(.top, 16)
                            
                            Text("SIGN IN TO ISLAND")
                                .font(.system(size: 20, weight: .black))
                                .foregroundColor(TacticalTheme.textPrimary)
                            
                            Text("Enter your invited operator credentials to synchronize.")
                                .font(.system(size: 11))
                                .foregroundColor(TacticalTheme.textSecondary)
                                .multilineTextAlignment(.center)
                        }
                        
                        // Messages
                        if let error = authVM.errorMessage {
                            HStack(spacing: 6) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .font(.system(size: 12))
                                Text(error)
                                    .font(.system(size: 11))
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(TacticalTheme.danger.opacity(0.12))
                            .foregroundColor(TacticalTheme.danger)
                            .cornerRadius(3)
                        }
                        
                        if let success = authVM.successMessage {
                            HStack(spacing: 6) {
                                Image(systemName: "checkmark.circle.fill")
                                    .font(.system(size: 12))
                                Text(success)
                                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(TacticalTheme.success.opacity(0.12))
                            .foregroundColor(TacticalTheme.success)
                            .cornerRadius(3)
                        }
                        
                        // Form Card
                        TacticalCard(isHighlighted: true) {
                            if !authVM.isOtpStep {
                                VStack(alignment: .leading, spacing: 12) {
                                    Text("PLAYER EMAIL")
                                        .font(.system(size: 9, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.textMuted)
                                    
                                    CustomTextField("operator@domain.com", icon: "envelope.fill", text: $authVM.emailInput)
                                    
                                    PrimaryButton("SEND VERIFICATION CODE", systemImage: "arrow.right", isLoading: authVM.isLoading) {
                                        authVM.requestSignInOtp()
                                    }
                                    .padding(.top, 4)
                                }
                            } else {
                                VStack(alignment: .leading, spacing: 12) {
                                    Text("6-DIGIT VERIFICATION CODE")
                                        .font(.system(size: 9, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.textMuted)
                                    
                                    CustomTextField("123456", icon: "lock.fill", text: $authVM.otpInput)
                                    
                                    PrimaryButton("VERIFY & ENTER", systemImage: "checkmark", isLoading: authVM.isLoading) {
                                        authVM.verifyOtp()
                                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                                            if authVM.isAuthenticated {
                                                launcherVM.navigateTo(.homeDashboard)
                                            }
                                        }
                                    }
                                    .padding(.top, 4)
                                    
                                    Button("Resend code") {
                                        authVM.requestSignInOtp()
                                    }
                                    .font(.system(size: 11, weight: .semibold))
                                    .foregroundColor(TacticalTheme.gold)
                                    .frame(maxWidth: .infinity)
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                    }
                    .padding(.bottom, 24)
                }
            }
        }
    }
}
