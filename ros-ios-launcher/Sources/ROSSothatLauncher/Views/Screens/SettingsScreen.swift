import SwiftUI

public struct SettingsScreen: View {
    @Environment(\.presentationMode) var presentationMode
    @EnvironmentObject public var serverConfig: ServerConfig
    @EnvironmentObject public var downloadVM: DownloadViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    @State private var hostInput: String = ""
    @State private var portInput: String = ""
    @State private var downloadUrlInput: String = ""
    @State private var callsignInput: String = ""
    @State private var showShareSheet: Bool = false
    @State private var showSaveAlert: Bool = false
    
    public init() {}
    
    public var body: some View {
        NavigationView {
            ZStack {
                TacticalTheme.bgPrimary.ignoresSafeArea()
                
                ScrollView {
                    VStack(spacing: 20) {
                        // Section 1: Private Server Configuration
                        settingsCard(title: "PRIVATE SERVER CONFIGURATION", systemIcon: "server.rack") {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack(spacing: 12) {
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("SERVER HOST")
                                            .font(.system(size: 9, weight: .bold))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        CustomTextField("127.0.0.1", icon: "network", text: $hostInput)
                                    }
                                    
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text("PORT")
                                            .font(.system(size: 9, weight: .bold))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        CustomTextField("20014", icon: "number", text: $portInput)
                                            .frame(width: 90)
                                    }
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text("Server Status:")
                                            .font(.system(size: 10))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        HStack(spacing: 6) {
                                            Circle()
                                                .fill(TacticalTheme.success)
                                                .frame(width: 6, height: 6)
                                            Text(serverConfig.isConnected ? "CONNECTED" : "ONLINE • READY")
                                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                                .foregroundColor(TacticalTheme.success)
                                        }
                                    }
                                    Spacer()
                                    Button(action: saveServerConfig) {
                                        Text("APPLY")
                                            .font(.system(size: 10, weight: .bold))
                                            .foregroundColor(TacticalTheme.gold)
                                            .padding(.horizontal, 14)
                                            .padding(.vertical, 7)
                                            .background(TacticalTheme.gold.opacity(0.12))
                                            .cornerRadius(4)
                                            .overlay(
                                                RoundedRectangle(cornerRadius: 4)
                                                    .stroke(TacticalTheme.borderGold, lineWidth: 1)
                                            )
                                    }
                                }
                            }
                        }
                        
                        // Section 2: Game Client Package & Sideloading
                        settingsCard(title: "GAME PACKAGE & INSTALLATION", systemIcon: "shippingbox.fill") {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack {
                                    Text("Client Installation:")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    Spacer()
                                    Text(downloadVM.isGameInstalled ? "INSTALLED (rosmobile://)" : "NOT INSTALLED")
                                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                                        .foregroundColor(downloadVM.isGameInstalled ? TacticalTheme.success : TacticalTheme.warning)
                                }
                                
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("PACKAGE DOWNLOAD URL")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    CustomTextField("https://...", icon: "link", text: $downloadUrlInput)
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                if case .completed(_, let sizeStr) = downloadVM.status {
                                    VStack(alignment: .leading, spacing: 8) {
                                        HStack {
                                            Text("Cached Archive:")
                                                .font(.system(size: 11))
                                                .foregroundColor(TacticalTheme.textMuted)
                                            Spacer()
                                            Text(sizeStr)
                                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                                .foregroundColor(TacticalTheme.textPrimary)
                                        }
                                        
                                        HStack(spacing: 10) {
                                            Button(action: { showShareSheet = true }) {
                                                HStack(spacing: 6) {
                                                    Image(systemName: "square.and.arrow.up")
                                                    Text("EXPORT IPA")
                                                }
                                                .font(.system(size: 11, weight: .bold))
                                                .foregroundColor(TacticalTheme.bgPrimary)
                                                .frame(maxWidth: .infinity)
                                                .frame(height: 38)
                                                .background(TacticalTheme.gold)
                                                .cornerRadius(4)
                                            }
                                            
                                            Button(action: { downloadVM.deleteLocalFile() }) {
                                                HStack(spacing: 6) {
                                                    Image(systemName: "trash")
                                                    Text("DELETE")
                                                }
                                                .font(.system(size: 11, weight: .bold))
                                                .foregroundColor(TacticalTheme.danger)
                                                .frame(width: 86)
                                                .frame(height: 38)
                                                .background(TacticalTheme.danger.opacity(0.12))
                                                .cornerRadius(4)
                                                .overlay(
                                                    RoundedRectangle(cornerRadius: 4)
                                                        .stroke(TacticalTheme.danger.opacity(0.3), lineWidth: 1)
                                                )
                                            }
                                        }
                                    }
                                } else if case .downloading(let progress, _, _, let speed) = downloadVM.status {
                                    VStack(spacing: 8) {
                                        ProgressView(value: progress)
                                            .accentColor(TacticalTheme.gold)
                                        HStack {
                                            Text(downloadVM.progressText)
                                                .font(.system(size: 10, design: .monospaced))
                                                .foregroundColor(TacticalTheme.textMuted)
                                            Spacer()
                                            Text(speed)
                                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                                .foregroundColor(TacticalTheme.gold)
                                        }
                                        Button(action: { downloadVM.cancelDownload() }) {
                                            Text("CANCEL DOWNLOAD")
                                                .font(.system(size: 10, weight: .bold))
                                                .foregroundColor(TacticalTheme.danger)
                                                .padding(.top, 4)
                                        }
                                    }
                                } else {
                                    Button(action: {
                                        if let url = serverConfig.downloadURL {
                                            downloadVM.startDownload(from: url)
                                        }
                                    }) {
                                        HStack(spacing: 6) {
                                            Image(systemName: "arrow.down.to.line")
                                            Text("DOWNLOAD GAME PACKAGE (806 MB)")
                                        }
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 40)
                                        .background(TacticalTheme.bgCard)
                                        .cornerRadius(4)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 4)
                                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                                        )
                                    }
                                }
                            }
                        }
                        
                        // Section 3: Operator Identity
                        settingsCard(title: "OPERATOR IDENTITY", systemIcon: "person.crop.circle.fill") {
                            VStack(alignment: .leading, spacing: 10) {
                                if authVM.isAuthenticated {
                                    HStack {
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text("ACTIVE CALLSIGN")
                                                .font(.system(size: 9, weight: .bold))
                                                .foregroundColor(TacticalTheme.textMuted)
                                            Text(authVM.callsign.uppercased())
                                                .font(.system(size: 15, weight: .black))
                                                .foregroundColor(TacticalTheme.gold)
                                        }
                                        Spacer()
                                        Button(action: { authVM.signOut() }) {
                                            Text("SIGN OUT")
                                                .font(.system(size: 10, weight: .bold))
                                                .foregroundColor(TacticalTheme.danger)
                                                .padding(.horizontal, 10)
                                                .padding(.vertical, 5)
                                                .background(TacticalTheme.danger.opacity(0.12))
                                                .cornerRadius(4)
                                        }
                                    }
                                } else {
                                    VStack(alignment: .leading, spacing: 8) {
                                        Text("SET OPERATOR CALLSIGN")
                                            .font(.system(size: 9, weight: .bold))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        CustomTextField("Callsign", icon: "person.fill", text: $callsignInput)
                                        Button(action: {
                                            authVM.callsign = callsignInput
                                            authVM.authenticate(serverConfig: serverConfig)
                                        }) {
                                            Text("SAVE CALLSIGN")
                                                .font(.system(size: 10, weight: .bold))
                                                .foregroundColor(TacticalTheme.bgPrimary)
                                                .frame(maxWidth: .infinity)
                                                .frame(height: 36)
                                                .background(TacticalTheme.gold)
                                                .cornerRadius(4)
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Section 4: Technical Diagnostics
                        settingsCard(title: "TECHNICAL DIAGNOSTICS", systemIcon: "wrench.and.screwdriver.fill") {
                            VStack(alignment: .leading, spacing: 8) {
                                diagnosticRow(label: "Bundle Identifier", value: "com.rossothat.launcher")
                                diagnosticRow(label: "Launcher Version", value: "1.0.0 (Build 101)")
                                diagnosticRow(label: "Architecture", value: "arm64 (iOS 15.0+)")
                                diagnosticRow(label: "Private Server Architecture", value: "Mercury UDP")
                                diagnosticRow(label: "Local Storage Path", value: "Documents/ROSSothatGame.ipa")
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("SETTINGS")
                        .font(.system(size: 12, weight: .bold, design: .monospaced))
                        .tracking(1.4)
                        .foregroundColor(TacticalTheme.gold)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: { presentationMode.wrappedValue.dismiss() }) {
                        Text("DONE")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(TacticalTheme.gold)
                    }
                }
            }
        }
        .sheet(isPresented: $showShareSheet) {
            if let localURL = downloadVM.localFileURL {
                ShareSheet(items: [localURL])
            }
        }
        .onAppear {
            hostInput = serverConfig.serverHost
            portInput = String(serverConfig.serverPort)
            downloadUrlInput = serverConfig.downloadSourceURL
            callsignInput = authVM.callsign
        }
    }
    
    private func saveServerConfig() {
        serverConfig.serverHost = hostInput.trimmingCharacters(in: .whitespaces)
        if let port = Int(portInput.trimmingCharacters(in: .whitespaces)) {
            serverConfig.serverPort = port
        }
        serverConfig.downloadSourceURL = downloadUrlInput.trimmingCharacters(in: .whitespaces)
    }
    
    private func settingsCard<Content: View>(title: String, systemIcon: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: systemIcon)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(TacticalTheme.gold)
                Text(title)
                    .font(.system(size: 10, weight: .bold))
                    .tracking(1.2)
                    .foregroundColor(TacticalTheme.gold)
            }
            
            VStack(alignment: .leading, spacing: 10) {
                content()
            }
            .padding(14)
            .background(TacticalTheme.bgCard)
            .cornerRadius(4)
            .overlay(
                RoundedRectangle(cornerRadius: 4)
                    .stroke(TacticalTheme.borderGold, lineWidth: 1)
            )
        }
    }
    
    private func diagnosticRow(label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 11))
                .foregroundColor(TacticalTheme.textMuted)
            Spacer()
            Text(value)
                .font(.system(size: 11, design: .monospaced))
                .foregroundColor(TacticalTheme.textSecondary)
        }
    }
}
