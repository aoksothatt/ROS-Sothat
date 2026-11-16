import SwiftUI

public struct PrimaryButton: View {
    public let title: String
    public let systemImage: String?
    public let isLoading: Bool
    public let action: () -> Void
    
    public init(
        _ title: String,
        systemImage: String? = nil,
        isLoading: Bool = false,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.systemImage = systemImage
        self.isLoading = isLoading
        self.action = action
    }
    
    // Backwards-compatible initializer
    public init(
        _ title: String,
        icon: String?,
        isLoading: Bool = false,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.systemImage = icon
        self.isLoading = isLoading
        self.action = action
    }
    
    public var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if isLoading {
                    ProgressView()
                        .progressViewStyle(CircularProgressViewStyle(tint: TacticalTheme.bgPrimary))
                        .scaleEffect(0.85)
                } else {
                    if let img = systemImage, !img.isEmpty, UIImage(systemName: img) != nil {
                        Image(systemName: img)
                            .font(.system(size: 13, weight: .bold))
                            .foregroundColor(TacticalTheme.bgPrimary)
                    }
                    Text(title)
                        .font(.system(size: 13, weight: .black))
                        .tracking(1.4)
                        .foregroundColor(TacticalTheme.bgPrimary)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 46)
            .background(TacticalTheme.gold)
            .cornerRadius(3)
            .overlay(
                RoundedRectangle(cornerRadius: 3)
                    .stroke(TacticalTheme.goldLight.opacity(0.6), lineWidth: 1)
            )
        }
        .disabled(isLoading)
    }
}
