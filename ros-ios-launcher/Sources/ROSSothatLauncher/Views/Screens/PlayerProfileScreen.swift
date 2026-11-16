import SwiftUI

public struct PlayerProfileScreen: View {
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
                        launcherVM.navigateTo(.homeDashboard)
                    }) {
                        HStack(spacing: 4) {
                            Text("←")
                                .font(.system(size: 16, weight: .bold))
                            Text("DASHBOARD")
                                .font(.system(size: 12, weight: .bold))
                        }
                        .foregroundColor(TacticalTheme.gold)
                    }
                    Spacer()
                    Text("PLAYER DOSSIER")
                        .font(.system(size: 12, weight: .bold))
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
                    if let user = authVM.currentUser {
                        VStack(spacing: 20) {
                            // Profile Card
                            TacticalCard(isHighlighted: true) {
                                VStack(spacing: 16) {
                                    HStack(spacing: 16) {
                                        ZStack {
                                            Circle()
                                                .fill(TacticalTheme.bgSecondary)
                                                .frame(width: 72, height: 72)
                                                .overlay(
                                                    Circle()
                                                        .stroke(TacticalTheme.gold, lineWidth: 2)
                                                )
                                                .shadow(color: TacticalTheme.gold.opacity(0.3), radius: 8)
                                            Text(user.avatarSymbol)
                                                .font(.system(size: 36))
                                        }
                                        
                                        VStack(alignment: .leading, spacing: 4) {
                                            HStack {
                                                Text(user.username)
                                                    .font(.system(size: 20, weight: .black))
                                                    .foregroundColor(TacticalTheme.textPrimary)
                                                if user.isVerified {
                                                    Text("✓")
                                                        .font(.system(size: 12, weight: .bold))
                                                        .foregroundColor(TacticalTheme.success)
                                                }
                                            }
                                            
                                            Text(user.rankTitle)
                                                .font(.system(size: 13, weight: .bold))
                                                .foregroundColor(TacticalTheme.gold)
                                            
                                            Text("ID: #\(user.id) • \(user.role)")
                                                .font(.system(size: 11))
                                                .foregroundColor(TacticalTheme.textMuted)
                                        }
                                        Spacer()
                                    }
                                    
                                    // EXP Bar
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack {
                                            Text("LEVEL \(user.level)")
                                                .font(.system(size: 10, weight: .black))
                                                .foregroundColor(TacticalTheme.gold)
                                            Spacer()
                                            Text("\(user.exp) / \(user.maxExp) EXP")
                                                .font(.system(size: 10, design: .monospaced))
                                                .foregroundColor(TacticalTheme.textSecondary)
                                        }
                                        
                                        GeometryReader { geo in
                                            ZStack(alignment: .leading) {
                                                Capsule()
                                                    .fill(TacticalTheme.border)
                                                    .frame(height: 6)
                                                Capsule()
                                                    .fill(TacticalTheme.gold)
                                                    .frame(width: geo.size.width * CGFloat(Double(user.exp) / Double(user.maxExp)), height: 6)
                                            }
                                        }
                                        .frame(height: 6)
                                    }
                                }
                            }
                            .padding(.horizontal, 16)
                            
                            // Combat Telemetry Grid
                            VStack(alignment: .leading, spacing: 10) {
                                Text("COMBAT TELEMETRY")
                                    .font(.system(size: 11, weight: .black))
                                    .tracking(1.0)
                                    .foregroundColor(TacticalTheme.textMuted)
                                    .padding(.horizontal, 16)
                                
                                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                                    StatTile(title: "MATCHES PLAYED", value: "\(user.matchesPlayed)", icon: "🎮")
                                    StatTile(title: "VICTORIES (WINS)", value: "\(user.wins)", icon: "🏆")
                                    StatTile(title: "KILL / DEATH RATIO", value: String(format: "%.2f", user.kdRatio), icon: "🎯", isHighlight: true)
                                    StatTile(title: "WIN RATE", value: String(format: "%.1f%%", user.winRate), icon: "📊")
                                    StatTile(title: "TOTAL CONFIRMED KILLS", value: "\(user.kills)", icon: "💀")
                                    StatTile(title: "DIAMOND LEDGER", value: "\(user.diamonds) 💎", icon: "💎", isHighlight: true)
                                }
                                .padding(.horizontal, 16)
                            }
                            
                            // Account Actions
                            VStack(spacing: 12) {
                                SecondaryButton("SIGN OUT OF LAUNCHER", icon: "🚪") {
                                    authVM.signOut()
                                    launcherVM.navigateTo(.welcome)
                                }
                            }
                            .padding(.horizontal, 16)
                        }
                        .padding(.top, 14)
                        .padding(.bottom, 80)
                    }
                }
            }
        }
    }
}

struct StatTile: View {
    let title: String
    let value: String
    let icon: String
    var isHighlight: Bool = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(icon)
                Spacer()
                Text(title)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundColor(TacticalTheme.textMuted)
            }
            Text(value)
                .font(.system(size: 18, weight: .black, design: .monospaced))
                .foregroundColor(isHighlight ? TacticalTheme.gold : TacticalTheme.textPrimary)
        }
        .padding(12)
        .background(TacticalTheme.bgCard)
        .cornerRadius(6)
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(isHighlight ? TacticalTheme.borderGold : TacticalTheme.border, lineWidth: 1)
        )
    }
}
