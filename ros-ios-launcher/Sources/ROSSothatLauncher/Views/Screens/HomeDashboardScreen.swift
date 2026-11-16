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
            // Dark charcoal / black tactical background
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // MARK: - Top Tactical Bar
                HStack {
                    // Operator Status
                    if authVM.isAuthenticated, let user = authVM.currentUser {
                        HStack(spacing: 6) {
                            Circle()
                                .fill(TacticalTheme.success)
                                .frame(width: 5, height: 5)
                            Text("OPERATOR // \(user.username.uppercased())")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .tracking(0.8)
                                .foregroundColor(TacticalTheme.gold)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(TacticalTheme.bgCard)
                        .cornerRadius(3)
                        .overlay(
                            RoundedRectangle(cornerRadius: 3)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    } else {
                        HStack(spacing: 6) {
                            Circle()
                                .fill(TacticalTheme.textMuted)
                                .frame(width: 5, height: 5)
                            Text("STANDBY // GUEST")
                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                .tracking(0.8)
                                .foregroundColor(TacticalTheme.textMuted)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(TacticalTheme.bgCard)
                        .cornerRadius(3)
                        .overlay(
                            RoundedRectangle(cornerRadius: 3)
                                .stroke(TacticalTheme.border, lineWidth: 1)
                        )
                    }
                    
                    Spacer()
                    
                    // Small Login Button in Top-Right Corner
                    Button(action: {
                        showLoginSheet = true
                    }) {
                        Text(authVM.isAuthenticated ? "ACCOUNT" : "LOGIN")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(1.4)
                            .foregroundColor(TacticalTheme.gold)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(TacticalTheme.bgCard)
                            .cornerRadius(3)
                            .overlay(
                                RoundedRectangle(cornerRadius: 3)
                                    .stroke(TacticalTheme.borderGold, lineWidth: 1)
                            )
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 12)
                
                Spacer()
                
                // MARK: - Center Hero (Focus on Game Artwork)
                VStack(spacing: 16) {
                    // Artwork with clean, flat gold bezel
                    Image("Logo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 170, height: 170)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    
                    VStack(spacing: 6) {
                        HStack(spacing: 6) {
                            Text("ROS")
                                .font(.system(size: 26, weight: .black))
                                .tracking(2.0)
                                .foregroundColor(TacticalTheme.textPrimary)
                            Text("SOTHATT")
                                .font(.system(size: 26, weight: .black))
                                .tracking(2.0)
                                .foregroundColor(TacticalTheme.gold)
                        }
                        
                        Text("RULES OF SURVIVAL LEGACY")
                            .font(.system(size: 11, weight: .bold))
                            .tracking(3.0)
                            .foregroundColor(TacticalTheme.textSecondary)
                        
                        Rectangle()
                            .fill(TacticalTheme.borderGold)
                            .frame(width: 48, height: 1)
                            .padding(.top, 4)
                    }
                }
                
                Spacer()
                
                // MARK: - Bottom Action Buttons (Clear, Flat, Precision Gaming UI)
                VStack(spacing: 12) {
                    // Action 1: PLAY GAME (Primary Action)
                    PrimaryButton("PLAY GAME", systemImage: "play.fill") {
                        showPlaySheet = true
                    }
                    
                    // Action 2: DOWNLOAD GAME (Secondary Action)
                    SecondaryButton("DOWNLOAD GAME", systemImage: "arrow.down.to.line") {
                        showDownloadSheet = true
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
    
    var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 16) {
                // Header
                HStack {
                    Text("DEPLOYMENT // PLAY GAME")
                        .font(.system(size: 12, weight: .black))
                        .tracking(1.2)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    Button("CLOSE") {
                        isPresented = false
                    }
                    .font(.system(size: 11, weight: .bold))
                    .tracking(1.0)
                    .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.horizontal, 20)
                .padding(.top, 20)
                
                ScrollView {
                    VStack(spacing: 14) {
                        TacticalCard(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("CLIENT STATUS")
                                        .font(.system(size: 10, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    StatusBadge("AUTHENTIC", variant: .beta)
                                }
                                
                                Text("Rules of Survival Legacy")
                                    .font(.system(size: 16, weight: .black))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                
                                Text("Preserved iOS ARM64 client build ready for island deployment.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                            }
                        }
                        
                        // Option 1: URL Scheme Launch
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack {
                                    Text("METHOD 1")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    StatusBadge("URL SCHEME", variant: .online)
                                }
                                
                                Text("Direct Client Launch")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                
                                Text("Launches the sideloaded game client directly via its registered 'rosmobile://' URL protocol.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                
                                PrimaryButton("LAUNCH VIA 'rosmobile://'", systemImage: "play.fill") {
                                    if let url = URL(string: "rosmobile://") {
                                        UIApplication.shared.open(url, options: [:], completionHandler: nil)
                                    }
                                }
                                .padding(.top, 4)
                            }
                        }
                        
                        // Option 2: Home Screen Launch
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("METHOD 2")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    StatusBadge("HOME SCREEN", variant: .gold)
                                }
                                
                                Text("iPhone Home Screen")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                
                                Text("If Rules of Survival Legacy has been installed on your device, swipe up to your Home Screen and tap the 'RoS Legacy' app icon directly.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                            }
                        }
                        
                        // Security Notice
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("IOS SANDBOX POLICY")
                                    .font(.system(size: 9, weight: .bold))
                                    .tracking(1.0)
                                    .foregroundColor(TacticalTheme.textMuted)
                                
                                Text("Standard iOS application sandboxing prevents third-party apps from injecting code or forcing external processes to execute without URL schemes.")
                                    .font(.system(size: 10))
                                    .foregroundColor(TacticalTheme.textMuted)
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
            
            VStack(spacing: 16) {
                // Header
                HStack {
                    Text("DISTRIBUTION // DOWNLOAD GAME")
                        .font(.system(size: 12, weight: .black))
                        .tracking(1.2)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    Button("CLOSE") {
                        isPresented = false
                    }
                    .font(.system(size: 11, weight: .bold))
                    .tracking(1.0)
                    .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.horizontal, 20)
                .padding(.top, 20)
                
                ScrollView {
                    VStack(spacing: 14) {
                        // Package Card
                        TacticalCard(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("ARCHIVE PACKAGE")
                                        .font(.system(size: 10, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    StatusBadge("ARM64 IPA", variant: .gold)
                                }
                                
                                Text("Rules of Survival Legacy")
                                    .font(.system(size: 16, weight: .black))
                                    .foregroundColor(TacticalTheme.textPrimary)
                                
                                Text("Preserved original iOS client binary (approx. 846 MB).")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                            }
                        }
                        
                        // Download Action
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 10) {
                                Text("DIRECT SAFARI DOWNLOAD")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(TacticalTheme.gold)
                                
                                Text("Tap below to download the IPA package into your iPhone Files / Safari download queue.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                
                                PrimaryButton("DOWNLOAD IPA VIA SAFARI", systemImage: "arrow.down.to.line") {
                                    if let url = URL(string: "https://rossothat.com/download") {
                                        UIApplication.shared.open(url, options: [:], completionHandler: nil)
                                    }
                                }
                                .padding(.top, 4)
                            }
                        }
                        
                        // Sideload Instructions
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("INSTALLATION INSTRUCTIONS")
                                    .font(.system(size: 11, weight: .bold))
                                    .foregroundColor(TacticalTheme.gold)
                                
                                VStack(alignment: .leading, spacing: 6) {
                                    Text("1. Transfer or open the downloaded IPA on your Mac/PC.")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                    Text("2. Use Sideloadly or AltStore to sign the app with your Apple ID.")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                    Text("3. On iPhone: Settings > General > VPN & Device Management > Trust.")
                                        .font(.system(size: 11))
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

// MARK: - Login Action Sheet
struct LoginActionSheet: View {
    @Binding var isPresented: Bool
    @EnvironmentObject public var authVM: AuthViewModel
    
    var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 16) {
                // Header
                HStack {
                    Text("OPERATOR ACCESS")
                        .font(.system(size: 12, weight: .black))
                        .tracking(1.2)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    Button("CLOSE") {
                        isPresented = false
                    }
                    .font(.system(size: 11, weight: .bold))
                    .tracking(1.0)
                    .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.horizontal, 20)
                .padding(.top, 20)
                
                ScrollView {
                    VStack(spacing: 14) {
                        if authVM.isAuthenticated, let user = authVM.currentUser {
                            TacticalCard(isHighlighted: true) {
                                VStack(spacing: 14) {
                                    VStack(spacing: 4) {
                                        Text(user.username.uppercased())
                                            .font(.system(size: 16, weight: .black))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                        Text(user.email)
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        StatusBadge("OPERATOR VERIFIED", variant: .online)
                                            .padding(.top, 4)
                                    }
                                    
                                    SecondaryButton("SIGN OUT", systemImage: "rectangle.portrait.and.arrow.right") {
                                        authVM.signOut()
                                    }
                                    .padding(.top, 4)
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 8)
                            }
                        } else {
                            TacticalCard(isHighlighted: true) {
                                VStack(alignment: .leading, spacing: 12) {
                                    Text("ENTER OPERATOR CALLSIGN")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    
                                    Text("PLAYER EMAIL")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    CustomTextField("operator@domain.com", icon: "envelope.fill", text: $authVM.emailInput)
                                    
                                    Text("VERIFICATION CODE")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    CustomTextField("123456", icon: "lock.fill", text: $authVM.otpInput)
                                    
                                    PrimaryButton("SIGN IN AS OPERATOR", systemImage: "key.fill", isLoading: authVM.isLoading) {
                                        authVM.verifyOtp()
                                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
                                            if authVM.isAuthenticated {
                                                isPresented = false
                                            }
                                        }
                                    }
                                    .padding(.top, 4)
                                }
                            }
                            
                            TacticalCard {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text("TOKEN AUTHENTICATION")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    Text("Operator state integrates with private server authentication endpoints.")
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
