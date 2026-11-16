import SwiftUI

public struct WelcomeScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 0) {
                BrandHeader(showStatus: true, serverPing: launcherVM.serverPingMs)
                
                ScrollView {
                    VStack(spacing: 24) {
                        // Hero Visual Banner
                        ZStack {
                            RoundedRectangle(cornerRadius: 12)
                                .fill(
                                    LinearGradient(
                                        gradient: Gradient(colors: [TacticalTheme.bgCard, TacticalTheme.bgSecondary]),
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    )
                                )
                                .frame(height: 180)
                                .overlay(
                                    RoundedRectangle(cornerRadius: 12)
                                        .stroke(TacticalTheme.borderGold, lineWidth: 1)
                                )
                            
                            VStack(spacing: 8) {
                                StatusBadge("PRIVATE COMMUNITY", variant: .gold)
                                Text("THE ISLAND IS WAITING")
                                    .font(.system(size: 22, weight: .black))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                Text("A closed private server ecosystem for 10–20 invited friends.")
                                    .font(.system(size: 12))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                    .multilineTextAlignment(.center)
                                    .padding(.horizontal, 24)
                            }
                        }
                        .padding(.horizontal, 16)
                        .padding(.top, 12)
                        
                        // Feature Pills
                        HStack(spacing: 12) {
                            FeaturePill(icon: "⚡", title: "120 FPS", subtitle: "ProMotion")
                            FeaturePill(icon: "🔒", title: "Blowfish", subtitle: "PBC Crypto")
                            FeaturePill(icon: "💎", title: "Free Diamonds", subtitle: "Ledger Sync")
                        }
                        .padding(.horizontal, 16)
                        
                        // Action Buttons
                        VStack(spacing: 12) {
                            PrimaryButton("SIGN IN WITH OPERATOR ID", icon: "🔑") {
                                launcherVM.navigateTo(.signIn)
                            }
                            
                            SecondaryButton("CREATE NEW ACCOUNT", icon: "📝") {
                                launcherVM.navigateTo(.createAccount)
                            }
                            
                            Button(action: {
                                // Guest preview directly enters home dashboard with mock player
                                authVM.isAuthenticated = true
                                authVM.currentUser = MockData.samplePlayer
                                launcherVM.navigateTo(.homeDashboard)
                            }) {
                                Text("CONTINUE AS GUEST PREVIEW ➔")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(TacticalTheme.gold)
                                    .padding(.vertical, 8)
                            }
                        }
                        .padding(.horizontal, 16)
                        
                        // Quick Links
                        HStack(spacing: 16) {
                            Button("Installation Guide") {
                                launcherVM.navigateTo(.installationGuide)
                            }
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(TacticalTheme.textSecondary)
                            
                            Text("•")
                                .foregroundColor(TacticalTheme.textMuted)
                            
                            Button("Download Portal") {
                                launcherVM.navigateTo(.gameDownload)
                            }
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundColor(TacticalTheme.textSecondary)
                        }
                        .padding(.top, 8)
                    }
                    .padding(.bottom, 24)
                }
            }
        }
    }
}

struct FeaturePill: View {
    let icon: String
    let title: String
    let subtitle: String
    
    var body: some View {
        VStack(spacing: 3) {
            Text(icon)
                .font(.system(size: 18))
            Text(title)
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(TacticalTheme.textPrimary)
            Text(subtitle)
                .font(.system(size: 9))
                .foregroundColor(TacticalTheme.textMuted)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(TacticalTheme.bgCard)
        .cornerRadius(6)
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(TacticalTheme.border, lineWidth: 1)
        )
    }
}
