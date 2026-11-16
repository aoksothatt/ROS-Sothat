import Foundation

public struct PlayerProfile: Identifiable, Codable {
    public let id: Int
    public var username: String
    public var email: String
    public var role: String
    public var isVerified: Bool
    
    public init(
        id: Int = 1,
        username: String = "Operator",
        email: String = "operator@rossothat.com",
        role: String = "Player",
        isVerified: Bool = true
    ) {
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.isVerified = isVerified
    }
}
