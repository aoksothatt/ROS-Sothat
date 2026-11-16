import SwiftUI

public struct InstallationGuideScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @State private var selectedMethod: Int = 0 // 0 = AltStore, 1 = Sideloadly, 2 = Xcode
    
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
                    Text("INSTALLATION GUIDE")
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
                
                // Method Tabs
                HStack(spacing: 8) {
                    GuideTabButton(title: "AltStore", isSelected: selectedMethod == 0) {
                        selectedMethod = 0
                    }
                    GuideTabButton(title: "Sideloadly", isSelected: selectedMethod == 1) {
                        selectedMethod = 1
                    }
                    GuideTabButton(title: "Xcode (Mac)", isSelected: selectedMethod == 2) {
                        selectedMethod = 2
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                
                ScrollView {
                    VStack(spacing: 16) {
                        // Guide Steps based on method
                        if selectedMethod == 0 {
                            GuideStepCard(step: "1", title: "Install AltServer", desc: "Download AltServer from altstore.io on Mac or Windows PC. Ensure iTunes and iCloud are installed.")
                            GuideStepCard(step: "2", title: "Connect via USB", desc: "Connect iPhone/iPad to PC, click AltServer in system tray, and choose 'Install AltStore' with your Apple ID.")
                            GuideStepCard(step: "3", title: "Load ROS IPA", desc: "Download the launcher IPA, open AltStore on iOS, tap '+' in My Apps, and select the package.")
                        } else if selectedMethod == 1 {
                            GuideStepCard(step: "1", title: "Open Sideloadly", desc: "Download sideloadly.io on PC/Mac. Connect device via USB and trust computer.")
                            GuideStepCard(step: "2", title: "Drag & Drop IPA", desc: "Drag ROSSothatLauncher.ipa into Sideloadly window.")
                            GuideStepCard(step: "3", title: "Start Sideload", desc: "Enter your personal Apple ID and click 'Start' to sign and install.")
                        } else {
                            GuideStepCard(step: "1", title: "Open in Xcode", desc: "Open ROSSothatLauncher.xcodeproj on macOS Sonoma/Sequoia with Xcode 15+.")
                            GuideStepCard(step: "2", title: "Select Team", desc: "In Signing & Capabilities, select your Personal Apple Developer team.")
                            GuideStepCard(step: "3", title: "Run (Cmd + R)", desc: "Select connected iPhone/iPad and compile directly to device.")
                        }
                        
                        // Critical System Instructions
                        TacticalCard(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: 12) {
                                HStack(spacing: 6) {
                                    Image(systemName: "gearshape.fill")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.gold)
                                    Text("MANDATORY SYSTEM SETTINGS")
                                        .font(.system(size: 11, weight: .black))
                                        .foregroundColor(TacticalTheme.gold)
                                }
                                
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("A. Trust Developer Certificate")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(TacticalTheme.textPrimary)
                                    Text("Settings > General > VPN & Device Management > Tap your Apple ID > Trust")
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("B. Developer Mode (iOS 16+)")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(TacticalTheme.textPrimary)
                                    Text("Settings > Privacy & Security > Developer Mode > Toggle ON > Restart")
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                    }
                    .padding(.top, 6)
                    .padding(.bottom, 80)
                }
            }
        }
    }
}

struct GuideTabButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 11, weight: .bold))
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .frame(maxWidth: .infinity)
                .background(isSelected ? TacticalTheme.gold : TacticalTheme.bgCard)
                .foregroundColor(isSelected ? TacticalTheme.bgPrimary : TacticalTheme.textSecondary)
                .cornerRadius(3)
                .overlay(
                    RoundedRectangle(cornerRadius: 3)
                        .stroke(isSelected ? TacticalTheme.gold : TacticalTheme.border, lineWidth: 1)
                )
        }
    }
}

struct GuideStepCard: View {
    let step: String
    let title: String
    let desc: String
    
    var body: some View {
        TacticalCard {
            HStack(spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 3)
                        .fill(TacticalTheme.bgSecondary)
                        .frame(width: 32, height: 32)
                        .overlay(
                            RoundedRectangle(cornerRadius: 3)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    Text(step)
                        .font(.system(size: 13, weight: .black))
                        .foregroundColor(TacticalTheme.gold)
                }
                
                VStack(alignment: .leading, spacing: 3) {
                    Text(title)
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(TacticalTheme.textPrimary)
                    Text(desc)
                        .font(.system(size: 11))
                        .foregroundColor(TacticalTheme.textSecondary)
                        .lineSpacing(2)
                }
            }
        }
        .padding(.horizontal, 16)
    }
}
