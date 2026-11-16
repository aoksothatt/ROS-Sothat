import Foundation
import Combine

/// Architecture configuration for connecting to future private server infrastructure.
/// Keeps backend endpoints modular and ready for real server deployment.
public class ServerConfig: ObservableObject {
    public static let shared = ServerConfig()
    
    // MARK: - Configurable Private Server Endpoints
    @Published public var serverHost: String = "127.0.0.1"
    @Published public var serverPort: Int = 20014
    @Published public var apiBaseURL: String = "https://rossothat.com/api"
    @Published public var downloadSourceURL: String = "https://rossothat.com/download/RoS-Legacy-iOS.ipa"
    
    // MARK: - Server State Architecture
    @Published public var isConnected: Bool = false
    @Published public var serverStatus: String = "STANDBY // READY FOR PRIVATE SERVER INTEGRATION"
    
    public init() {}
    
    /// Returns the resolved game IPA download URL.
    public var downloadURL: URL? {
        return URL(string: downloadSourceURL)
    }
}
