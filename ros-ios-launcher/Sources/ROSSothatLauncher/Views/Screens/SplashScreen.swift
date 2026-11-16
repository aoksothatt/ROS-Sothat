import SwiftUI

public struct SplashScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    @State private var isAnimating: Bool = false
    @State private var pulseEffect: Bool = false
    @State private var loadingProgress: Double = 0.0
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            // Radial background glow
            RadialGradient(
                gradient: Gradient(colors: [TacticalTheme.gold.opacity(0.12), Color.clear]),
                center: .center,
                startRadius: 10,
                endRadius: 280
            )
            .ignoresSafeArea()
            
            VStack(spacing: 24) {
                Spacer()
                
                // Animated Emblem
                ZStack {
                    Circle()
                        .stroke(TacticalTheme.gold.opacity(0.2), lineWidth: 2)
                        .frame(width: 120, height: 120)
                        .scaleEffect(pulseEffect ? 1.15 : 0.95)
                        .opacity(pulseEffect ? 0.3 : 0.8)
                    
                    Circle()
                        .fill(
                            LinearGradient(
                                gradient: Gradient(colors: [TacticalTheme.bgCard, TacticalTheme.bgSecondary]),
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            )
                        )
                        .frame(width: 96, height: 96)
                        .overlay(
                            Circle()
                                .stroke(TacticalTheme.gold, lineWidth: 2)
                        )
                        .shadow(color: TacticalTheme.gold.opacity(0.4), radius: 16)
                    
                    Text("⚔️")
                        .font(.system(size: 44))
                        .scaleEffect(isAnimating ? 1.0 : 0.6)
                }
                
                VStack(spacing: 6) {
                    HStack(spacing: 6) {
                        Text("ROS")
                            .font(.system(size: 28, weight: .black))
                            .foregroundColor(TacticalTheme.textPrimary)
                        Text("SOTHAT")
                            .font(.system(size: 28, weight: .black))
                            .foregroundColor(TacticalTheme.gold)
                    }
                    
                    Text("RULES OF SURVIVAL LEGACY COMPANION")
                        .font(.system(size: 10, weight: .bold))
                        .tracking(2.0)
                        .foregroundColor(TacticalTheme.textMuted)
                }
                .opacity(isAnimating ? 1.0 : 0.0)
                .offset(y: isAnimating ? 0 : 15)
                
                Spacer()
                
                // Loading Progress Bar
                VStack(spacing: 8) {
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(TacticalTheme.border)
                            .frame(width: 200, height: 4)
                        
                        Capsule()
                            .fill(
                                LinearGradient(
                                    gradient: Gradient(colors: [TacticalTheme.goldLight, TacticalTheme.goldDark]),
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: 200 * CGFloat(loadingProgress), height: 4)
                            .shadow(color: TacticalTheme.gold, radius: 4)
                    }
                    
                    Text("INITIALIZING TACTICAL PROTOCOLS...")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundColor(TacticalTheme.textMuted)
                }
                .padding(.bottom, 40)
            }
        }
        .onAppear {
            withAnimation(.easeOut(duration: 0.8)) {
                isAnimating = true
            }
            withAnimation(.easeInOut(duration: 1.2).repeatForever(autoreverses: true)) {
                pulseEffect = true
            }
            withAnimation(.linear(duration: 1.5)) {
                loadingProgress = 1.0
            }
            
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
                if authVM.isAuthenticated {
                    launcherVM.navigateTo(.homeDashboard)
                } else {
                    launcherVM.navigateTo(.welcome)
                }
            }
        }
    }
}
