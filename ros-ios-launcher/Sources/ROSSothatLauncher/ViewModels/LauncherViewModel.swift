import Foundation
import Combine

public enum LauncherScreen: Hashable {
    case splash
    case welcome
    case signIn
    case createAccount
    case homeDashboard
    case playerProfile
    case gameDownload
    case installationGuide
    case playScreen
}

public class LauncherViewModel: ObservableObject {
    @Published public var currentScreen: LauncherScreen = .splash
    @Published public var gameVersion: GameVersionInfo = MockData.defaultGameVersion
    @Published public var announcements: [LauncherAnnouncement] = MockData.sampleAnnouncements
    @Published public var serverPingMs: Int = 18
    @Published public var isServerOnline: Bool = true
    @Published public var selectedTab: Int = 0 // 0 = Home, 1 = Download, 2 = Guide, 3 = Profile, 4 = Play
    
    public init() {}
    
    public func navigateTo(_ screen: LauncherScreen) {
        currentScreen = screen
    }
    
    public func refreshServerStatus() {
        // Mock server ping simulation
        serverPingMs = Int.random(in: 15...28)
        isServerOnline = true
    }
}
