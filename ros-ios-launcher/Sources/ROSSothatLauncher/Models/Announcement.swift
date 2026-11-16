import Foundation

public struct LauncherAnnouncement: Identifiable, Codable {
    public let id: Int
    public let title: String
    public let summary: String
    public let date: String
    public let tag: String
    public let author: String
    
    public init(
        id: Int,
        title: String,
        summary: String,
        date: String,
        tag: String = "UPDATE",
        author: String = "ROS Admin"
    ) {
        self.id = id
        self.title = title
        self.summary = summary
        self.date = date
        self.tag = tag
        self.author = author
    }
}
