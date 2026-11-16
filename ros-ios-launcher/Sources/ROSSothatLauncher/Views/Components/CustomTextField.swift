import SwiftUI

public struct CustomTextField: View {
    public let placeholder: String
    public let icon: String
    @Binding public var text: String
    public var isSecure: Bool
    
    public init(
        _ placeholder: String,
        icon: String,
        text: Binding<String>,
        isSecure: Bool = false
    ) {
        self.placeholder = placeholder
        self.icon = icon
        self._text = text
        self.isSecure = isSecure
    }
    
    public var body: some View {
        HStack(spacing: 12) {
            Text(icon)
                .font(.system(size: 15))
                .foregroundColor(TacticalTheme.textMuted)
            
            if isSecure {
                SecureField("", text: $text)
                    .placeholder(when: text.isEmpty) {
                        Text(placeholder).foregroundColor(TacticalTheme.textMuted)
                    }
                    .font(.system(size: 14))
                    .foregroundColor(TacticalTheme.textPrimary)
            } else {
                TextField("", text: $text)
                    .placeholder(when: text.isEmpty) {
                        Text(placeholder).foregroundColor(TacticalTheme.textMuted)
                    }
                    .font(.system(size: 14))
                    .foregroundColor(TacticalTheme.textPrimary)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(TacticalTheme.bgSecondary)
        .cornerRadius(6)
        .overlay(
            RoundedRectangle(cornerRadius: 6)
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
