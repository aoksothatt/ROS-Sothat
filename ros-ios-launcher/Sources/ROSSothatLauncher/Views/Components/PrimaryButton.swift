import SwiftUI

public struct PrimaryButton: View {
    public let title: String
    public let icon: String?
    public let isLoading: Bool
    public let action: () -> Void
    
    public init(
        _ title: String,
        icon: String? = nil,
        isLoading: Bool = false,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.isLoading = isLoading
        self.action = action
    }
    
    public var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: TacticalTheme.bgPrimary))
                        .scaleEffect(0.9)
                } else {
                    if let icon = icon {
                        Text(icon)
                            .font(.system(size: 15))
                    }
                    Text(title)
                        .font(.system(size: 14, weight: .bold))
                        .tracking(1.0)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 48)
            .background(
                LinearGradient(
                    gradient: Gradient(colors: [TacticalTheme.goldLight, TacticalTheme.goldDark]),
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            )
            .foregroundColor(TacticalTheme.bgPrimary)
            .cornerRadius(6)
            .shadow(color: TacticalTheme.gold.opacity(0.3), radius: 8, x: 0, y: 3)
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(TacticalTheme.goldLight, lineWidth: 1)
            )
        }
        .disabled(isLoading)
    }
}
