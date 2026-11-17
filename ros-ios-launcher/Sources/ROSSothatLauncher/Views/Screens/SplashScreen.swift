import SwiftUI

public struct SplashScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @State private var isAnimating: Bool = false
    @State private var progressAmount: CGFloat = 0.2
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            VStack(spacing: 24) {
                Spacer()
                
                // ROS Sothatt Black-and-Gold Logo (EXACTLY UNCHANGED)
                Image("Logo")
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 140, height: 140)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(TacticalTheme.borderGold, lineWidth: 1)
                    )
                    .scaleEffect(isAnimating ? 1.0 : 0.94)
                    .opacity(isAnimating ? 1.0 : 0.0)
                
                // Brand Title
                VStack(spacing: 6) {
                    HStack(spacing: 8) {
                        Text("ROS")
                            .font(.system(size: 28, weight: .black))
                            .tracking(3.0)
                            .foregroundColor(TacticalTheme.textPrimary)
                        Text("SOTHATT")
                            .font(.system(size: 28, weight: .black))
                            .tracking(3.0)
                            .foregroundColor(TacticalTheme.gold)
                    }
                    
                    Text("PRIVATE SERVER LAUNCHER")
                        .font(.system(size: 10, weight: .bold))
                        .tracking(3.0)
                        .foregroundColor(TacticalTheme.textSecondary)
                }
                .opacity(isAnimating ? 1.0 : 0.0)
                
                Spacer()
                
                // Subtle Gold Loading Bar
                VStack(spacing: 12) {
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            Capsule()
                                .fill(TacticalTheme.bgCard)
                                .frame(height: 2)
                            Capsule()
                                .fill(TacticalTheme.goldGradient)
                                .frame(width: geo.size.width * progressAmount, height: 2)
                        }
                    }
                    .frame(width: 140, height: 2)
                    
                    Text("CONNECTING...")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .tracking(1.5)
                        .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.bottom, 48)
            }
        }
        .onAppear {
            withAnimation(.easeOut(duration: 0.6)) {
                isAnimating = true
            }
            withAnimation(.easeInOut(duration: 1.2)) {
                progressAmount = 1.0
            }
            
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.4) {
                withAnimation(.easeInOut(duration: 0.35)) {
                    launcherVM.finishInitialization()
                }
            }
        }
    }
}
