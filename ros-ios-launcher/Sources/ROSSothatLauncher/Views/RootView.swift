import SwiftUI

public struct RootView: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack(alignment: .bottom) {
            // Main Content Area
            Group {
                switch launcherVM.currentScreen {
                case .splash:
                    SplashScreen()
                case .welcome:
                    WelcomeScreen()
                case .signIn:
                    SignInScreen()
                case .createAccount:
                    CreateAccountScreen()
                case .homeDashboard:
                    HomeDashboardScreen()
                case .playerProfile:
                    PlayerProfileScreen()
                case .gameDownload:
                    GameDownloadScreen()
                case .installationGuide:
                    InstallationGuideScreen()
                case .playScreen:
                    PlayScreen()
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            
            // Bottom Tactical Navigation Bar (shown on dashboard & inner screens)
            if shouldShowBottomBar {
                TacticalBottomBar()
            }
        }
    }
    
    private var shouldShowBottomBar: Bool {
        switch launcherVM.currentScreen {
        case .splash, .welcome, .signIn, .createAccount:
            return false
        default:
            return true
        }
    }
}

struct TacticalBottomBar: View {
    @EnvironmentObject var launcherVM: LauncherViewModel
    
    var body: some View {
        HStack(spacing: 0) {
            BottomTabItem(
                title: "DASHBOARD",
                icon: "🏛️",
                isSelected: launcherVM.currentScreen == .homeDashboard
            ) {
                launcherVM.navigateTo(.homeDashboard)
            }
            
            BottomTabItem(
                title: "DOWNLOAD",
                icon: "📥",
                isSelected: launcherVM.currentScreen == .gameDownload
            ) {
                launcherVM.navigateTo(.gameDownload)
            }
            
            BottomTabItem(
                title: "PLAY",
                icon: "▶️",
                isSelected: launcherVM.currentScreen == .playScreen,
                isCenterPlay: true
            ) {
                launcherVM.navigateTo(.playScreen)
            }
            
            BottomTabItem(
                title: "GUIDE",
                icon: "📖",
                isSelected: launcherVM.currentScreen == .installationGuide
            ) {
                launcherVM.navigateTo(.installationGuide)
            }
            
            BottomTabItem(
                title: "PROFILE",
                icon: "👤",
                isSelected: launcherVM.currentScreen == .playerProfile
            ) {
                launcherVM.navigateTo(.playerProfile)
            }
        }
        .frame(height: 56)
        .background(TacticalTheme.bgCard)
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(TacticalTheme.border),
            alignment: .top
        )
    }
}

struct BottomTabItem: View {
    let title: String
    let icon: String
    let isSelected: Bool
    var isCenterPlay: Bool = false
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 2) {
                if isCenterPlay {
                    ZStack {
                        Circle()
                            .fill(isSelected ? TacticalTheme.gold : TacticalTheme.bgSecondary)
                            .frame(width: 32, height: 32)
                            .overlay(
                                Circle().stroke(TacticalTheme.gold, lineWidth: 1)
                            )
                        Text(icon)
                            .font(.system(size: 14))
                    }
                    .offset(y: -4)
                } else {
                    Text(icon)
                        .font(.system(size: 16))
                }
                
                Text(title)
                    .font(.system(size: 8, weight: .black))
                    .tracking(0.5)
                    .foregroundColor(isSelected ? TacticalTheme.gold : TacticalTheme.textMuted)
            }
            .frame(maxWidth: .infinity)
            .padding(.top, isCenterPlay ? 0 : 4)
        }
    }
}
