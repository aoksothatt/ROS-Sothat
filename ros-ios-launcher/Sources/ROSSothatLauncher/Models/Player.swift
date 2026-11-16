import Foundation

public struct PlayerProfile: Identifiable, Codable {
    public let id: Int
    public var username: String
    public var email: String
    public var role: String
    public var level: Int
    public var exp: Int
    public var maxExp: Int
    public var diamonds: Int
    public var gold: Int
    public var matchesPlayed: Int
    public var wins: Int
    public var kills: Int
    public var kdRatio: Double
    public var winRate: Double
    public var rankTitle: String
    public var rankTier: String
    public var avatarSymbol: String
    public var isVerified: Bool
    
    public init(
        id: Int,
        username: String,
        email: String,
        role: String = "Player",
        level: Int = 42,
        exp: Int = 12450,
        maxExp: Int = 15000,
        diamonds: Int = 850,
        gold: Int = 45200,
        matchesPlayed: Int = 184,
        wins: Int = 38,
        kills: Int = 542,
        kdRatio: Double = 3.71,
        winRate: Double = 20.65,
        rankTitle: String = "Master Operator",
        rankTier: String = "Tier III",
        avatarSymbol: String = "🎖️",
        isVerified: Bool = true
    ) {
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.level = level
        self.exp = exp
        self.maxExp = maxExp
        self.diamonds = diamonds
        self.gold = gold
        self.matchesPlayed = matchesPlayed
        self.wins = wins
        self.kills = kills
        self.kdRatio = kdRatio
        self.winRate = winRate
        self.rankTitle = rankTitle
        self.rankTier = rankTier
        self.avatarSymbol = avatarSymbol
        self.isVerified = isVerified
    }
}
