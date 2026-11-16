import Foundation
import Combine

public class AuthViewModel: ObservableObject {
    @Published public var isAuthenticated: Bool = false
    @Published public var currentUser: PlayerProfile?
    @Published public var emailInput: String = ""
    @Published public var usernameInput: String = ""
    @Published public var otpInput: String = ""
    @Published public var isOtpStep: Bool = false
    @Published public var isLoading: Bool = false
    @Published public var errorMessage: String?
    @Published public var successMessage: String?
    
    public init(authenticated: Bool = true) {
        self.isAuthenticated = authenticated
        if authenticated {
            self.currentUser = MockData.samplePlayer
        }
    }
    
    public func requestSignInOtp() {
        guard !emailInput.isEmpty && emailInput.contains("@") else {
            errorMessage = "Please enter a valid email address."
            return
        }
        isLoading = true
        errorMessage = nil
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            self.isLoading = false
            self.isOtpStep = true
            self.successMessage = "Mock code generated: 123456"
        }
    }
    
    public func requestRegisterOtp() {
        guard !usernameInput.isEmpty else {
            errorMessage = "Please choose a codename."
            return
        }
        guard !emailInput.isEmpty && emailInput.contains("@") else {
            errorMessage = "Please enter a valid email address."
            return
        }
        isLoading = true
        errorMessage = nil
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            self.isLoading = false
            self.isOtpStep = true
            self.successMessage = "Mock code generated: 123456"
        }
    }
    
    public func verifyOtp() {
        guard otpInput == "123456" || otpInput.count == 6 else {
            errorMessage = "Invalid verification code. Enter 123456 in mock mode."
            return
        }
        isLoading = true
        errorMessage = nil
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            self.isLoading = false
            self.isAuthenticated = true
            var user = MockData.samplePlayer
            if !self.emailInput.isEmpty { user.email = self.emailInput }
            if !self.usernameInput.isEmpty { user.username = self.usernameInput }
            self.currentUser = user
            self.isOtpStep = false
            self.otpInput = ""
            self.successMessage = nil
        }
    }
    
    public func signOut() {
        isAuthenticated = false
        currentUser = nil
        emailInput = ""
        usernameInput = ""
        otpInput = ""
        isOtpStep = false
        errorMessage = nil
        successMessage = nil
    }
}
