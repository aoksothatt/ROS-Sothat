import SwiftUI

public struct PlayScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    @State private var selectedMode: String = "SOLO SURVIVAL"
    
    private let matchModes = ["SOLO SURVIVAL", "DUO SQUAD", "CUSTOM PRIVATE ROOM"]
    
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
                            Image(systemName: "chevron.left")
                                .font(.system(size: 12, weight: .bold))
                            Text("DASHBOARD")
                                .font(.system(size: 11, weight: .bold))
                                .tracking(1.0)
                        }
                        .foregroundColor(TacticalTheme.gold)
                    }
                    Spacer()
                    Text("WAR ROOM DISPATCH")
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
                    VStack(spacing: 16) {
                        // Combat Ready Hero Card
                        TacticalCard(isHighlighted: true) {
                            VStack(spacing: 12) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text("OPERATION ISLAND SURVIVOR")
                                            .font(.system(size: 10, weight: .bold))
                                            .tracking(1.0)
                                            .foregroundColor(TacticalTheme.gold)
                                        Text(selectedMode)
                                            .font(.system(size: 16, weight: .black))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                    }
                                    Spacer()
                                    StatusBadge("SERVER READY", variant: .online)
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                // Server & Session Telemetry
                                VStack(spacing: 6) {
                                    HStack {
                                        Text("Mercury Gateway:")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        Spacer()
                                        Text("\(launcherVM.gameVersion.serverHost):\(launcherVM.gameVersion.serverPort)")
                                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                    }
                                    
                                    HStack {
                                        Text("Protocol Codec:")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        Spacer()
                                        Text("Blowfish PBC (Zero-IV)")
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(TacticalTheme.gold)
                                    }
                                    
                                    HStack {
                                        Text("Active Operator:")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        Spacer()
                                        Text(authVM.currentUser?.username ?? "GhostOperator")
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(TacticalTheme.success)
                                    }
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                        
                        // Mode Selection
                        VStack(alignment: .leading, spacing: 8) {
                            Text("SELECT DEPLOYMENT MODE")
                                .font(.system(size: 10, weight: .black))
                                .tracking(1.2)
                                .foregroundColor(TacticalTheme.textMuted)
                                .padding(.horizontal, 16)
                            
                            VStack(spacing: 6) {
                                ForEach(matchModes, id: \.self) { mode in
                                    Button(action: {
                                        selectedMode = mode
                                    }) {
                                        HStack {
                                            Image(systemName: modeIcon(mode))
                                                .font(.system(size: 13, weight: .bold))
                                                .foregroundColor(selectedMode == mode ? TacticalTheme.gold : TacticalTheme.textMuted)
                                            Text(mode)
                                                .font(.system(size: 12, weight: .bold))
                                                .tracking(0.8)
                                                .foregroundColor(selectedMode == mode ? TacticalTheme.gold : TacticalTheme.textPrimary)
                                            Spacer()
                                            if selectedMode == mode {
                                                Image(systemName: "checkmark")
                                                    .font(.system(size: 11, weight: .bold))
                                                    .foregroundColor(TacticalTheme.gold)
                                            }
                                        }
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 12)
                                        .background(selectedMode == mode ? TacticalTheme.bgCardHover : TacticalTheme.bgCard)
                                        .cornerRadius(3)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 3)
                                                .stroke(selectedMode == mode ? TacticalTheme.gold : TacticalTheme.border, lineWidth: 1)
                                        )
                                    }
                                    .padding(.horizontal, 16)
                                }
                            }
                        }
                        
                        // Launch Action Area
                        VStack(spacing: 12) {
                            PrimaryButton("OPEN GAME CLIENT ('rosmobile://')", systemImage: "play.fill") {
                                if let url = URL(string: "rosmobile://") {
                                    UIApplication.shared.open(url, options: [:], completionHandler: nil)
                                }
                            }
                            .padding(.horizontal, 16)
                            
                            TacticalCard {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text("IOS SANDBOX POLICY")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    
                                    Text("If Rules of Survival Legacy has been sideloaded, tap above to open via 'rosmobile://', or launch 'RoS Legacy' directly from your iPhone Home Screen.")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                }
                            }
                            .padding(.horizontal, 16)
                        }
                    }
                    .padding(.top, 14)
                    .padding(.bottom, 40)
                }
            }
        }
    }
    
    private func modeIcon(_ mode: String) -> String {
        switch mode {
        case "SOLO SURVIVAL": return "person.fill"
        case "DUO SQUAD": return "person.2.fill"
        default: return "shield.fill"
        }
    }
}
