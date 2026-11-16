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
                    RoundedRectangle(cornerRadius: 3)
                        .fill(TacticalTheme.bgCard)
                        .frame(width: 28, height: 28)
                        .overlay(
                            RoundedRectangle(cornerRadius: 3)
                                .stroke(TacticalTheme.borderGold, lineWidth: 1)
                        )
                    Image(systemName: "shield.fill")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(TacticalTheme.gold)
                }
                
                VStack(alignment: .leading, spacing: 1) {
                    HStack(spacing: 4) {
                        Text("ROS")
                            .font(.system(size: 16, weight: .black))
                            .foregroundColor(TacticalTheme.textPrimary)
                        Text("SOTHATT")
                            .font(.system(size: 16, weight: .black))
                            .foregroundColor(TacticalTheme.gold)
                    }
                    Text("TACTICAL LAUNCHER")
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
                        .frame(width: 6, height: 6)
                    Text("\(serverPing) MS")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundColor(TacticalTheme.success)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(TacticalTheme.bgCard)
                .cornerRadius(2)
                .overlay(
                    RoundedRectangle(cornerRadius: 2)
                        .stroke(TacticalTheme.border, lineWidth: 1)
                )
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
    }
}
