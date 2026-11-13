"""
Configuration for Local Synthetic Mercury UDP Gateway Prototype
Phase 6.2B.8 - Research & Prototype Only

Strict Security Controls:
- MUST bind strictly to 127.0.0.1.
- Absolutely NO external or 0.0.0.0 network interfaces.
- Assertion halts process immediately if non-localhost binding is attempted.
"""

import sys


class SecurityError(Exception):
    """Raised when security boundaries or isolation rules are breached."""
    pass


class GatewayConfig:
    # Strictly localhost only
    HOST = "127.0.0.1"
    PORT = 30042
    MAX_PACKET_SIZE = 2048
    SOCKET_TIMEOUT = 1.0  # seconds (short timeout to prevent hangs)
    BUFFER_SIZE = 4096

    # Master synthetic key for deterministic testing (56 bytes Blowfish key)
    SYNTHETIC_MASTER_KEY = (
        b"ROS_SOTHAT_DETERMINISTIC_SYNTHETIC_BLOWFISH_SESSION_KEY!"
    )
    assert len(SYNTHETIC_MASTER_KEY) == 56

    # Secondary synthetic key for multi-channel / isolation testing
    SYNTHETIC_CLIENT2_KEY = (
        b"ROS_SOTHAT_SECONDARY_SYNTHETIC_BLOWFISH_SESSION_KEY_02!!"
    )
    assert len(SYNTHETIC_CLIENT2_KEY) == 56

    @classmethod
    def validate_bind_address(cls, host: str):
        """
        Startup assertion: Strictly forbids any interface other than 127.0.0.1.
        Prevents accidental LAN (0.0.0.0, 192.168.x.x, 10.x.x.x) exposure.
        """
        if host != "127.0.0.1":
            raise SecurityError(
                f"[SECURITY ALERT] Gateway refused to initialize on bind address '{host}'. "
                f"Phase 6.2B.8 strictly permits binding exclusively to '127.0.0.1'. "
                f"Exposing to external or 0.0.0.0 interfaces is strictly prohibited."
            )
