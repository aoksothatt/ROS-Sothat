import SwiftUI

public enum TacticalTheme {
    // Backgrounds - deep tactical charcoal & matte black
    public static let bgPrimary = Color(hex: "080B10")
    public static let bgSecondary = Color(hex: "0D1219")
    public static let bgCard = Color(hex: "121822")
    public static let bgCardHover = Color(hex: "17202D")
    
    // Accents - refined military gold
    public static let gold = Color(hex: "D7A84B")
    public static let goldLight = Color(hex: "E5B85C")
    public static let goldDark = Color(hex: "B88A32")
    public static let goldMuted = Color(hex: "7A6332")
    public static let red = Color(hex: "B94B3C")
    public static let redHover = Color(hex: "CB5A4A")
    
    // Borders - precise hairline borders
    public static let border = Color(hex: "1E2836")
    public static let borderLight = Color(hex: "2A384A")
    public static let borderGold = Color(hex: "D7A84B").opacity(0.35)
    public static let borderGoldSolid = Color(hex: "D7A84B")
    
    // Text
    public static let textPrimary = Color(hex: "F3F6FA")
    public static let textSecondary = Color(hex: "94A3B8")
    public static let textMuted = Color(hex: "566579")
    
    // Status
    public static let success = Color(hex: "34D399")
    public static let warning = Color(hex: "FBBF24")
    public static let danger = Color(hex: "F87171")
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        _ = Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
