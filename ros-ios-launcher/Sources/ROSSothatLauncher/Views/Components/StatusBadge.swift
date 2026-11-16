import SwiftUI

public enum BadgeVariant {
    case gold
    case beta
    case online
    case warning
}

public struct StatusBadge: View {
    public let text: String
    public let variant: BadgeVariant
    
    public init(_ text: String, variant: BadgeVariant = .gold) {
        self.text = text
        self.variant = variant
    }
    
    public var body: some View {
        Text(text)
            .font(.system(size: 9, weight: .bold, design: .monospaced))
            .tracking(0.8)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(bgColor)
            .foregroundColor(fgColor)
            .cornerRadius(2)
            .overlay(
                RoundedRectangle(cornerRadius: 2)
                    .stroke(borderColor, lineWidth: 1)
            )
    }
    
    private var fgColor: Color {
        switch variant {
        case .gold: return TacticalTheme.gold
        case .beta, .online: return TacticalTheme.success
        case .warning: return TacticalTheme.warning
        }
    }
    
    private var bgColor: Color {
        switch variant {
        case .gold: return TacticalTheme.gold.opacity(0.12)
        case .beta, .online: return TacticalTheme.success.opacity(0.12)
        case .warning: return TacticalTheme.warning.opacity(0.12)
        }
    }
    
    private var borderColor: Color {
        switch variant {
        case .gold: return TacticalTheme.gold.opacity(0.4)
        case .beta, .online: return TacticalTheme.success.opacity(0.4)
        case .warning: return TacticalTheme.warning.opacity(0.4)
        }
    }
}
