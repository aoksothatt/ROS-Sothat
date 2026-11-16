import SwiftUI

@main
public struct ROSSothatLauncherApp: App {
    @StateObject private var launcherVM = LauncherViewModel()
    @StateObject private var authVM = AuthViewModel()
    
    public init() {}
    
    public var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(launcherVM)
                .environmentObject(authVM)
                .preferredColorScheme(.dark)
        }
    }
}
