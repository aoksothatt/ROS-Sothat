import Foundation

public struct GameVersionInfo: Identifiable, Codable {
    public let id: String
    public let version: String
    public let buildNumber: Int
    public let releaseDate: String
    public let clientSizeMB: Double
    public let launcherSizeMB: Double
    public let sha256Checksum: String
    public let minIosVersion: String
    public let channel: String
    public let serverStatus: String
    public let serverHost: String
    public let serverPort: Int
    public let isInstalled: Bool
    public let isUpdateAvailable: Bool
    
    public init(
        id: String = "ros-v1.0.0-beta",
        version: String = "1.0.0-beta.1",
        buildNumber: Int = 101,
        releaseDate: String = "November 2026",
        clientSizeMB: Double = 1840.0,
        launcherSizeMB: Double = 18.4,
        sha256Checksum: String = "7E4B29A1054F8E93B123C04928174092EBAF3019842C97184A10294719283741",
        minIosVersion: String = "iOS 15.0+",
        channel: String = "Private Beta",
        serverStatus: String = "Online",
        serverHost: String = "127.0.0.1",
        serverPort: Int = 20014,
        isInstalled: Bool = false,
        isUpdateAvailable: Bool = false
    ) {
        self.id = id
        self.version = version
        self.buildNumber = buildNumber
        self.releaseDate = releaseDate
        self.clientSizeMB = clientSizeMB
        self.launcherSizeMB = launcherSizeMB
        self.sha256Checksum = sha256Checksum
        self.minIosVersion = minIosVersion
        self.channel = channel
        self.serverStatus = serverStatus
        self.serverHost = serverHost
        self.serverPort = serverPort
        self.isInstalled = isInstalled
        self.isUpdateAvailable = isUpdateAvailable
    }
}
