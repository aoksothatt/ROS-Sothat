import SwiftUI

public struct SecondaryButton: View {
    public let title: String
    public let icon: String?
    public let action: () -> Void
    
    public init(_ title: String, icon: String? = nil, action: @escaping () -> Void) {
        self.title = title
        self.icon = icon
        self.action = action
    }
    
    public var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let icon = icon {
                    Text(icon)
                        .font(.system(size: 14))
                }
                Text(title)
                    .font(.system(size: 13, weight: .bold))
                    .tracking(0.8)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 44)
            .background(TacticalTheme.bgSecondary)
            .foregroundColor(TacticalTheme.textPrimary)
            .cornerRadius(6)
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(TacticalTheme.border, lineWidth: 1)
            )
        }
    }
}
