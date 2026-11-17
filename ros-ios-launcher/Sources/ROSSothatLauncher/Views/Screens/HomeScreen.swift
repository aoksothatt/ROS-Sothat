import SwiftUI

public struct HomeScreen: View {
    @EnvironmentObject public var serverConfig: ServerConfig
    @EnvironmentObject public var downloadVM: DownloadViewModel
    @EnvironmentObject public var authVM: AuthViewModel

    @State private var showSettings: Bool = false
    @State private var showInstallGuide: Bool = false

    public init() {}

    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()

            // Subtle ambient gold radial glow centered behind hero
            RadialGradient(
                gradient: Gradient(colors: [
                    TacticalTheme.gold.opacity(0.06),
                    Color.clear
                ]),
                center: .center,
                startRadius: 30,
                endRadius: 260
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {
                // MARK: - 1. Top Bar: Dynamic Connection Status & Settings Button
                HStack {
                    // Dynamic Private Server Health Status Capsule
                    HStack(spacing: 6) {
                        Circle()
                            .fill(statusDotColor)
                            .frame(width: 6, height: 6)

                        Text(serverConfig.healthStatus.displayText)
                            .font(.system(size: 9, weight: .bold, design: .monospaced))
                            .tracking(1.2)
                            .foregroundColor(statusTextColor)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(TacticalTheme.bgCard)
                    .cornerRadius(12)
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(TacticalTheme.borderGold, lineWidth: 0.8)
                    )

                    Spacer()

                    // Small Settings Button
                    Button(action: { showSettings = true }) {
                        ZStack {
                            Circle()
                                .fill(TacticalTheme.bgCard)
                                .frame(width: 36, height: 36)
                                .overlay(
                                    Circle()
                                        .stroke(TacticalTheme.borderGold, lineWidth: 0.8)
                                )

                            Image(systemName: "gearshape.fill")
                                .font(.system(size: 14, weight: .medium))
                                .foregroundColor(TacticalTheme.gold)
                        }
                    }
                    .buttonStyle(ScaleButtonStyle())
                    .accessibilityLabel("Settings")
                }
                .padding(.horizontal, 24)
                .padding(.top, 14)

                Spacer(minLength: 20)

                // MARK: - 2. Center Hero: Logo & Minimal Title
                VStack(spacing: 18) {
                    // Existing ROS Sothatt launcher logo
                    Image("Logo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 140, height: 140)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                        .overlay(
                            RoundedRectangle(cornerRadius: 16)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                        .shadow(color: Color.black.opacity(0.6), radius: 14, x: 0, y: 8)

                    // Minimal Game Identity / Title Area
                    VStack(spacing: 6) {
                        HStack(spacing: 8) {
                            Text("ROS")
                                .font(.system(size: 28, weight: .black))
                                .tracking(3.0)
                                .foregroundColor(TacticalTheme.textPrimary)

                            Text("SOTHATT")
                                .font(.system(size: 28, weight: .black))
                                .tracking(3.0)
                                .foregroundColor(TacticalTheme.gold)
                        }

                        Text("PRIVATE SERVER LAUNCHER")
                            .font(.system(size: 10, weight: .bold))
                            .tracking(3.0)
                            .foregroundColor(TacticalTheme.textSecondary)

                        // Subtle gold separator accent
                        Rectangle()
                            .fill(TacticalTheme.goldGradient)
                            .frame(width: 36, height: 1.5)
                            .cornerRadius(0.75)
                            .padding(.top, 4)
                    }
                }

                Spacer(minLength: 30)

                // MARK: - 3. Prominent Gold Action Button (PLAY / HOW TO INSTALL)
                VStack(spacing: 12) {
                    Button(action: handlePlayAction) {
                        HStack(spacing: 10) {
                            Image(systemName: playButtonIcon)
                                .font(.system(size: 16, weight: .black))
                                .foregroundColor(TacticalTheme.bgPrimary)

                            Text(playButtonTitle)
                                .font(.system(size: 16, weight: .black))
                                .tracking(2.5)
                                .foregroundColor(TacticalTheme.bgPrimary)
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(TacticalTheme.goldGradient)
                        .cornerRadius(28)
                        .overlay(
                            RoundedRectangle(cornerRadius: 28)
                                .stroke(Color.white.opacity(0.25), lineWidth: 1)
                        )
                        .shadow(color: TacticalTheme.gold.opacity(0.35), radius: 14, x: 0, y: 6)
                    }
                    .buttonStyle(ScaleButtonStyle())

                    // Auxiliary hint when game is not detected
                    if !downloadVM.isGameInstalled {
                        HStack(spacing: 4) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.system(size: 10))
                                .foregroundColor(TacticalTheme.warning)
                            Text("Original game client required on device")
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundColor(TacticalTheme.textMuted)
                        }
                        .padding(.top, 2)
                    }
                }
                .padding(.horizontal, 32)
                .padding(.bottom, 22)

                // MARK: - 4. Discreet Version Label at Bottom
                Text("v1.0.0 (Build 102) • ROS Sothatt")
                    .font(.system(size: 10, weight: .medium, design: .monospaced))
                    .tracking(1.0)
                    .foregroundColor(TacticalTheme.textMuted)
                    .padding(.bottom, 12)
            }
        }
        .sheet(isPresented: $showSettings) {
            SettingsScreen()
                .environmentObject(serverConfig)
                .environmentObject(downloadVM)
                .environmentObject(authVM)
        }
        .sheet(isPresented: $showInstallGuide) {
            InstallationGuideScreen()
                .environmentObject(downloadVM)
        }
        .onAppear {
            serverConfig.startPolling()
            downloadVM.checkGameInstallation()
        }
        .onDisappear {
            serverConfig.stopPolling()
        }
    }

    // MARK: - Dynamic Status Styles

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
            return TacticalTheme.gold
        case .connecting:
            return TacticalTheme.textSecondary
        case .offline:
            return Color.red.opacity(0.85)
        }
    }

    // MARK: - Play Action Logic

    private var playButtonTitle: String {
        if downloadVM.isGameInstalled {
            return "PLAY"
        } else {
            return "HOW TO INSTALL"
        }
    }

    private var playButtonIcon: String {
        if downloadVM.isGameInstalled {
            return "play.fill"
        } else {
            return "info.circle.fill"
        }
    }

    private func handlePlayAction() {
        if downloadVM.isGameInstalled {
            downloadVM.launchGame()
        } else {
            showInstallGuide = true
        }
    }
}

// MARK: - Smooth Scale Button Style
struct ScaleButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.96 : 1.0)
            .animation(.easeInOut(duration: 0.15), value: configuration.isPressed)
    }
}
