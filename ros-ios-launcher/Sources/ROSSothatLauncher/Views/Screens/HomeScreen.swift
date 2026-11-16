import SwiftUI

public struct HomeScreen: View {
    @EnvironmentObject public var serverConfig: ServerConfig
    @EnvironmentObject public var downloadVM: DownloadViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    @State private var showShareSheet: Bool = false
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // MARK: - Top Status Bar
                HStack {
                    if authVM.isAuthenticated {
                        HStack(spacing: 6) {
                            Circle()
                                .fill(TacticalTheme.success)
                                .frame(width: 5, height: 5)
                            Text("OPERATOR // \(authVM.callsign.uppercased())")
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .tracking(0.8)
                                .foregroundColor(TacticalTheme.gold)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(TacticalTheme.bgCard)
                        .cornerRadius(3)
                        .overlay(
                            RoundedRectangle(cornerRadius: 3)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    } else {
                        HStack(spacing: 6) {
                            Circle()
                                .fill(TacticalTheme.textMuted)
                                .frame(width: 5, height: 5)
                            Text("STANDBY // GUEST")
                                .font(.system(size: 9, weight: .bold, design: .monospaced))
                                .tracking(0.8)
                                .foregroundColor(TacticalTheme.textMuted)
                        }
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(TacticalTheme.bgCard)
                        .cornerRadius(3)
                        .overlay(
                            RoundedRectangle(cornerRadius: 3)
                                .stroke(TacticalTheme.border, lineWidth: 1)
                        )
                    }
                    
                    Spacer()
                    
                    StatusBadge("SERVER READY", variant: .gold)
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)
                .padding(.bottom, 12)
                
                Spacer()
                
                // MARK: - Center Hero (Brand Only: ROS Sothatt)
                VStack(spacing: 16) {
                    Image("Logo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 160, height: 160)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    
                    VStack(spacing: 6) {
                        HStack(spacing: 6) {
                            Text("ROS")
                                .font(.system(size: 26, weight: .black))
                                .tracking(2.0)
                                .foregroundColor(TacticalTheme.textPrimary)
                            Text("SOTHATT")
                                .font(.system(size: 26, weight: .black))
                                .tracking(2.0)
                                .foregroundColor(TacticalTheme.gold)
                        }
                        
                        Text("OFFICIAL GAME LAUNCHER")
                            .font(.system(size: 11, weight: .bold))
                            .tracking(3.0)
                            .foregroundColor(TacticalTheme.textSecondary)
                        
                        Rectangle()
                            .fill(TacticalTheme.borderGold)
                            .frame(width: 48, height: 1)
                            .padding(.top, 4)
                    }
                }
                
                Spacer()
                
                // MARK: - Primary Action: Download & Installation Flow
                VStack(spacing: 12) {
                    switch downloadVM.status {
                    case .notStarted:
                        PrimaryButton("DOWNLOAD", systemImage: "arrow.down.to.line") {
                            if let url = serverConfig.downloadURL {
                                downloadVM.startDownload(from: url)
                            }
                        }
                        
                    case .connecting:
                        VStack(spacing: 8) {
                            HStack(spacing: 8) {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: TacticalTheme.gold))
                                    .scaleEffect(0.85)
                                Text("CONNECTING TO SERVER...")
                                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                                    .tracking(1.0)
                                    .foregroundColor(TacticalTheme.gold)
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 46)
                            .background(TacticalTheme.bgCard)
                            .cornerRadius(3)
                            .overlay(
                                RoundedRectangle(cornerRadius: 3)
                                    .stroke(TacticalTheme.borderGold, lineWidth: 1)
                            )
                            
                            Button(action: {
                                downloadVM.cancelDownload()
                            }) {
                                Text("CANCEL")
                                    .font(.system(size: 10, weight: .bold))
                                    .tracking(1.0)
                                    .foregroundColor(TacticalTheme.textMuted)
                            }
                        }
                        
                    case .downloading(let progress, _, _, let speed):
                        VStack(spacing: 8) {
                            // Progress bar
                            GeometryReader { geo in
                                ZStack(alignment: .leading) {
                                    Rectangle()
                                        .fill(TacticalTheme.bgCard)
                                    Rectangle()
                                        .fill(TacticalTheme.gold)
                                        .frame(width: geo.size.width * CGFloat(progress))
                                }
                            }
                            .frame(height: 6)
                            .cornerRadius(3)
                            
                            HStack {
                                Text(downloadVM.progressText)
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundColor(TacticalTheme.textSecondary)
                                Spacer()
                                if !speed.isEmpty {
                                    Text(speed)
                                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                                        .foregroundColor(TacticalTheme.gold)
                                }
                            }
                            
                            SecondaryButton("CANCEL DOWNLOAD", systemImage: "xmark") {
                                downloadVM.cancelDownload()
                            }
                        }
                        
                    case .completed(let localURL, let fileSize):
                        VStack(spacing: 10) {
                            TacticalCard(isHighlighted: true) {
                                HStack {
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text("GAME PACKAGE READY")
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(TacticalTheme.gold)
                                        Text("Size: \(fileSize) • Stored in Documents")
                                            .font(.system(size: 10, design: .monospaced))
                                            .foregroundColor(TacticalTheme.textMuted)
                                    }
                                    Spacer()
                                    StatusBadge("VERIFIED", variant: .online)
                                }
                            }
                            
                            if downloadVM.isGameInstalled {
                                PrimaryButton("PLAY GAME", systemImage: "play.fill") {
                                    downloadVM.launchGame()
                                }
                            } else {
                                PrimaryButton("EXPORT / INSTALL GAME", systemImage: "square.and.arrow.up") {
                                    showShareSheet = true
                                }
                                
                                Text("iOS sandboxing requires sideloading downloaded IPA files using AltStore or Sideloadly.")
                                    .font(.system(size: 10))
                                    .foregroundColor(TacticalTheme.textMuted)
                                    .multilineTextAlignment(.center)
                                    .padding(.horizontal, 8)
                            }
                        }
                        
                    case .failed(let errorMessage):
                        VStack(spacing: 8) {
                            HStack(spacing: 6) {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .font(.system(size: 12))
                                    .foregroundColor(TacticalTheme.danger)
                                Text(errorMessage)
                                    .font(.system(size: 11))
                                    .foregroundColor(TacticalTheme.danger)
                                    .lineLimit(2)
                            }
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(TacticalTheme.danger.opacity(0.12))
                            .cornerRadius(3)
                            
                            PrimaryButton("RETRY DOWNLOAD", systemImage: "arrow.clockwise") {
                                if let url = serverConfig.downloadURL {
                                    downloadVM.startDownload(from: url)
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
        }
        .onAppear {
            downloadVM.checkGameInstallation()
            downloadVM.checkLocalFile()
        }
        .sheet(isPresented: $showShareSheet) {
            if let localURL = downloadVM.localFileURL {
                ShareSheet(items: [localURL])
            }
        }
    }
}
