import SwiftUI

public struct HomeDashboardScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    @State private var showPlaySheet: Bool = false
    @State private var showDownloadSheet: Bool = false
    @State private var showLoginSheet: Bool = false
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            // Subtle radial gold ambient glow behind hero
            VStack {
                RadialGradient(
                    gradient: Gradient(colors: [TacticalTheme.gold.opacity(0.12), Color.clear]),
                    center: .center,
                    startRadius: 20,
                    endRadius: 300
                )
                .frame(height: 380)
                .ignoresSafeArea()
                Spacer()
            }
            
            VStack(spacing: 0) {
                // Top Status Bar
                HStack {
                    if authVM.isAuthenticated, let user = authVM.currentUser {
                        HStack(spacing: 6) {
                            Circle()
                                .fill(TacticalTheme.success)
                                .frame(width: 8, height: 8)
                            Text("OPERATOR:")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(TacticalTheme.textMuted)
                            Text(user.username.uppercased())
                                .font(.system(size: 11, weight: .black))
                                .foregroundColor(TacticalTheme.gold)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(TacticalTheme.bgCard)
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    } else {
                        HStack(spacing: 6) {
                            Circle()
                                .fill(TacticalTheme.textMuted)
                                .frame(width: 8, height: 8)
                            Text("GUEST MODE")
                                .font(.system(size: 10, weight: .bold))
                                .foregroundColor(TacticalTheme.textMuted)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(TacticalTheme.bgCard)
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(TacticalTheme.border, lineWidth: 1)
                        )
                    }
                    
                    Spacer()
                    
                    Button(action: {
                        showLoginSheet = true
                    }) {
                        HStack(spacing: 5) {
                            Text("🔑")
                                .font(.system(size: 12))
                            Text(authVM.isAuthenticated ? "ACCOUNT" : "LOGIN")
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(TacticalTheme.gold)
                        }
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(TacticalTheme.bgCard)
                        .cornerRadius(12)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 16)
                
                Spacer()
                
                // Center Hero Branding
                VStack(spacing: 16) {
                    Image("Logo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 140, height: 140)
                        .clipShape(RoundedRectangle(cornerRadius: 24, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 24, style: .continuous)
                                .stroke(
                                    LinearGradient(
                                        colors: [TacticalTheme.goldLight, TacticalTheme.goldDark],
                                        startPoint: .topLeading,
                                        endPoint: .bottomTrailing
                                    ),
                                    lineWidth: 2
                                )
                        )
                        .shadow(color: TacticalTheme.gold.opacity(0.35), radius: 20, x: 0, y: 6)
                    
                    VStack(spacing: 6) {
                        HStack(spacing: 8) {
                            Text("ROS")
                                .font(.system(size: 32, weight: .black))
                                .foregroundColor(TacticalTheme.textPrimary)
                            Text("SOTHATT")
                                .font(.system(size: 32, weight: .black))
                                .foregroundColor(TacticalTheme.gold)
                        }
                        
                        Text("RULES OF SURVIVAL LEGACY")
                            .font(.system(size: 12, weight: .bold))
                            .tracking(2.5)
                            .foregroundColor(TacticalTheme.textSecondary)
                        
                        StatusBadge("COMMUNITY LAUNCHER", variant: .gold)
                            .padding(.top, 4)
                    }
                }
                
                Spacer()
                
                // The 3 Main Actions
                VStack(spacing: 14) {
                    // Action 1: PLAY GAME (Primary CTA)
                    PrimaryButton("PLAY GAME", icon: "▶️") {
                        showPlaySheet = true
                    }
                    
                    // Action 2: DOWNLOAD GAME IPA
                    SecondaryButton("DOWNLOAD GAME IPA", icon: "📥") {
                        showDownloadSheet = true
                    }
                    
                    // Action 3: LOGIN
                    SecondaryButton(authVM.isAuthenticated ? "MANAGE OPERATOR ACCOUNT" : "LOGIN TO ACCOUNT", icon: "🔑") {
                        showLoginSheet = true
                    }
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 40)
            }
        }
        // Action Sheets
        .sheet(isPresented: $showPlaySheet) {
            PlayActionSheet(isPresented: $showPlaySheet)
        }
        .sheet(isPresented: $showDownloadSheet) {
            DownloadActionSheet(isPresented: $showDownloadSheet)
        }
        .sheet(isPresented: $showLoginSheet) {
            LoginActionSheet(isPresented: $showLoginSheet)
        }
    }
}

// MARK: - Play Action Sheet
struct PlayActionSheet: View {
    @Binding var isPresented: Bool
    @State private var launchAttempted: Bool = false
    
