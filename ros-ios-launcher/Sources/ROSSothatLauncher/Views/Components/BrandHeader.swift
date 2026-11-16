import SwiftUI

public struct BrandHeader: View {
    public var showStatus: Bool
    public var serverPing: Int
    
    public init(showStatus: Bool = true, serverPing: Int = 18) {
        self.showStatus = showStatus
        self.serverPing = serverPing
    }
    
    public var body: some View {
        HStack {
            HStack(spacing: 8) {
                ZStack {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(TacticalTheme.gold.opacity(0.15))
                        .frame(width: 32, height: 32)
                        .overlay(
                            RoundedRectangle(cornerRadius: 6)
                                .stroke(TacticalTheme.gold.opacity(0.4), lineWidth: 1)
                        )
                    Text("⚔️")
                        .font(.system(size: 16))
                }
                
                VStack(alignment: .leading, spacing: 1) {
                    HStack(spacing: 4) {
                        Text("ROS")
                            .font(.system(size: 18, weight: .black, design: .default))
                            .foregroundColor(TacticalTheme.textPrimary)
                        Text("SOTHATT")
                            .font(.system(size: 18, weight: .black, design: .default))
                            .foregroundColor(TacticalTheme.gold)
                    }
                    Text("RULES OF SURVIVAL LEGACY")
                        .font(.system(size: 8, weight: .bold))
                        .tracking(1.5)
                        .foregroundColor(TacticalTheme.textMuted)
                }
            }
            
            Spacer()
            
            if showStatus {
                HStack(spacing: 6) {
                    Circle()
                        .fill(TacticalTheme.success)
                        .frame(width: 8, height: 8)
                        .shadow(color: TacticalTheme.success.opacity(0.8), radius: 4)
                    Text("\(serverPing) ms")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .foregroundColor(TacticalTheme.success)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(TacticalTheme.success.opacity(0.1))
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(TacticalTheme.success.opacity(0.3), lineWidth: 1)
                )
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}
