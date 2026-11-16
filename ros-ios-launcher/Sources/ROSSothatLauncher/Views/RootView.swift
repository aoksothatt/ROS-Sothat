import SwiftUI

public struct RootView: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack {
            // Main Content Area
            Group {
                switch launcherVM.currentScreen {
                case .splash:
                    SplashScreen()
                case .welcome:
                    HomeDashboardScreen()
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
        }
    }
}
