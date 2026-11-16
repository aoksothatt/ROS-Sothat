import SwiftUI

public struct TacticalCard<Content: View>: View {
    public let isHighlighted: Bool
    public let content: Content
    
    public init(isHighlighted: Bool = false, @ViewBuilder content: () -> Content) {
        self.isHighlighted = isHighlighted
        self.content = content()
    }
    
    public var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            content
        }
        .padding(16)
        .background(TacticalTheme.bgCard)
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(isHighlighted ? TacticalTheme.borderGold : TacticalTheme.border, lineWidth: 1)
        )
        .shadow(
            color: isHighlighted ? TacticalTheme.gold.opacity(0.12) : Color.black.opacity(0.3),
            radius: isHighlighted ? 12 : 6,
            x: 0,
            y: 3
        )
    }
}
