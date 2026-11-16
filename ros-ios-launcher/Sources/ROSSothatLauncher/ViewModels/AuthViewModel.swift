import Foundation
import Combine

public class AuthViewModel: ObservableObject {
    @Published public var isAuthenticated: Bool = false
    @Published public var callsign: String = ""
    @Published public var emailInput: String = ""
    @Published public var passwordInput: String = ""
    @Published public var isLoading: Bool = false
    @Published public var statusMessage: String?
    @Published public var errorMessage: String?
    
    public init() {
        // Load saved session if available
        if let savedCallsign = UserDefaults.standard.string(forKey: "rossothat_callsign"), !savedCallsign.isEmpty {
            self.callsign = savedCallsign
            self.isAuthenticated = true
        }
    }
    
    /// Connects to private server authentication endpoint when live.
    public func authenticate(serverConfig: ServerConfig) {
        guard !callsign.trimmingCharacters(in: .whitespaces).isEmpty else {
            errorMessage = "Please enter an operator callsign."
            return
        }
        
        isLoading = true
        errorMessage = nil
        statusMessage = "Connecting to \(serverConfig.serverHost):\(serverConfig.serverPort)..."
        
        // Architecture placeholder: Once the user's private server backend is deployed,
        // this will perform a real URLSession POST to serverConfig.apiBaseURL + "/auth/login".
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
            self.isLoading = false
            self.isAuthenticated = true
            self.statusMessage = "Authenticated as \(self.callsign)"
            UserDefaults.standard.set(self.callsign, forKey: "rossothat_callsign")
        }
    }
    
    public func signOut() {
        isAuthenticated = false
        callsign = ""
        emailInput = ""
        passwordInput = ""
        statusMessage = nil
        errorMessage = nil
        UserDefaults.standard.removeObject(forKey: "rossothat_callsign")
    }
}
