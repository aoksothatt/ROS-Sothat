import SwiftUI

public struct CreateAccountScreen: View {
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
                            launcherVM.navigateTo(.welcome)
                        }
                    }) {
                        HStack(spacing: 4) {
                            Text("←")
                                .font(.system(size: 16, weight: .bold))
                            Text("BACK")
                                .font(.system(size: 12, weight: .bold))
                        }
                        .foregroundColor(TacticalTheme.gold)
                    }
                    
                    Spacer()
                    
                    Text("NEW OPERATOR REGISTRATION")
                        .font(.system(size: 11, weight: .bold))
                        .tracking(1.0)
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
                    VStack(spacing: 24) {
                        // Title Area
                        VStack(spacing: 6) {
                            Text("🎖️")
                                .font(.system(size: 36))
                                .padding(.top, 16)
                            
                            Text("COMMUNITY REGISTRATION")
                                .font(.system(size: 22, weight: .black))
                                .foregroundColor(TacticalTheme.textPrimary)
                            
                            Text("Create your persistent survivor profile and join private rooms.")
                                .font(.system(size: 12))
                                .foregroundColor(TacticalTheme.textSecondary)
                                .multilineTextAlignment(.center)
                        }
                        
                        // Messages
                        if let error = authVM.errorMessage {
                            HStack {
                                Text("⚠️")
                                Text(error)
                                    .font(.system(size: 12))
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(TacticalTheme.danger.opacity(0.12))
                            .foregroundColor(TacticalTheme.danger)
                            .cornerRadius(6)
                        }
                        
                        if let success = authVM.successMessage {
                            HStack {
                                Text("💡")
                                Text(success)
                                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                            }
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(TacticalTheme.success.opacity(0.12))
                            .foregroundColor(TacticalTheme.success)
                            .cornerRadius(6)
                        }
                        
                        // Form Card
                        TacticalCard(isHighlighted: true) {
                            if !authVM.isOtpStep {
                                VStack(alignment: .leading, spacing: 14) {
                                    Text("CALLSIGN / CODENAME")
                                        .font(.system(size: 10, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.textMuted)
                                    
                                    CustomTextField("GhostOperator", icon: "👤", text: $authVM.usernameInput)
                                    
                                    Text("PLAYER EMAIL")
                                        .font(.system(size: 10, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.textMuted)
                                    
                                    CustomTextField("operator@ros-sothat.island", icon: "✉️", text: $authVM.emailInput)
                                    
                                    PrimaryButton("REQUEST INVITATION CODE", icon: "✉️", isLoading: authVM.isLoading) {
                                        authVM.requestRegisterOtp()
                                    }
                                }
                            } else {
                                VStack(alignment: .leading, spacing: 14) {
                                    Text("6-DIGIT VERIFICATION CODE")
                                        .font(.system(size: 10, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.textMuted)
                                    
                                    CustomTextField("123456", icon: "🔐", text: $authVM.otpInput)
                                    
                                    PrimaryButton("REGISTER & INITIALIZE", icon: "✓", isLoading: authVM.isLoading) {
                                        authVM.verifyOtp()
                                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                                            if authVM.isAuthenticated {
                                                launcherVM.navigateTo(.homeDashboard)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                        
                        // Bottom Link
                        Button(action: {
                            launcherVM.navigateTo(.signIn)
                        }) {
                            Text("Already registered? Sign In ➔")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(TacticalTheme.gold)
                        }
                    }
                    .padding(.bottom, 24)
                }
            }
        }
    }
}
