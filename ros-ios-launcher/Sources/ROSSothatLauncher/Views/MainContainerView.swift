import SwiftUI

public struct MainContainerView: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            HomeScreen()
        }
        .preferredColorScheme(.dark)
    }
}
