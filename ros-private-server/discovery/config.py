"""
Configuration and data models for ROS Sothat Server Discovery service.
Defines server cluster parameters matching the legacy client specification.
"""

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ServerEntry:
    """
    Represents a single server cluster entry as consumed by the ROS Legacy client.
    Format:
    <zone> <numberSt> <netSt> <serverSt> <name> <oriName> <telIP> <cncIP> <eduIP> <hostID> <loginIP>:<loginPort>:<battlePort>
    """
    zone: int = 1
    number_st: int = 1
    net_st: int = 0         # 0 = Normal, 1 = Busy
    server_st: int = 1      # 1 = Smooth/Online, 2 = Crowded, 3 = Maintenance
    name: str = "ROS_Sothat_Local"
    ori_name: str = "Sothat"
    tel_ip: str = "127.0.0.1"
    cnc_ip: str = "127.0.0.1"
    edu_ip: str = "127.0.0.1"
    host_id: int = 1001
    login_ip: str = "127.0.0.1"
    login_port: int = 20001
    battle_port: int = 20002

    def validate(self) -> None:
        """Validate fields against protocol constraints."""
        if self.zone < 1:
            raise ValueError(f"zone must be >= 1, got {self.zone}")
        if self.number_st < 0:
            raise ValueError(f"number_st must be >= 0, got {self.number_st}")
        if self.net_st not in (0, 1):
            raise ValueError(f"net_st must be 0 (normal) or 1 (busy), got {self.net_st}")
        if self.server_st not in (1, 2, 3):
            raise ValueError(f"server_st must be 1 (online), 2 (crowded), or 3 (maintenance), got {self.server_st}")
        if not self.name or " " in self.name:
            raise ValueError(f"name must be non-empty and cannot contain spaces, got {repr(self.name)}")
        if not self.ori_name or " " in self.ori_name:
            raise ValueError(f"ori_name must be non-empty and cannot contain spaces, got {repr(self.ori_name)}")
        for ip_field, val in [("tel_ip", self.tel_ip), ("cnc_ip", self.cnc_ip), ("edu_ip", self.edu_ip), ("login_ip", self.login_ip)]:
            if not val or " " in val:
                raise ValueError(f"{ip_field} must be a valid host string without spaces, got {repr(val)}")
        if self.host_id <= 0:
            raise ValueError(f"host_id must be > 0, got {self.host_id}")
        if not (1 <= self.login_port <= 65535):
            raise ValueError(f"login_port must be in range 1-65535, got {self.login_port}")
        if self.battle_port and not (1 <= self.battle_port <= 65535):
            raise ValueError(f"battle_port must be in range 1-65535, got {self.battle_port}")

    def to_line(self) -> str:
        """Format the entry into the exact single line format required by the client."""
        self.validate()
        port_spec = f"{self.login_ip}:{self.login_port}"
        if self.battle_port:
            port_spec += f":{self.battle_port}"
        
        return (
            f"{self.zone} {self.number_st} {self.net_st} {self.server_st} "
            f"{self.name} {self.ori_name} {self.tel_ip} {self.cnc_ip} {self.edu_ip} "
            f"{self.host_id} {port_spec}"
        )


class DiscoverySettings:
    """Environment-driven configuration for the discovery service."""
    def __init__(self):
        self.DISCOVERY_HOST: str = os.getenv("DISCOVERY_HOST", "127.0.0.1")
        self.DISCOVERY_PORT: int = int(os.getenv("DISCOVERY_PORT", "50010"))
        self.LOGIN_UDP_HOST: str = os.getenv("LOGIN_UDP_HOST", "127.0.0.1")
        self.LOGIN_UDP_PORT: int = int(os.getenv("LOGIN_UDP_PORT", "20001"))
        self.BATTLE_UDP_PORT: int = int(os.getenv("BATTLE_UDP_PORT", "20002"))
        self.SERVER_NAME: str = os.getenv("SERVER_NAME", "ROS_Sothat_Private")
        self.CLUSTER_NAME: str = os.getenv("CLUSTER_NAME", "Sothat")
        self.ZONE: int = int(os.getenv("SERVER_ZONE", "1"))
        self.HOST_ID: int = int(os.getenv("SERVER_HOST_ID", "1001"))

    def create_default_entry(self) -> ServerEntry:
        """Create a default local development cluster entry."""
        return ServerEntry(
            zone=self.ZONE,
            number_st=1,
            net_st=0,
            server_st=1,
            name=self.SERVER_NAME,
            ori_name=self.CLUSTER_NAME,
            tel_ip=self.LOGIN_UDP_HOST,
            cnc_ip=self.LOGIN_UDP_HOST,
            edu_ip=self.LOGIN_UDP_HOST,
            host_id=self.HOST_ID,
            login_ip=self.LOGIN_UDP_HOST,
            login_port=self.LOGIN_UDP_PORT,
            battle_port=self.BATTLE_UDP_PORT
        )


discovery_settings = DiscoverySettings()
