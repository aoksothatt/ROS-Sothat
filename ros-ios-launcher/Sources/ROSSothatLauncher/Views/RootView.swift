import SwiftUI

public struct RootView: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack {
            if launcherVM.isInitializing {
                SplashScreen()
                    .transition(.opacity)
            } else {
                MainContainerView()
                    .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.35), value: launcherVM.isInitializing)
    }
}
