"""
Discovery service managing ROS Sothat server entries and generating server_list_ios.txt.
"""

from typing import Dict, List, Optional
from discovery.config import ServerEntry, discovery_settings
from discovery.parser import parse_sa_server_list


class DiscoveryService:
    """Service responsible for generating and validating the discovery server list."""

    _instance: Optional['DiscoveryService'] = None

    def __init__(self):
        self._servers: List[ServerEntry] = []
        self._init_defaults()

    @classmethod
    def get_instance(cls) -> 'DiscoveryService':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def _init_defaults(self) -> None:
        """Initialize with default cluster from settings."""
        self._servers.append(discovery_settings.create_default_entry())

    def get_servers(self) -> List[ServerEntry]:
        """Return registered servers."""
        return list(self._servers)

    def set_servers(self, servers: List[ServerEntry]) -> None:
        """Replace all servers after validating each entry."""
        for s in servers:
            s.validate()
        self._servers = list(servers)

    def add_server(self, server: ServerEntry) -> None:
        """Add a validated server entry."""
        server.validate()
        self._servers.append(server)

    def clear_servers(self) -> None:
        """Clear all registered servers."""
        self._servers.clear()

    def generate_server_list_content(self, include_comments: bool = True) -> str:
        """
        Generate the raw server_list_ios.txt file content.
        Validates the output using the recovered client-side parser before returning.
        """
        lines = []
        if include_comments:
            lines.append("# Rules of Survival Private Server Discovery")
            lines.append("# Format: <zone> <numberSt> <netSt> <serverSt> <name> <oriName> <telIP> <cncIP> <eduIP> <hostID> <loginIP>:<loginPort>:<battlePort>")
        
        for server in self._servers:
            lines.append(server.to_line())

        content = "\n".join(lines) + "\n"

        # Validate generated content against the recovered client-side parser
        parsed = parse_sa_server_list(content)
        if len(parsed) != len(self._servers):
            raise RuntimeError(
                f"Discovery service generated invalid content: expected {len(self._servers)} "
                f"parseable server entries, but recovered parser only found {len(parsed)}."
            )

        return content
