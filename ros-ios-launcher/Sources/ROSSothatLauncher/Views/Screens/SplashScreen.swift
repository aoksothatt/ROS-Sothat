import SwiftUI

public struct SplashScreen: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    @EnvironmentObject public var authVM: AuthViewModel
    @State private var isAnimating: Bool = false
    @State private var pulseEffect: Bool = false
    
    public init() {}
    
    public var body: some View {
        ZStack {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            // Radial background glow
            RadialGradient(
                gradient: Gradient(colors: [TacticalTheme.gold.opacity(0.15), Color.clear]),
                center: .center,
                startRadius: 10,
                endRadius: 280
            )
            .ignoresSafeArea()
            
            VStack(spacing: 24) {
                Spacer()
                
                // Animated Emblem with Real Logo
                ZStack {
                    Circle()
                        .stroke(TacticalTheme.gold.opacity(0.25), lineWidth: 2)
                        .frame(width: 140, height: 140)
                        .scaleEffect(pulseEffect ? 1.15 : 0.95)
                        .opacity(pulseEffect ? 0.3 : 0.8)
                    
                    Image("Logo")
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 110, height: 110)
                        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 20, style: .continuous)
                                .stroke(TacticalTheme.gold, lineWidth: 1.5)
                        )
                        .shadow(color: TacticalTheme.gold.opacity(0.4), radius: 16)
                        .scaleEffect(isAnimating ? 1.0 : 0.8)
                }
                
                VStack(spacing: 6) {
                    HStack(spacing: 6) {
                        Text("ROS")
                            .font(.system(size: 28, weight: .black))
                            .foregroundColor(TacticalTheme.textPrimary)
                        Text("SOTHATT")
                            .font(.system(size: 28, weight: .black))
                            .foregroundColor(TacticalTheme.gold)
                    }
                    
                    Text("RULES OF SURVIVAL LEGACY")
                        .font(.system(size: 11, weight: .bold))
                        .tracking(2.0)
                        .foregroundColor(TacticalTheme.textSecondary)
                }
                .opacity(isAnimating ? 1.0 : 0.0)
                .offset(y: isAnimating ? 0 : 15)
                
                Spacer()
                
                Text("TACTICAL LAUNCHER INITIALIZING...")
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundColor(TacticalTheme.textMuted)
                    .padding(.bottom, 40)
            }
        }
        .onAppear {
            withAnimation(.easeOut(duration: 0.6)) {
                isAnimating = true
            }
            withAnimation(.easeInOut(duration: 1.0).repeatForever(autoreverses: true)) {
                pulseEffect = true
            }
            
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                launcherVM.navigateTo(.homeDashboard)
            }
        }
    }
}
