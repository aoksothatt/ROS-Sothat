import Foundation
import Combine

/// Architecture configuration for connecting to private server infrastructure.
/// Provides real-time asynchronous health polling against backend /health endpoint.
public enum HealthStatus: Equatable {
    case connecting
    case online(latencyMs: Int)
    case offline(reason: String)

    public var displayText: String {
        switch self {
        case .connecting:
            return "CONNECTING..."
        case .online(let ms):
            return "ONLINE (\(ms)ms)"
        case .offline:
            return "OFFLINE"
        }
    }
}

public class ServerConfig: ObservableObject {
    public static let shared = ServerConfig()

    // MARK: - Configurable Private Server Endpoints
    @Published public var serverHost: String = "127.0.0.1"
    @Published public var serverPort: Int = 8000
    @Published public var apiBaseURL: String = "http://127.0.0.1:8000"
    @Published public var downloadSourceURL: String = "https://rossothat.com/download/RoS-Legacy-iOS.ipa"

    // MARK: - Server State Architecture
    @Published public var isConnected: Bool = false
    @Published public var healthStatus: HealthStatus = .connecting
    @Published public var latencyMs: Int? = nil
    @Published public var lastCheckedTime: Date? = nil

    private var pollingTask: Task<Void, Never>?
    private var isPollingActive: Bool = false

    public init() {}

    /// Resolves the actual existing backend health endpoint.
    public var healthURL: URL? {
        let base = apiBaseURL.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        return URL(string: "\(base)/health")
    }

    /// Returns the resolved game IPA download URL.
    public var downloadURL: URL? {
        return URL(string: downloadSourceURL)
    }

    // MARK: - Asynchronous Health Polling

    @MainActor
    public func checkHealthNow() async {
        guard let url = healthURL else {
            self.healthStatus = .offline(reason: "Invalid URL")
            self.isConnected = false
            self.latencyMs = nil
            return
        }

        let start = CFAbsoluteTimeGetCurrent()
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.timeoutInterval = 3.0
        request.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData

        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            let elapsed = Int((CFAbsoluteTimeGetCurrent() - start) * 1000)

            if let httpResp = response as? HTTPURLResponse, (200...299).contains(httpResp.statusCode) {
                let ms = max(1, elapsed)
                self.latencyMs = ms
                self.isConnected = true
                self.healthStatus = .online(latencyMs: ms)
                self.lastCheckedTime = Date()
            } else {
                let code = (response as? HTTPURLResponse)?.statusCode ?? 0
                self.isConnected = false
                self.latencyMs = nil
                self.healthStatus = .offline(reason: "HTTP \(code)")
                self.lastCheckedTime = Date()
            }
        } catch {
            self.isConnected = false
            self.latencyMs = nil
            self.healthStatus = .offline(reason: error.localizedDescription)
            self.lastCheckedTime = Date()
        }
    }

    // MARK: - Lifecycle-Safe Polling Control

    public func startPolling(intervalSeconds: TimeInterval = 10.0) {
        guard !isPollingActive else { return }
        isPollingActive = true

        pollingTask?.cancel()
        pollingTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.checkHealthNow()
                do {
                    try await Task.sleep(nanoseconds: UInt64(intervalSeconds * 1_000_000_000))
                } catch {
                    break
                }
            }
        }
    }

    public func stopPolling() {
        isPollingActive = false
        pollingTask?.cancel()
        pollingTask = nil
    }
}
