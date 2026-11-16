import SwiftUI

public struct GameDownloadScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @StateObject private var downloadVM = DownloadViewModel()
    
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
                    Text("CLIENT DISTRIBUTION")
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
                    VStack(spacing: 18) {
                        // Package Card
                        TacticalCard(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: 14) {
                                HStack(alignment: .top) {
                                    ZStack {
                                        RoundedRectangle(cornerRadius: 10)
                                            .fill(TacticalTheme.bgSecondary)
                                            .frame(width: 52, height: 52)
                                            .overlay(
                                                RoundedRectangle(cornerRadius: 10)
                                                    .stroke(TacticalTheme.borderGold, lineWidth: 1)
                                            )
                                        Text("📦")
                                            .font(.system(size: 26))
                                    }
                                    
                                    VStack(alignment: .leading, spacing: 3) {
                                        HStack {
                                            Text("ROS LEGACY CLIENT")
                                                .font(.system(size: 15, weight: .black))
                                                .foregroundColor(TacticalTheme.textPrimary)
                                            StatusBadge("v\(launcherVM.gameVersion.version)", variant: .gold)
                                        }
                                        Text("Preserved Original ARM64 iOS Binary")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                        Text("Build \(launcherVM.gameVersion.buildNumber) • \(String(format: "%.1f", launcherVM.gameVersion.clientSizeMB)) MB")
                                            .font(.system(size: 10, design: .monospaced))
                                            .foregroundColor(TacticalTheme.textMuted)
                                    }
                                    Spacer()
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                // Progress or Action
                                switch downloadVM.downloadState {
                                case .notStarted:
                                    PrimaryButton("DOWNLOAD CLIENT PACKAGE", icon: "📥") {
                                        downloadVM.startSimulatedDownload()
                                    }
                                    
                                case .downloading(let progress, _):
                                    VStack(spacing: 8) {
                                        HStack {
                                            Text("DOWNLOADING ASSETS...")
                                                .font(.system(size: 11, weight: .bold))
                                                .foregroundColor(TacticalTheme.gold)
                                            Spacer()
                                            Text(downloadVM.speedText)
                                                .font(.system(size: 11, design: .monospaced))
                                                .foregroundColor(TacticalTheme.textSecondary)
                                        }
                                        
                                        ProgressView(value: progress)
                                            .progressViewStyle(LinearProgressViewStyle(tint: TacticalTheme.gold))
                                            .scaleEffect(x: 1, y: 2, anchor: .center)
                                    }
                                    
                                case .verifyingChecksum:
                                    HStack {
                                        ProgressView()
                                            .progressViewStyle(CircularProgressViewStyle(tint: TacticalTheme.gold))
                                        Text("VERIFYING SHA-256 CHECKSUM INTEGRITY...")
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                    }
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 8)
                                    
                                case .verifiedReady:
                                    VStack(spacing: 8) {
                                        HStack {
                                            Text("✓")
                                                .foregroundColor(TacticalTheme.success)
                                                .font(.system(size: 16, weight: .bold))
                                            Text("PACKAGE VERIFIED & READY FOR SIDELOADING")
                                                .font(.system(size: 11, weight: .bold))
                                                .foregroundColor(TacticalTheme.success)
                                        }
                                        
                                        SecondaryButton("OPEN INSTALLATION GUIDE", icon: "📖") {
                                            launcherVM.navigateTo(.installationGuide)
                                        }
                                    }
                                    
                                case .error(let msg):
                                    Text(msg)
                                        .font(.system(size: 12))
                                        .foregroundColor(TacticalTheme.danger)
                                }
                            }
                        }
                        .padding(.horizontal, 16)
                        
                        // SHA-256 Verification Box
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack {
                                    Text("🛡️ SHA-256 VERIFICATION HASH")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    StatusBadge("AUTHENTIC", variant: .beta)
                                }
                                
                                Text(launcherVM.gameVersion.sha256Checksum)
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                    .padding(8)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(TacticalTheme.bgPrimary)
                                    .cornerRadius(4)
                                
                                Text("Cryptographic digest verifies byte-for-byte authenticity against the golden archive.")
                                    .font(.system(size: 10))
                                    .foregroundColor(TacticalTheme.textMuted)
                            }
                        }
                        .padding(.horizontal, 16)
                        
                        // Ad Hoc Security Notice
                        TacticalCard {
                            HStack(alignment: .top, spacing: 10) {
                                Text("⚠️")
                                    .font(.system(size: 18))
                                VStack(alignment: .leading, spacing: 4) {
                                    Text("AD HOC SIGNING REQUIREMENT")
                                        .font(.system(size: 11, weight: .bold))
                                        .foregroundColor(TacticalTheme.warning)
                                    Text("Apple iOS security enforces strict app sandboxing. The launcher cannot silently install IPA packages without user-guided sideloading (AltStore or Sideloadly).")
                                        .font(.system(size: 10))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                        .lineSpacing(2)
                                }
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
