import Foundation
import Combine

public class LauncherViewModel: ObservableObject {
    @Published public var isInitializing: Bool = true
    @Published public var selectedTab: Int = 0 // 0 = Home, 1 = Download, 2 = Account
    
    public init() {}
    
    /// Finishes initial loading screen and presents the launcher.
    public func finishInitialization() {
        self.isInitializing = false
    }
}
