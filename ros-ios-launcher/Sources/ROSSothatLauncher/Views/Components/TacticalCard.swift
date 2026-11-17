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
        .padding(14)
        .background(TacticalTheme.bgCard)
        .cornerRadius(6)
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(isHighlighted ? TacticalTheme.borderGold : TacticalTheme.border, lineWidth: 1)
        )
    }
}
