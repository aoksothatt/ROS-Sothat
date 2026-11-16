import SwiftUI

public struct AccountScreen: View {
    @EnvironmentObject public var serverConfig: ServerConfig
    @EnvironmentObject public var authVM: AuthViewModel
    
    @State private var callsignInput: String = ""
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Top Header Bar
                HStack {
                    Text("OPERATOR ACCOUNT")
                        .font(.system(size: 11, weight: .bold))
                        .tracking(1.4)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    if authVM.isAuthenticated {
                        StatusBadge("ACTIVE", variant: .online)
                    } else {
                        StatusBadge("GUEST", variant: .beta)
                    }
                }
                .padding(.horizontal, 20)
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
                        // Operator Profile Card
                        TacticalCard(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack(spacing: 6) {
                                    Image(systemName: "person.crop.circle.fill")
                                        .font(.system(size: 14))
                                        .foregroundColor(TacticalTheme.gold)
                                    Text("OPERATOR IDENTITY")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(TacticalTheme.textPrimary)
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                if authVM.isAuthenticated {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("Active Callsign:")
                                            .font(.system(size: 10))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        Text(authVM.callsign.uppercased())
                                            .font(.system(size: 16, weight: .black))
                                            .foregroundColor(TacticalTheme.gold)
                                    }
                                    
                                    SecondaryButton("SIGN OUT", systemImage: "rectangle.portrait.and.arrow.right") {
                                        authVM.signOut()
                                    }
                                    .padding(.top, 4)
                                } else {
                                    VStack(alignment: .leading, spacing: 8) {
                                        Text("SET CALLSIGN")
                                            .font(.system(size: 9, weight: .bold))
                                            .tracking(1.0)
                                            .foregroundColor(TacticalTheme.textMuted)
                                        
                                        CustomTextField("OperatorCallsign", icon: "person.fill", text: $callsignInput)
                                        
                                        PrimaryButton("SAVE OPERATOR CALLSIGN", systemImage: "checkmark") {
                                            authVM.callsign = callsignInput
                                            authVM.authenticate(serverConfig: serverConfig)
                                        }
                                        .padding(.top, 4)
                                    }
                                }
                            }
                        }
                        
                        // Private Server Architecture Card
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack(spacing: 6) {
                                    Image(systemName: "server.rack")
                                        .font(.system(size: 12))
                                        .foregroundColor(TacticalTheme.gold)
                                    Text("PRIVATE SERVER ARCHITECTURE")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                VStack(spacing: 6) {
                                    HStack {
                                        Text("Server Host:")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        Spacer()
                                        Text(serverConfig.serverHost)
                                            .font(.system(size: 11, design: .monospaced))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                    }
                                    HStack {
                                        Text("Game Port:")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        Spacer()
                                        Text("\(serverConfig.serverPort)")
                                            .font(.system(size: 11, design: .monospaced))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                    }
                                    HStack {
                                        Text("API Gateway:")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        Spacer()
                                        Text(serverConfig.apiBaseURL)
                                            .font(.system(size: 10, design: .monospaced))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                    }
                                }
                                
                                Text("Architecture ready. Backend endpoints will connect seamlessly when the real private server infrastructure goes live.")
                                    .font(.system(size: 10))
                                    .foregroundColor(TacticalTheme.textMuted)
                                    .padding(.top, 2)
                            }
                        }
                    }
                    .padding(20)
                }
            }
        }
        .onAppear {
            if !authVM.callsign.isEmpty {
                callsignInput = authVM.callsign
            }
        }
    }
}