    var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 20) {
                // Header
                HStack {
                    Text("WAR ROOM — PLAY GAME")
                        .font(.system(size: 13, weight: .black))
                        .tracking(1.0)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    Button("Close") {
                        isPresented = false
                    }
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.horizontal, 20)
                .padding(.top, 20)
                
                ScrollView {
                    VStack(spacing: 18) {
                        TacticalCard(isHighlighted: true) {
                            VStack(spacing: 12) {
                                Text("⚔️")
                                    .font(.system(size: 36))
                                Text("RULES OF SURVIVAL LEGACY")
                                    .font(.system(size: 16, weight: .black))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                Text("Ready for combat deployment on private island rooms.")
                                    .font(.system(size: 12))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                    .multilineTextAlignment(.center)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                        }
                        
                        // Launch Option 1: URL Scheme
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack {
                                    Text("OPTION 1")
                                        .font(.system(size: 10, weight: .black))
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    StatusBadge("URL SCHEME", variant: .online)
                                }
                                
                                Text("Attempt Direct Launch")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                
                                Text("Attempts to launch the game client via its registered 'rosmobile://' URL scheme.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                
                                PrimaryButton("LAUNCH VIA 'rosmobile://'", icon: "🚀") {
                                    launchAttempted = true
                                    if let url = URL(string: "rosmobile://") {
                                        UIApplication.shared.open(url, options: [:], completionHandler: nil)
                                    }
                                }
                                .padding(.top, 4)
                            }
                        }
                        
                        // Launch Option 2: Home Screen Manual
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack {
                                    Text("OPTION 2")
                                        .font(.system(size: 10, weight: .black))
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    StatusBadge("HOME SCREEN", variant: .gold)
                                }
                                
                                Text("iPhone Home Screen Launch")
                                    .font(.system(size: 14, weight: .bold))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                
                                Text("If Rules of Survival Legacy has been sideloaded onto your iPhone, swipe up and tap the 'RoS Legacy' app icon directly from your Home Screen.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                
                                Text("ℹ️ Under standard iOS security sandboxing, one app cannot force another app to open unless the target custom URL scheme is active.")
                                    .font(.system(size: 10))
                                    .foregroundColor(TacticalTheme.textMuted)
                                    .padding(8)
                                    .background(TacticalTheme.bgSecondary)
                                    .cornerRadius(6)
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 24)
                }
            }
        }
    }
}

// MARK: - Download Action Sheet
struct DownloadActionSheet: View {
    @Binding var isPresented: Bool
    
    var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 20) {
                // Header
                HStack {
                    Text("CLIENT DISTRIBUTION")
                        .font(.system(size: 13, weight: .black))
                        .tracking(1.0)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    Button("Close") {
                        isPresented = false
                    }
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.horizontal, 20)
                .padding(.top, 20)
                
                ScrollView {
                    VStack(spacing: 18) {
                        TacticalCard(isHighlighted: true) {
                            VStack(spacing: 10) {
                                Text("📦")
                                    .font(.system(size: 36))
                                Text("ORIGINAL GAME IPA PACKAGE")
                                    .font(.system(size: 16, weight: .black))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                Text("Preserved original Rules of Survival iOS ARM64 client package (846 MB).")
                                    .font(.system(size: 12))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                    .multilineTextAlignment(.center)
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 8)
                        }
                        
                        // Download Action
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("DOWNLOAD FILE VIA SAFARI")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(TacticalTheme.gold)
                                
                                Text("Tap below to download the game IPA package directly into your iPhone's Files app / Safari download manager.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                
                                PrimaryButton("OPEN DOWNLOAD IN SAFARI", icon: "🌐") {
                                    if let url = URL(string: "https://rossothat.com/download") {
                                        UIApplication.shared.open(url, options: [:], completionHandler: nil)
                                    }
                                }
                            }
                        }
                        
                        // Sideload Notice
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("⚙️ HOW TO INSTALL ON IPHONE")
                                    .font(.system(size: 11, weight: .black))
                                    .foregroundColor(TacticalTheme.gold)
                                
                                Text("1. iOS sandboxing prevents any normal app from installing an IPA file directly on device.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                
                                Text("2. Use a computer with Sideloadly (Windows/Mac) or AltStore to sign and install the downloaded IPA using your free Apple ID.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                
                                Text("3. Once installed, trust your certificate under Settings > General > VPN & Device Management.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 24)
                }
            }
        }
    }
}

// MARK: - Login Action Sheet
struct LoginActionSheet: View {
    @Binding var isPresented: Bool
    @EnvironmentObject public var authVM: AuthViewModel
    
    var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 20) {
                // Header
                HStack {
                    Text("OPERATOR ACCESS")
                        .font(.system(size: 13, weight: .black))
                        .tracking(1.0)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    Button("Close") {
                        isPresented = false
                    }
                    .font(.system(size: 13, weight: .bold))
                    .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.horizontal, 20)
                .padding(.top, 20)
                
                ScrollView {
                    VStack(spacing: 20) {
                        if authVM.isAuthenticated, let user = authVM.currentUser {
                            TacticalCard(isHighlighted: true) {
                                VStack(spacing: 14) {
                                    Text("🎖️")
                                        .font(.system(size: 40))
                                    
                                    VStack(spacing: 4) {
                                        Text(user.username)
                                            .font(.system(size: 18, weight: .black))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                        Text(user.email)
                                            .font(.system(size: 12))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        StatusBadge("OPERATOR VERIFIED", variant: .online)
                                            .padding(.top, 4)
                                    }
                                    
                                    SecondaryButton("SIGN OUT", icon: "🚪") {
                                        authVM.signOut()
                                    }
                                    .padding(.top, 8)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 8)
                            }
                        } else {
                            TacticalCard(isHighlighted: true) {
                                VStack(alignment: .leading, spacing: 14) {
                                    Text("SIGN IN WITH OPERATOR ID")
                                        .font(.system(size: 12, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    
                                    Text("PLAYER EMAIL / CALLSIGN")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    CustomTextField("operator@ros-sothat.island", icon: "✉️", text: $authVM.emailInput)
                                    
                                    Text("VERIFICATION CODE")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    CustomTextField("123456", icon: "🔐", text: $authVM.otpInput)
                                    
                                    PrimaryButton("SIGN IN AS OPERATOR", icon: "🔑", isLoading: authVM.isLoading) {
                                        authVM.verifyOtp()
                                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                                            if authVM.isAuthenticated {
                                                isPresented = false
                                            }
                                        }
                                    }
                                    .padding(.top, 6)
                                }
                            }
                            
                            TacticalCard {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text("ℹ️ PRIVATE SERVER AUTHENTICATION")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    Text("Interface is pre-configured and ready for live server token integration when the backend authentication endpoint goes live.")
                                        .font(.system(size: 10))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 24)
                }
            }
        }
    }
}
