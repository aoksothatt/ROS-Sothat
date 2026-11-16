import Foundation
import Combine

public enum DownloadState {
    case notStarted
    case downloading(progress: Double, speedMBs: Double)
    case verifyingChecksum
    case verifiedReady
    case error(String)
}

public class DownloadViewModel: ObservableObject {
    @Published public var downloadState: DownloadState = .notStarted
    @Published public var downloadProgress: Double = 0.0
    @Published public var speedText: String = ""
    @Published public var selectedGuideMethod: Int = 0 // 0 = AltStore, 1 = Sideloadly, 2 = Xcode
    
    private var downloadTimer: Timer?
    
    public init() {}
    
    public func startSimulatedDownload() {
        guard case .notStarted = downloadState else { return }
        downloadState = .downloading(progress: 0.05, speedMBs: 14.8)
        downloadProgress = 0.05
        speedText = "14.8 MB/s"
        
        var current = 0.05
        downloadTimer?.invalidate()
        downloadTimer = Timer.scheduledTimer(withTimeInterval: 0.15, repeats: true) { [weak self] timer in
            guard let self = self else {
                timer.invalidate()
                return
            }
            current += 0.08
            if current >= 1.0 {
                timer.invalidate()
                self.downloadProgress = 1.0
                self.downloadState = .verifyingChecksum
                self.speedText = "Calculating SHA-256..."
                
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) {
                    self.downloadState = .verifiedReady
                    self.speedText = "Integrity Verified ✓"
                }
            } else {
                self.downloadProgress = current
                self.downloadState = .downloading(progress: current, speedMBs: 15.2)
                self.speedText = "15.2 MB/s"
            }
        }
    }
    
    public func resetDownload() {
        downloadTimer?.invalidate()
        downloadState = .notStarted
        downloadProgress = 0.0
        speedText = ""
    }
}
