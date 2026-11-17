import SwiftUI

public struct InstallationGuideScreen: View {
    @Environment(\.presentationMode) var presentationMode
    @EnvironmentObject public var downloadVM: DownloadViewModel

    @State private var checkStatusMessage: String? = nil

    public init() {}

    public var body: some View {
        NavigationView {
            ZStack {
                TacticalTheme.bgPrimary.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 20) {
                        // Header Banner
                        VStack(spacing: 8) {
                            Image(systemName: "info.circle.fill")
                                .font(.system(size: 32))
                                .foregroundColor(TacticalTheme.gold)

                            Text("GAME INSTALLATION REQUIRED")
                                .font(.system(size: 14, weight: .black, design: .monospaced))
                                .tracking(1.8)
                                .foregroundColor(TacticalTheme.textPrimary)

                            Text("Original Rules of Survival Legacy client is not installed.")
                                .font(.system(size: 11))
                                .foregroundColor(TacticalTheme.textMuted)
                                .multilineTextAlignment(.center)
                        }
                        .padding(.top, 10)

                        // Technical Sandbox Transparency Notice
                        TacticalCard(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack(spacing: 6) {
                                    Image(systemName: "lock.shield.fill")
                                        .font(.system(size: 12))
                                        .foregroundColor(TacticalTheme.gold)
                                    Text("APPLE IOS SANDBOX TRANSPARENCY")
                                        .font(.system(size: 10, weight: .bold))
                                        .tracking(1.0)
                                        .foregroundColor(TacticalTheme.gold)
                                }

                                Text("Under Apple iOS security architecture, applications run in strictly isolated sandboxes. A launcher app has no system permission to install an .ipa archive directly. The game client must be sideloaded onto your iOS device using standard Apple-supported or community tools.")
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                    .lineSpacing(3)
                            }
                        }

                        // Step-by-Step Installation Instructions
                        VStack(spacing: 12) {
                            stepCard(
                                stepNumber: "1",
                                title: "OBTAIN THE GAME PACKAGE",
                                description: "Download the verified RoS-Legacy-iOS.ipa package from the ROS Sothatt web portal or your server distribution share."
                            )

                            stepCard(
                                stepNumber: "2",
                                title: "SIDELOAD ONTO YOUR IPHONE",
                                description: "Install the IPA using your preferred sideloading method:\n• Sideloadly (USB install via Windows / macOS)\n• AltStore (Local on-device signing via free Apple ID)\n• TrollStore (Permanent install on iOS 15.0–16.6.1)\n• Apple Ad Hoc OTA (Safari install if your device UDID is pre-enrolled)"
                            )

                            stepCard(
                                stepNumber: "3",
                                title: "TRUST DEVELOPER CERTIFICATE",
                                description: "Go to iOS Settings > General > VPN & Device Management > Tap your signing certificate profile and select 'Trust'."
                            )

                            stepCard(
                                stepNumber: "4",
                                title: "RETURN & TAP PLAY",
                                description: "Once installed on your home screen, the game registers custom URL scheme rosmobile://. The launcher will automatically detect it and enable the PLAY button."
                            )
                        }

                        // Check Installation Status Button
                        VStack(spacing: 10) {
                            Button(action: verifyInstallation) {
                                HStack(spacing: 8) {
                                    Image(systemName: "arrow.clockwise")
                                        .font(.system(size: 13, weight: .bold))
                                    Text("CHECK INSTALLATION NOW")
                                        .font(.system(size: 13, weight: .black))
                                        .tracking(1.4)
                                }
                                .frame(maxWidth: .infinity)
                                .frame(height: 50)
                                .background(TacticalTheme.goldGradient)
                                .foregroundColor(TacticalTheme.bgPrimary)
                                .cornerRadius(25)
                                .shadow(color: TacticalTheme.gold.opacity(0.3), radius: 8, x: 0, y: 4)
                            }

                            if let msg = checkStatusMessage {
                                Text(msg)
                                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                                    .foregroundColor(downloadVM.isGameInstalled ? TacticalTheme.success : TacticalTheme.warning)
                                    .padding(.top, 4)
                            }
                        }
                        .padding(.top, 10)
                        .padding(.bottom, 20)
                    }
                    .padding(.horizontal, 20)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("INSTALLATION INSTRUCTIONS")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .tracking(1.2)
                        .foregroundColor(TacticalTheme.gold)
                }
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("DONE") {
                        presentationMode.wrappedValue.dismiss()
                    }
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(TacticalTheme.gold)
                }
            }
        }
        .onAppear {
            downloadVM.checkGameInstallation()
        }
    }

    private func verifyInstallation() {
        downloadVM.checkGameInstallation()
        if downloadVM.isGameInstalled {
            checkStatusMessage = "SUCCESS: ROS Legacy detected (rosmobile:// ready)!"
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                presentationMode.wrappedValue.dismiss()
            }
        } else {
            checkStatusMessage = "Game not detected yet. Please ensure the app is installed on your home screen."
        }
    }

    private func stepCard(stepNumber: String, title: String, description: String) -> some View {
        HStack(alignment: .top, spacing: 14) {
            ZStack {
                Circle()
                    .fill(TacticalTheme.bgCard)
                    .frame(width: 28, height: 28)
                    .overlay(
                        Circle().stroke(TacticalTheme.borderGold, lineWidth: 1)
                    )
                Text(stepNumber)
                    .font(.system(size: 12, weight: .black, design: .monospaced))
                    .foregroundColor(TacticalTheme.gold)
            }
            .padding(.top, 2)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 11, weight: .bold))
                    .tracking(0.8)
                    .foregroundColor(TacticalTheme.textPrimary)

                Text(description)
                    .font(.system(size: 11))
                    .foregroundColor(TacticalTheme.textSecondary)
                    .lineSpacing(2.5)
            }
            Spacer()
        }
        .padding(14)
        .background(TacticalTheme.bgCard)
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(TacticalTheme.border, lineWidth: 1)
        )
    }
}
