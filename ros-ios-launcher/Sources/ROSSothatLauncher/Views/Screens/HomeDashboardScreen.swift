import SwiftUI

public struct HomeDashboardScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 0) {
                BrandHeader(showStatus: true, serverPing: launcherVM.serverPingMs)
                
                ScrollView {
                    VStack(spacing: 18) {
                        // Player Overview Card
                        if let user = authVM.currentUser {
                            TacticalCard(isHighlighted: true) {
                                HStack(spacing: 14) {
                                    ZStack {
                                        RoundedRectangle(cornerRadius: 10)
                                            .fill(TacticalTheme.bgSecondary)
                                            .frame(width: 52, height: 52)
                                            .overlay(
                                                RoundedRectangle(cornerRadius: 10)
                                                    .stroke(TacticalTheme.gold.opacity(0.4), lineWidth: 1)
                                            )
                                        Text(user.avatarSymbol)
                                            .font(.system(size: 26))
                                    }
                                    
                                    VStack(alignment: .leading, spacing: 3) {
                                        HStack {
                                            Text(user.username)
                                                .font(.system(size: 17, weight: .black))
                                                .foregroundColor(TacticalTheme.textPrimary)
                                            StatusBadge("LVL \(user.level)", variant: .gold)
                                        }
                                        Text(user.rankTitle)
                                            .font(.system(size: 11, weight: .semibold))
                                            .foregroundColor(TacticalTheme.gold)
                                        Text("ID: #\(user.id) • \(user.role)")
                                            .font(.system(size: 10))
                                            .foregroundColor(TacticalTheme.textMuted)
                                    }
                                    
                                    Spacer()
                                    
                                    Button(action: {
                                        launcherVM.navigateTo(.playerProfile)
                                    }) {
                                        Text("STATS ➔")
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(TacticalTheme.gold)
                                    }
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                HStack {
                                    HStack(spacing: 4) {
                                        Text("💎")
                                        Text("\(user.diamonds)")
                                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                                            .foregroundColor(TacticalTheme.gold)
                                        Text("Diamonds")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                    }
                                    Spacer()
                                    HStack(spacing: 4) {
                                        Text("🪙")
                                        Text("\(user.gold)")
                                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                        Text("Gold")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                    }
                                    Spacer()
                                    HStack(spacing: 4) {
                                        Text("🎯")
                                        Text(String(format: "%.1f", user.kdRatio))
                                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                                            .foregroundColor(TacticalTheme.success)
                                        Text("K/D")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                    }
                                }
                            }
                            .padding(.horizontal, 16)
                        }
                        
                        // Main Play CTA Card
                        VStack(spacing: 12) {
                            PrimaryButton("LAUNCH LEGACY SESSION", icon: "▶️") {
                                launcherVM.navigateTo(.playScreen)
                            }
                            
                            HStack(spacing: 12) {
                                SecondaryButton("GAME DOWNLOAD", icon: "📥") {
                                    launcherVM.navigateTo(.gameDownload)
                                }
                                SecondaryButton("INSTALL GUIDE", icon: "📖") {
                                    launcherVM.navigateTo(.installationGuide)
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                        
                        // Server Status Quick Bar
                        TacticalCard {
                            HStack {
                                VStack(alignment: .leading, spacing: 3) {
                                    HStack(spacing: 6) {
                                        Circle()
                                            .fill(TacticalTheme.success)
                                            .frame(width: 8, height: 8)
                                        Text("GATEWAY STATUS: ONLINE")
                                            .font(.system(size: 11, weight: .black))
                                            .foregroundColor(TacticalTheme.success)
                                    }
                                    Text("Mercury UDP: \(launcherVM.gameVersion.serverHost):\(launcherVM.gameVersion.serverPort)")
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                }
                                Spacer()
                                Button("PING") {
                                    launcherVM.refreshServerStatus()
                                }
                                .font(.system(size: 10, weight: .bold))
                                .padding(.horizontal, 10)
                                .padding(.vertical, 4)
                                .background(TacticalTheme.bgSecondary)
                                .foregroundColor(TacticalTheme.gold)
                                .cornerRadius(4)
                            }
                        }
                        .padding(.horizontal, 16)
                        
                        // Announcements List
                        VStack(alignment: .leading, spacing: 10) {
                            Text("COMMUNITY ANNOUNCEMENTS")
                                .font(.system(size: 11, weight: .black))
                                .tracking(1.0)
                                .foregroundColor(TacticalTheme.textMuted)
                                .padding(.horizontal, 16)
                            
                            ForEach(launcherVM.announcements) { news in
                                TacticalCard {
                                    VStack(alignment: .leading, spacing: 6) {
                                        HStack {
                                            StatusBadge(news.tag, variant: .gold)
                                            Spacer()
                                            Text(news.date)
                                                .font(.system(size: 10))
                                                .foregroundColor(TacticalTheme.textMuted)
                                        }
                                        Text(news.title)
                                            .font(.system(size: 13, weight: .bold))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                        Text(news.summary)
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                            .lineLimit(2)
                                    }
                                }
                                .padding(.horizontal, 16)
                            }
                        }
                    }
                    .padding(.top, 12)
                    .padding(.bottom, 80)
                }
            }
        }
    }
}
