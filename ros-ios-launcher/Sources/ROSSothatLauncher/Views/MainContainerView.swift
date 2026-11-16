import SwiftUI

public struct MainContainerView: View {
    @EnvironmentObject public var launcherVM: LauncherViewModel
    
    public init() {}
    
    public var body: some View {
        ZStack(alignment: .bottom) {
            TacticalTheme.bgPrimary.ignoresSafeArea()
            
            // Tab View Content
            VStack(spacing: 0) {
                Group {
                    switch launcherVM.selectedTab {
                    case 0:
                        HomeScreen()
                    case 1:
                        DownloadManagerScreen()
                    case 2:
                        AccountScreen()
                    default:
                        HomeScreen()
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                
                // Permanent Bottom Navigation Bar
                TacticalBottomBar(selectedTab: $launcherVM.selectedTab)
            }
            .ignoresSafeArea(.keyboard, edges: .bottom)
        }
    }
}

// MARK: - Permanent Bottom Navigation Bar
struct TacticalBottomBar: View {
    @Binding var selectedTab: Int
    
    var body: some View {
        VStack(spacing: 0) {
            // Hairline divider
            Rectangle()
                .fill(TacticalTheme.border)
                .frame(height: 1)
            
            HStack(spacing: 0) {
                NavBarItem(
                    title: "HOME",
                    systemImage: "house.fill",
                    isSelected: selectedTab == 0
                ) {
                    selectedTab = 0
                }
                
                NavBarItem(
                    title: "DOWNLOAD",
                    systemImage: "arrow.down.circle.fill",
                    isSelected: selectedTab == 1
                ) {
                    selectedTab = 1
                }
                
                NavBarItem(
                    title: "ACCOUNT",
                    systemImage: "person.fill",
                    isSelected: selectedTab == 2
                ) {
                    selectedTab = 2
                }
            }
            .frame(height: 52)
            .background(TacticalTheme.bgSecondary)
        }
    }
}

struct NavBarItem: View {
    let title: String
    let systemImage: String
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 3) {
                Image(systemName: systemImage)
                    .font(.system(size: 16, weight: isSelected ? .bold : .regular))
                    .foregroundColor(isSelected ? TacticalTheme.gold : TacticalTheme.textMuted)
                
                Text(title)
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .tracking(0.8)
                    .foregroundColor(isSelected ? TacticalTheme.gold : TacticalTheme.textMuted)
                
                // Subtle active indicator dot
                Circle()
                    .fill(isSelected ? TacticalTheme.gold : Color.clear)
                    .frame(width: 3, height: 3)
            }
            .frame(maxWidth: .infinity)
            .contentShape(Rectangle())
        }
        .buttonStyle(PlainButtonStyle())
    }
}
