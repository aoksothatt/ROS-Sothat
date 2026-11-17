import SwiftUI

public struct HomeScreen: View {
    @EnvironmentObject public var serverConfig: ServerConfig
    @EnvironmentObject public var downloadVM: DownloadViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    @State private var showSettings: Bool = false
    @State private var showInstallSheet: Bool = false
    @State private var showShareSheet: Bool = false
    
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
                // MARK: - 1. Top Bar: Connection Status & Settings Button
                HStack {
                    // Small Private Server Connection Status Capsule
                    HStack(spacing: 6) {
                        Circle()
                            .fill(TacticalTheme.success)
                            .frame(width: 6, height: 6)
                        
                        Text("SERVER ONLINE")
                            .font(.system(size: 9, weight: .bold, design: .monospaced))
                            .tracking(1.2)
                            .foregroundColor(TacticalTheme.gold)
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
                
                // MARK: - 3. Prominent Gold PLAY Button
                VStack(spacing: 12) {
                    Button(action: handlePlayAction) {
                        HStack(spacing: 10) {
                            if case .downloading = downloadVM.status {
                                ProgressView()
                                    .progressViewStyle(CircularProgressViewStyle(tint: TacticalTheme.bgPrimary))
                                    .scaleEffect(0.9)
                            } else {
                                Image(systemName: "play.fill")
                                    .font(.system(size: 16, weight: .black))
                                    .foregroundColor(TacticalTheme.bgPrimary)
                            }
                            
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
                    
                    // Restrained progress display (only during active download)
                    if case .downloading(let progress, _, _, let speed) = downloadVM.status {
                        VStack(spacing: 6) {
                            GeometryReader { geo in
                                ZStack(alignment: .leading) {
                                    Capsule()
                                        .fill(TacticalTheme.bgCard)
                                    Capsule()
                                        .fill(TacticalTheme.goldGradient)
                                        .frame(width: geo.size.width * CGFloat(progress))
                                }
                            }
                            .frame(height: 4)
                            
                            HStack {
                                Text(downloadVM.progressText)
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundColor(TacticalTheme.textMuted)
                                Spacer()
                                Text(speed)
                                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                                    .foregroundColor(TacticalTheme.gold)
                            }
                        }
                        .padding(.top, 2)
                        .transition(.opacity)
                    }
                }
                .padding(.horizontal, 32)
                .padding(.bottom, 22)
                
                // MARK: - 4. Discreet Version Label at Bottom
                Text("v1.0.0 (Build 101) • ROS Sothatt")
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
        .actionSheet(isPresented: $showInstallSheet) {
            ActionSheet(
                title: Text("ROS Sothatt Game Package"),
                message: Text("Game client archive is downloaded. Sideload it using Sideloadly or launch via rosmobile://."),
                buttons: [
                    .default(Text("Export Game IPA (Sideloadly / AirDrop)")) {
                        showShareSheet = true
                    },
                    .default(Text("Launch Game (rosmobile://)")) {
                        downloadVM.launchGame()
                    },
                    .cancel(Text("Dismiss"))
                ]
            )
        }
        .sheet(isPresented: $showShareSheet) {
            if let localURL = downloadVM.localFileURL {
                ShareSheet(items: [localURL])
            }
        }
        .onAppear {
            downloadVM.checkGameInstallation()
            downloadVM.checkLocalFile()
        }
    }
    
    // MARK: - Play Action Logic
    private var playButtonTitle: String {
        if downloadVM.isGameInstalled {
            return "PLAY"
        }
        switch downloadVM.status {
        case .completed:
            return "PLAY"
        case .downloading:
            return "DOWNLOADING..."
        case .connecting:
            return "CONNECTING..."
        default:
            return "PLAY"
        }
    }
    
    private func handlePlayAction() {
        if downloadVM.isGameInstalled {
            downloadVM.launchGame()
        } else if case .completed = downloadVM.status {
            showInstallSheet = true
        } else if case .downloading = downloadVM.status {
            showSettings = true
        } else {
            if let url = serverConfig.downloadURL {
                downloadVM.startDownload(from: url)
            }
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
