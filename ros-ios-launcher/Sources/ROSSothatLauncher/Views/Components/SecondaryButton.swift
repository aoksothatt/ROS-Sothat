import SwiftUI

public struct SecondaryButton: View {
    public let title: String
    public let systemImage: String?
    public let action: () -> Void
    
    public init(_ title: String, systemImage: String? = nil, action: @escaping () -> Void) {
        self.title = title
        self.systemImage = systemImage
        self.action = action
    }
    
    // Backwards-compatible initializer
    public init(_ title: String, icon: String?, action: @escaping () -> Void) {
        self.title = title
        self.systemImage = icon
        self.action = action
    }
    
    public var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if let img = systemImage, !img.isEmpty, UIImage(systemName: img) != nil {
                    Image(systemName: img)
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(TacticalTheme.gold)
                }
                Text(title)
                    .font(.system(size: 12, weight: .bold))
                    .tracking(1.2)
                    .foregroundColor(TacticalTheme.textPrimary)
            }
            .frame(maxWidth: .infinity)
            .frame(height: 44)
            .background(TacticalTheme.bgCard)
            .cornerRadius(3)
            .overlay(
                RoundedRectangle(cornerRadius: 3)
                    .stroke(TacticalTheme.borderGold, lineWidth: 1)
            )
        }
    }
}
