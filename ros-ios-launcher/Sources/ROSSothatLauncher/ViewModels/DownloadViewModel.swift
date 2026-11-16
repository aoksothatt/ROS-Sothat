import Foundation
import Combine
import UIKit

public enum DownloadStatus: Equatable {
    case notStarted
    case connecting
    case downloading(progress: Double, bytesWritten: Int64, totalBytes: Int64, speedText: String)
    case completed(localURL: URL, fileSizeFormatted: String)
    case failed(errorMessage: String)
}

public class DownloadViewModel: NSObject, ObservableObject, URLSessionDownloadDelegate {
    @Published public var status: DownloadStatus = .notStarted
    @Published public var downloadProgress: Double = 0.0
    @Published public var progressText: String = ""
    @Published public var speedText: String = ""
    @Published public var localFileURL: URL?
    @Published public var isGameInstalled: Bool = false
    
    private var downloadTask: URLSessionDownloadTask?
    private var session: URLSession?
    private var lastBytesWritten: Int64 = 0
    private var lastSpeedCheckTime: Date?
    
    public override init() {
        super.init()
        checkLocalFile()
        checkGameInstallation()
    }
    
    private var documentsDirectory: URL? {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first
    }
    
    public var destinationURL: URL? {
        documentsDirectory?.appendingPathComponent("ROSSothatGame.ipa")
    }
    
    /// Checks if the game package is already downloaded in local storage.
    public func checkLocalFile() {
        guard let dest = destinationURL else { return }
        if FileManager.default.fileExists(atPath: dest.path) {
            do {
                let attrs = try FileManager.default.attributesOfItem(atPath: dest.path)
                let fileSize = attrs[.size] as? Int64 ?? 0
                let formatted = ByteCountFormatter.string(fromByteCount: fileSize, countStyle: .file)
                self.localFileURL = dest
                self.downloadProgress = 1.0
                self.status = .completed(localURL: dest, fileSizeFormatted: formatted)
            } catch {
                self.localFileURL = dest
                self.status = .completed(localURL: dest, fileSizeFormatted: "Downloaded")
            }
        } else {
            self.localFileURL = nil
            self.status = .notStarted
            self.downloadProgress = 0.0
            self.progressText = ""
            self.speedText = ""
        }
    }
    
    /// Checks whether the game client has already been sideloaded on iOS.
    public func checkGameInstallation() {
        if let url = URL(string: "rosmobile://"), UIApplication.shared.canOpenURL(url) {
            self.isGameInstalled = true
        } else {
            self.isGameInstalled = false
        }
    }
    
    /// Starts real download from the configured URL.
    public func startDownload(from url: URL) {
        // Cancel existing task if running
        downloadTask?.cancel()
        
        status = .connecting
        downloadProgress = 0.0
        progressText = "Connecting to download server..."
        speedText = ""
        lastBytesWritten = 0
        lastSpeedCheckTime = Date()
        
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 3600
        
        session = URLSession(configuration: config, delegate: self, delegateQueue: nil)
        downloadTask = session?.downloadTask(with: url)
        downloadTask?.resume()
    }
    
    /// Cancels active download task.
    public func cancelDownload() {
        downloadTask?.cancel()
        downloadTask = nil
        session?.invalidateAndCancel()
        checkLocalFile()
    }
    
    /// Removes local downloaded IPA file to allow fresh re-download.
    public func deleteLocalFile() {
        guard let dest = destinationURL, FileManager.default.fileExists(atPath: dest.path) else { return }
        try? FileManager.default.removeItem(at: dest)
        checkLocalFile()
    }
    
    /// Launches the sideloaded game client if supported.
    public func launchGame() {
        if let url = URL(string: "rosmobile://") {
            UIApplication.shared.open(url, options: [:], completionHandler: nil)
        }
    }
    
    // MARK: - URLSessionDownloadDelegate
    
    public func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didWriteData bytesWritten: Int64,
        totalBytesWritten: Int64,
        totalBytesExpectedToWrite: Int64
    ) {
        let now = Date()
        var currentSpeedText = speedText
        
        if let lastCheck = lastSpeedCheckTime {
            let elapsed = now.timeIntervalSince(lastCheck)
            if elapsed >= 0.5 {
                let bytesDiff = totalBytesWritten - lastBytesWritten
                let bytesPerSec = Double(bytesDiff) / elapsed
                let speedMB = bytesPerSec / (1024 * 1024)
                currentSpeedText = String(format: "%.1f MB/s", speedMB)
                self.lastBytesWritten = totalBytesWritten
                self.lastSpeedCheckTime = now
            }
        } else {
            lastSpeedCheckTime = now
            lastBytesWritten = totalBytesWritten
        }
        
        let progress = totalBytesExpectedToWrite > 0
            ? Double(totalBytesWritten) / Double(totalBytesExpectedToWrite)
            : 0.0
        
        let writtenStr = ByteCountFormatter.string(fromByteCount: totalBytesWritten, countStyle: .file)
        let totalStr = totalBytesExpectedToWrite > 0
            ? ByteCountFormatter.string(fromByteCount: totalBytesExpectedToWrite, countStyle: .file)
            : "Unknown"
        let pText = "\(writtenStr) / \(totalStr)"
        
        DispatchQueue.main.async {
            self.downloadProgress = progress
            self.progressText = pText
            self.speedText = currentSpeedText
            self.status = .downloading(
                progress: progress,
                bytesWritten: totalBytesWritten,
                totalBytes: totalBytesExpectedToWrite,
                speedText: currentSpeedText
            )
        }
    }
    
    public func urlSession(
        _ session: URLSession,
        downloadTask: URLSessionDownloadTask,
        didFinishDownloadingTo location: URL
    ) {
        guard let dest = destinationURL else {
            DispatchQueue.main.async {
                self.status = .failed(errorMessage: "Unable to access local Documents directory.")
            }
            return
        }
        
        // Remove existing file if present
        if FileManager.default.fileExists(atPath: dest.path) {
            try? FileManager.default.removeItem(at: dest)
        }
        
        do {
            try FileManager.default.moveItem(at: location, to: dest)
            let attrs = try FileManager.default.attributesOfItem(atPath: dest.path)
            let fileSize = attrs[.size] as? Int64 ?? 0
            let formatted = ByteCountFormatter.string(fromByteCount: fileSize, countStyle: .file)
            
            DispatchQueue.main.async {
                self.localFileURL = dest
                self.downloadProgress = 1.0
                self.progressText = "Download Complete"
                self.speedText = ""
                self.status = .completed(localURL: dest, fileSizeFormatted: formatted)
                self.checkGameInstallation()
            }
        } catch {
            DispatchQueue.main.async {
                self.status = .failed(errorMessage: "Failed to save file: \(error.localizedDescription)")
            }
        }
    }
    
    public func urlSession(
        _ session: URLSession,
        task: URLSessionTask,
        didCompleteWithError error: Error?
    ) {
        if let error = error {
            // Ignore cancellation error
            if (error as NSError).code == NSURLErrorCancelled {
                return
            }
            DispatchQueue.main.async {
                self.status = .failed(errorMessage: error.localizedDescription)
            }
        } else if let response = task.response as? HTTPURLResponse, response.statusCode >= 400 {
            DispatchQueue.main.async {
                self.status = .failed(errorMessage: "HTTP Error \(response.statusCode): Server returned an error.")
            }
        }
    }
}
