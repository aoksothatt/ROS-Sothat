import SwiftUI

public struct PlayScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    @State private var selectedMode: String = "SOLO SURVIVAL"
    @State private var isLaunching: Bool = false
    @State private var launchStepText: String = "READY FOR COMBAT"
    @State private var launchProgress: Double = 0.0
    @State private var isSessionActive: Bool = false
    
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
                            Text("←")
                                .font(.system(size: 16, weight: .bold))
                            Text("DASHBOARD")
                                .font(.system(size: 12, weight: .bold))
                        }
                        .foregroundColor(TacticalTheme.gold)
                    }
                    Spacer()
                    Text("WAR ROOM DISPATCH")
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
                    VStack(spacing: 20) {
                        // Combat Ready Hero Card
                        TacticalCard(isHighlighted: true) {
                            VStack(spacing: 14) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text("OPERATION ISLAND SURVIVOR")
                                            .font(.system(size: 10, weight: .bold))
                                            .tracking(1.0)
                                            .foregroundColor(TacticalTheme.gold)
                                        Text(selectedMode)
                                            .font(.system(size: 18, weight: .black))
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
                        VStack(alignment: .leading, spacing: 10) {
                            Text("SELECT DEPLOYMENT MODE")
                                .font(.system(size: 11, weight: .black))
                                .tracking(1.0)
                                .foregroundColor(TacticalTheme.textMuted)
                                .padding(.horizontal, 16)
                            
                            VStack(spacing: 8) {
                                ForEach(matchModes, id: \.self) { mode in
                                    Button(action: {
                                        selectedMode = mode
                                    }) {
                                        HStack {
                                            Text(modeIcon(mode))
                                                .font(.system(size: 18))
                                            Text(mode)
                                                .font(.system(size: 13, weight: .bold))
                                                .foregroundColor(selectedMode == mode ? TacticalTheme.gold : TacticalTheme.textPrimary)
                                            Spacer()
                                            if selectedMode == mode {
                                                Text("✓")
                                                    .font(.system(size: 13, weight: .black))
                                                    .foregroundColor(TacticalTheme.gold)
                                            }
                                        }
                                        .padding(.horizontal, 16)
                                        .padding(.vertical, 14)
                                        .background(selectedMode == mode ? TacticalTheme.bgCardHover : TacticalTheme.bgCard)
                                        .cornerRadius(6)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 6)
                                                .stroke(selectedMode == mode ? TacticalTheme.gold : TacticalTheme.border, lineWidth: 1)
                                        )
                                    }
                                    .padding(.horizontal, 16)
                                }
                            }
                        }
                        
                        // Launch Action Area
                        VStack(spacing: 12) {
                            if isLaunching {
                                VStack(spacing: 8) {
                                    Text(launchStepText)
                                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                                        .foregroundColor(TacticalTheme.gold)
                                    
                                    ProgressView(value: launchProgress)
                                        .progressViewStyle(LinearProgressViewStyle(tint: TacticalTheme.gold))
                                        .scaleEffect(x: 1, y: 2, anchor: .center)
                                }
                                .padding(16)
                                .background(TacticalTheme.bgCard)
                                .cornerRadius(6)
                                .padding(.horizontal, 16)
                            } else if isSessionActive {
                                TacticalCard(isHighlighted: true) {
                                    VStack(spacing: 10) {
                                        Text("SESSION HANDSHAKE COMPLETE ✓")
                                            .font(.system(size: 12, weight: .black))
                                            .foregroundColor(TacticalTheme.success)
                                        Text("Symmetric 56-byte Blowfish channel established on 127.0.0.1:20014. Launch original game client on your device to enter battle.")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                            .multilineTextAlignment(.center)
                                        
                                        SecondaryButton("RESET SESSION") {
                                            isSessionActive = false
                                        }
                                    }
                                }
                                .padding(.horizontal, 16)
                            } else {
                                PrimaryButton("INITIALIZE & LAUNCH SESSION", icon: "🚀") {
                                    simulateLaunch()
                                }
                                .padding(.horizontal, 16)
                            }
                        }
                    }
                    .padding(.top, 14)
                    .padding(.bottom, 80)
                }
            }
        }
    }
    
    private func modeIcon(_ mode: String) -> String {
        switch mode {
        case "SOLO SURVIVAL": return "👤"
        case "DUO SQUAD": return "👥"
        default: return "🏛️"
        }
    }
    
    private func simulateLaunch() {
        isLaunching = true
        launchProgress = 0.1
        launchStepText = "CONNECTING TO LOGINAPP GATEWAY..."
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.launchProgress = 0.4
            self.launchStepText = "AUTHENTICATING 56-BYTE SESSION TOKEN..."
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.launchProgress = 0.75
            self.launchStepText = "DEMUXING MERCURY BASEAPP UDP HANDSHAKE..."
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.6) {
            self.launchProgress = 1.0
            self.isLaunching = false
            self.isSessionActive = true
            self.launchStepText = "READY"
        }
    }
}
