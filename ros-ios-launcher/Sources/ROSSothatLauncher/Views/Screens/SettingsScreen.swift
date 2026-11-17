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
    @State private var showGuideSheet: Bool = false
    @State private var isTestingConnection: Bool = false

    public init() {}

    public var body: some View {
        NavigationView {
            ZStack {
                TacticalTheme.bgPrimary.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 20) {
                        // Section 1: Private Server Configuration & Live Health
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
                                        CustomTextField("8000", icon: "number", text: $portInput)
                                            .frame(width: 90)
                                    }
                                }

                                Divider().background(TacticalTheme.border)

                                HStack {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text("Server Health Status:")
                                            .font(.system(size: 10))
                                            .foregroundColor(TacticalTheme.textMuted)
                                        HStack(spacing: 6) {
                                            Circle()
                                                .fill(statusDotColor)
                                                .frame(width: 6, height: 6)
                                            Text(serverConfig.healthStatus.displayText)
                                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                                .foregroundColor(statusTextColor)
                                        }
                                    }
                                    Spacer()
                                    Button(action: saveAndTestConnection) {
                                        HStack(spacing: 4) {
                                            if isTestingConnection {
                                                ProgressView()
                                                    .progressViewStyle(CircularProgressViewStyle(tint: TacticalTheme.gold))
                                                    .scaleEffect(0.7)
                                            }
                                            Text(isTestingConnection ? "TESTING..." : "APPLY & TEST")
                                                .font(.system(size: 10, weight: .bold))
                                                .foregroundColor(TacticalTheme.gold)
                                        }
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 7)
                                        .background(TacticalTheme.gold.opacity(0.12))
                                        .cornerRadius(4)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 4)
                                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                                        )
                                    }
                                    .disabled(isTestingConnection)
                                }
                            }
                        }

                        // Section 2: Game Client Package & Installation
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

                                Button(action: { showGuideSheet = true }) {
                                    HStack {
                                        Image(systemName: "book.fill")
                                            .font(.system(size: 11))
                                        Text("VIEW INSTALLATION INSTRUCTIONS")
                                            .font(.system(size: 10, weight: .bold))
                                            .tracking(1.0)
                                        Spacer()
                                        Image(systemName: "chevron.right")
                                            .font(.system(size: 10))
                                    }
                                    .foregroundColor(TacticalTheme.gold)
                                    .padding(.vertical, 8)
                                    .padding(.horizontal, 10)
                                    .background(TacticalTheme.bgPrimary)
                                    .cornerRadius(4)
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 4)
                                            .stroke(TacticalTheme.border, lineWidth: 1)
                                    )
                                }

                                VStack(alignment: .leading, spacing: 4) {
                                    Text("PACKAGE DOWNLOAD URL")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    CustomTextField("https://...", icon: "link", text: $downloadUrlInput)
                                }

                                if case .completed(_, let sizeStr) = downloadVM.status {
                                    Divider().background(TacticalTheme.border)

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
                                                .padding(.horizontal, 14)
                                                .padding(.vertical, 8)
                                                .background(TacticalTheme.goldGradient)
                                                .cornerRadius(4)
                                            }

                                            Button(action: { downloadVM.deleteLocalFile() }) {
                                                HStack(spacing: 6) {
                                                    Image(systemName: "trash")
                                                    Text("DELETE")
                                                }
                                                .font(.system(size: 11, weight: .bold))
                                                .foregroundColor(TacticalTheme.warning)
                                                .padding(.horizontal, 14)
                                                .padding(.vertical, 8)
                                                .background(TacticalTheme.warning.opacity(0.12))
                                                .cornerRadius(4)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Section 3: Player Profile
                        settingsCard(title: "OPERATOR CALLSIGN", systemIcon: "person.crop.circle.badge.checkmark") {
                            VStack(alignment: .leading, spacing: 10) {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("CALLSIGN")
                                        .font(.system(size: 9, weight: .bold))
                                        .foregroundColor(TacticalTheme.textMuted)
                                    CustomTextField("DEV_TESTER_IPHONE", icon: "person.text.rectangle", text: $callsignInput)
                                }

                                Button(action: { authVM.callsign = callsignInput.trimmingCharacters(in: .whitespaces) }) {
                                    Text("SAVE CALLSIGN")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                        .padding(.horizontal, 14)
                                        .padding(.vertical, 7)
                                        .background(TacticalTheme.gold.opacity(0.12))
                                        .cornerRadius(4)
                                }
                            }
                        }

                        // Section 4: Technical Diagnostics
                        settingsCard(title: "TECHNICAL DIAGNOSTICS", systemIcon: "wrench.and.screwdriver.fill") {
                            VStack(alignment: .leading, spacing: 8) {
                                diagnosticRow(label: "Bundle Identifier", value: "com.rossothat.launcher")
                                diagnosticRow(label: "Launcher Version", value: "1.0.0 (Build 102)")
                                diagnosticRow(label: "Health Endpoint", value: serverConfig.healthURL?.path ?? "/health")
                                diagnosticRow(label: "Measured Latency", value: serverConfig.latencyMs.map { "\($0) ms" } ?? "None")
                                diagnosticRow(label: "Registered URL Scheme", value: "rosmobile://")
                                diagnosticRow(label: "Game Detection", value: downloadVM.isGameInstalled ? "POSITIVE" : "NOT DETECTED")
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
        .sheet(isPresented: $showGuideSheet) {
            InstallationGuideScreen()
                .environmentObject(downloadVM)
        }
        .onAppear {
            hostInput = serverConfig.serverHost
            portInput = String(serverConfig.serverPort)
            downloadUrlInput = serverConfig.downloadSourceURL
            callsignInput = authVM.callsign
        }
    }

    private var statusDotColor: Color {
        switch serverConfig.healthStatus {
        case .online:
            return TacticalTheme.success
        case .connecting:
            return TacticalTheme.gold
        case .offline:
            return Color.red
        }
    }

    private var statusTextColor: Color {
        switch serverConfig.healthStatus {
        case .online:
            return TacticalTheme.success
        case .connecting:
            return TacticalTheme.gold
        case .offline:
            return Color.red.opacity(0.85)
        }
    }

    private func saveAndTestConnection() {
        serverConfig.serverHost = hostInput.trimmingCharacters(in: .whitespaces)
        if let port = Int(portInput.trimmingCharacters(in: .whitespaces)) {
            serverConfig.serverPort = port
        }
        serverConfig.apiBaseURL = "http://\(serverConfig.serverHost):\(serverConfig.serverPort)"
        serverConfig.downloadSourceURL = downloadUrlInput.trimmingCharacters(in: .whitespaces)

        isTestingConnection = true
        Task {
            await serverConfig.checkHealthNow()
            isTestingConnection = false
        }
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
