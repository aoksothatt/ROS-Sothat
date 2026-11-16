import Foundation

public enum MockData {
    public static let samplePlayer = PlayerProfile(
        id: 10001,
        username: "GhostOperator",
        email: "ghost.operator@ros-sothat.island",
        role: "Alpha Tester",
        level: 42,
        exp: 12450,
        maxExp: 15000,
        diamonds: 850,
        gold: 45200,
        matchesPlayed: 184,
        wins: 38,
        kills: 542,
        kdRatio: 3.71,
        winRate: 20.65,
        rankTitle: "Master Operator",
        rankTier: "Tier III",
        avatarSymbol: "🎖️",
        isVerified: true
    )
    
    public static let defaultGameVersion = GameVersionInfo()
    
    public static let sampleAnnouncements: [LauncherAnnouncement] = [
        LauncherAnnouncement(
            id: 1,
            title: "ROS-Sothat iOS Companion Launcher Online",
            summary: "Native SwiftUI launcher preview available for private community testing. Includes full telemetry and checksum verification.",
            date: "November 16, 2026",
            tag: "LAUNCHER",
            author: "Dev Team"
        ),
        LauncherAnnouncement(
            id: 2,
            title: "Mercury BaseApp Handshake Verified",
            summary: "Protocol Stage 1–5 regression test passed on localhost UDP port 20014 with 100% session isolation.",
            date: "November 15, 2026",
            tag: "ENGINE",
            author: "Network Core"
        ),
        LauncherAnnouncement(
            id: 3,
            title: "Community Sideloading Guide Published",
            summary: "Detailed AltStore, Sideloadly, and iOS 16 Developer Mode setup documentation is now live.",
            date: "November 12, 2026",
            tag: "GUIDE",
            author: "Support"
        )
    ]
}
