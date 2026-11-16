import SwiftUI

public struct SplashScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    @State private var isAnimating: Bool = false
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 20) {
                Spacer()
                
                // Artwork with clean, flat gold bezel
                Image("Logo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 140, height: 140)
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(TacticalTheme.borderGold, lineWidth: 1)
                    )
                    .scaleEffect(isAnimating ? 1.0 : 0.9)
                    .opacity(isAnimating ? 1.0 : 0.0)
                
                VStack(spacing: 6) {
                    HStack(spacing: 6) {
                        Text("ROS")
                            .font(.system(size: 26, weight: .black))
                            .tracking(2.0)
                            .foregroundColor(TacticalTheme.textPrimary)
                        Text("SOTHATT")
                            .font(.system(size: 26, weight: .black))
                            .tracking(2.0)
                            .foregroundColor(TacticalTheme.gold)
                    }
                    
                    Text("RULES OF SURVIVAL LEGACY")
                        .font(.system(size: 11, weight: .bold))
                        .tracking(3.0)
                        .foregroundColor(TacticalTheme.textSecondary)
                }
                .opacity(isAnimating ? 1.0 : 0.0)
                
                Spacer()
                
                Text("INITIALIZING // TACTICAL CONSOLE")
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .tracking(1.5)
                    .foregroundColor(TacticalTheme.textMuted)
                    .padding(.bottom, 40)
            }
        }
        .onAppear {
            withAnimation(.easeOut(duration: 0.5)) {
                isAnimating = true
            }
            
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                launcherVM.navigateTo(.homeDashboard)
            }
        }
    }
}
