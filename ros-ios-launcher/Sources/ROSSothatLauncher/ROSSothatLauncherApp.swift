import SwiftUI

@main
public struct ROSSothatLauncherApp: App {
    @StateObject private var launcherVM = LauncherViewModel()
    @StateObject private var authVM = AuthViewModel()
    @StateObject private var serverConfig = ServerConfig.shared
    @StateObject private var downloadVM = DownloadViewModel()
    
    public init() {}
    
    public var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(launcherVM)
                .environmentObject(authVM)
                .environmentObject(serverConfig)
                .environmentObject(downloadVM)
                .preferredColorScheme(.dark)
        }
    }
}
