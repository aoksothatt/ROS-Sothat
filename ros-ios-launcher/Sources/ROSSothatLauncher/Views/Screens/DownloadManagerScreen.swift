import SwiftUI

public struct DownloadManagerScreen: View {
    @EnvironmentObject public var serverConfig: ServerConfig
    @EnvironmentObject public var downloadVM: DownloadViewModel
    
    @State private var showShareSheet: Bool = false
    @State private var isEditingURL: Bool = false
    @State private var urlDraft: String = ""
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Top Header Bar
                HStack {
                    Text("DOWNLOAD MANAGER")
                        .font(.system(size: 11, weight: .bold))
                        .tracking(1.4)
                        .foregroundColor(TacticalTheme.gold)
                    Spacer()
                    if case .completed = downloadVM.status {
                        StatusBadge("READY", variant: .online)
                    } else if case .downloading = downloadVM.status {
                        StatusBadge("ACTIVE", variant: .gold)
                    } else {
                        StatusBadge("STANDBY", variant: .beta)
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
                        // Package Status Card
                        TacticalCard(isHighlighted: true) {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack {
                                    HStack(spacing: 6) {
                                        Image(systemName: "shippingbox.fill")
                                            .font(.system(size: 13))
                                            .foregroundColor(TacticalTheme.gold)
                                        Text("GAME PACKAGE ARCHIVE")
                                            .font(.system(size: 11, weight: .bold))
                                            .foregroundColor(TacticalTheme.textPrimary)
                                    }
                                    Spacer()
                                    if case .completed = downloadVM.status {
                                        StatusBadge("SAVED", variant: .online)
                                    } else {
                                        StatusBadge("NOT DOWNLOADED", variant: .warning)
                                    }
                                }
                                
                                Divider().background(TacticalTheme.border)
                                
                                if case .completed(_, let sizeStr) = downloadVM.status {
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack {
                                            Text("File Size:")
                                                .font(.system(size: 11))
                                                .foregroundColor(TacticalTheme.textMuted)
                                            Spacer()
                                            Text(sizeStr)
                                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                                .foregroundColor(TacticalTheme.textPrimary)
                                        }
                                        HStack {
                                            Text("Storage Path:")
                                                .font(.system(size: 11))
                                                .foregroundColor(TacticalTheme.textMuted)
                                            Spacer()
                                            Text("Documents/ROSSothatGame.ipa")
                                                .font(.system(size: 10, design: .monospaced))
                                                .foregroundColor(TacticalTheme.textSecondary)
                                        }
                                    }
                                    
                                    PrimaryButton("EXPORT TO FILES / AIRDROP", systemImage: "square.and.arrow.up") {
                                        showShareSheet = true
                                    }
                                    .padding(.top, 4)
                                    
                                    SecondaryButton("DELETE CACHED PACKAGE", systemImage: "trash") {
                                        downloadVM.deleteLocalFile()
                                    }
                                } else if case .downloading(let progress, _, _, let speed) = downloadVM.status {
                                    VStack(spacing: 6) {
                                        ProgressView(value: progress)
                                            .accentColor(TacticalTheme.gold)
                                        HStack {
                                            Text(downloadVM.progressText)
                                                .font(.system(size: 10, design: .monospaced))
                                                .foregroundColor(TacticalTheme.textSecondary)
                                            Spacer()
                                            Text(speed)
                                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                                .foregroundColor(TacticalTheme.gold)
                                        }
                                        SecondaryButton("CANCEL DOWNLOAD", systemImage: "xmark") {
                                            downloadVM.cancelDownload()
                                        }
                                        .padding(.top, 4)
                                    }
                                } else {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text("No game archive downloaded yet. Start download from the Home tab or using the button below.")
                                            .font(.system(size: 11))
                                            .foregroundColor(TacticalTheme.textSecondary)
                                        
                                        PrimaryButton("START DOWNLOAD", systemImage: "arrow.down.to.line") {
                                            if let url = serverConfig.downloadURL {
                                                downloadVM.startDownload(from: url)
                                            }
                                        }
                                        .padding(.top, 4)
                                    }
                                }
                            }
                        }
                        
                        // Configured Download Source
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 10) {
                                HStack {
                                    Text("DOWNLOAD SOURCE ENDPOINT")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                    Spacer()
                                    Button(action: {
                                        if isEditingURL {
                                            serverConfig.downloadSourceURL = urlDraft
                                            isEditingURL = false
                                        } else {
                                            urlDraft = serverConfig.downloadSourceURL
                                            isEditingURL = true
                                        }
                                    }) {
                                        Text(isEditingURL ? "SAVE" : "EDIT")
                                            .font(.system(size: 10, weight: .bold))
                                            .foregroundColor(TacticalTheme.gold)
                                    }
                                }
                                
                                if isEditingURL {
                                    TextField("https://...", text: $urlDraft)
                                        .font(.system(size: 11, design: .monospaced))
                                        .padding(8)
                                        .background(TacticalTheme.bgSecondary)
                                        .cornerRadius(3)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 3)
                                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                                        )
                                } else {
                                    Text(serverConfig.downloadSourceURL)
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                        .padding(8)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(TacticalTheme.bgSecondary)
                                        .cornerRadius(3)
                                }
                                
                                Text("Configurable package origin for private server deployment.")
                                    .font(.system(size: 10))
                                    .foregroundColor(TacticalTheme.textMuted)
                            }
                        }
                        
                        // Sideload Installation Guide
                        TacticalCard {
                            VStack(alignment: .leading, spacing: 8) {
                                HStack(spacing: 6) {
                                    Image(systemName: "info.circle.fill")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.gold)
                                    Text("IOS SIDELOADING PROCEDURE")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(TacticalTheme.gold)
                                }
                                
                                VStack(alignment: .leading, spacing: 6) {
                                    Text("1. Standard iOS sandboxing prevents apps from silently installing IPA files.")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                    Text("2. Once downloaded, tap 'Export' to save to your iPhone Files or AirDrop to Mac/PC.")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                    Text("3. Use Sideloadly or AltStore to sign and install onto your iOS device.")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                    Text("4. Once installed, launch directly or dispatch from the ROS Sothatt launcher.")
                                        .font(.system(size: 11))
                                        .foregroundColor(TacticalTheme.textSecondary)
                                }
                            }
                        }
                    }
                    .padding(20)
                }
            }
        }
        .sheet(isPresented: $showShareSheet) {
            if let localURL = downloadVM.localFileURL {
                ShareSheet(items: [localURL])
            }
        }
    }
}
