import SwiftUI

public struct CustomTextField: View {
    public let placeholder: String
    public let systemImage: String
    @Binding public var text: String
    public var isSecure: Bool
    
    public init(
        _ placeholder: String,
        icon: String = "envelope.fill",
        text: Binding<String>,
        isSecure: Bool = false
    ) {
        self.placeholder = placeholder
        self.systemImage = icon
        self._text = text
        self.isSecure = isSecure
    }
    
    public var body: some View {
        HStack(spacing: 10) {
            if !systemImage.isEmpty && UIImage(systemName: systemImage) != nil {
                Image(systemName: systemImage)
                    .font(.system(size: 13))
                    .foregroundColor(TacticalTheme.goldMuted)
            }
            
            if isSecure {
                SecureField("", text: $text)
                    .placeholder(when: text.isEmpty) {
                        Text(placeholder).foregroundColor(TacticalTheme.textMuted)
                    }
                    .font(.system(size: 13))
                    .foregroundColor(TacticalTheme.textPrimary)
            } else {
                TextField("", text: $text)
                    .placeholder(when: text.isEmpty) {
                        Text(placeholder).foregroundColor(TacticalTheme.textMuted)
                    }
                    .font(.system(size: 13))
                    .foregroundColor(TacticalTheme.textPrimary)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 11)
        .background(TacticalTheme.bgSecondary)
        .cornerRadius(3)
        .overlay(
            RoundedRectangle(cornerRadius: 3)
                .stroke(TacticalTheme.border, lineWidth: 1)
        )
    }
}

extension View {
    func placeholder<Content: View>(
        when shouldShow: Bool,
        alignment: Alignment = .leading,
        @ViewBuilder placeholder: () -> Content
    ) -> some View {
        ZStack(alignment: alignment) {
            placeholder().opacity(shouldShow ? 1 : 0)
            self
        }
    }
}
