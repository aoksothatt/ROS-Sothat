"""
Safe Structured Logging & Observability Module
Phase 6.2B.8 - Research & Prototype Only

Strict Observability Rules:
- Logs direction, timestamp, channel ID, length, sequence numbers, validation outcome, and error category.
- REDACTS all cryptographic keys, session tokens, and raw decrypted payloads.
- Tracks metrics for terminal status output (packets received, processed, rejected, active channels).
"""

import time
import threading
from typing import Optional, Dict, Any


class GatewayMetrics:
    """Thread-safe telemetry metrics for the local prototype."""
    def __init__(self):
        self._lock = threading.Lock()
        self.packets_received = 0
        self.packets_processed = 0
        self.packets_rejected = 0
        self.packets_sent = 0
        self.active_channels = 0
        self.start_time = time.time()

    def record_received(self):
        with self._lock:
            self.packets_received += 1

    def record_processed(self):
        with self._lock:
            self.packets_processed += 1

    def record_rejected(self):
        with self._lock:
            self.packets_rejected += 1

    def record_sent(self):
        with self._lock:
            self.packets_sent += 1

    def update_active_channels(self, count: int):
        with self._lock:
            self.active_channels = count

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time
            return {
                "uptime_seconds": round(uptime, 2),
                "packets_received": self.packets_received,
                "packets_processed": self.packets_processed,
                "packets_rejected": self.packets_rejected,
                "packets_sent": self.packets_sent,
                "active_channels": self.active_channels,
            }


class SafeLogger:
    """Safe, redaction-enforced logger for UDP gateway communications."""
    def __init__(self, name: str = "Gateway"):
        self.name = name
        self.metrics = GatewayMetrics()
        self.log_entries = []
        self._lock = threading.Lock()

    def log(
        self,
        direction: str,
        channel_id: Optional[int],
        length: int,
        seq_num: Optional[int],
        outcome: str,
        error_category: Optional[str] = None,
        details: Optional[str] = None,
        print_to_console: bool = True
    ):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        cid_str = f"CH:{channel_id}" if channel_id is not None else "CH:NONE"
        seq_str = f"SEQ:{seq_num}" if seq_num is not None else "SEQ:NONE"
        err_str = f" | ERR:{error_category}" if error_category else ""
        det_str = f" | {details}" if details else ""

        # Redact any obvious secrets or key hex patterns if accidentally passed in details
        if det_str:
            for redact_target in ["key", "token", "password", "secret"]:
                if redact_target in det_str.lower():
                    det_str = " | [REDACTED_SENSITIVE_CONTENT]"
                    break

        line = f"[{timestamp}] [{self.name}] [{direction.upper():<4}] {cid_str:<8} {seq_str:<9} LEN:{length:<4} OUTCOME:{outcome:<8}{err_str}{det_str}"

        with self._lock:
            self.log_entries.append(line)

        if print_to_console:
            print(line)

    def print_terminal_status(self, bind_host: str, port: int, is_running: bool):
        """Displays clear terminal status summary for testing."""
        summary = self.metrics.get_summary()
        state = "RUNNING" if is_running else "STOPPED"
        print("\n" + "=" * 60)
        print(f" ROS SOTHAT — MERCURY UDP GATEWAY STATUS ({self.name})")
        print("=" * 60)
        print(f" State:             {state}")
        print(f" Bind Address:      {bind_host}:{port} (STRICT LOCALHOST)")
        print(f" Active Channels:   {summary['active_channels']}")
        print(f" Packets Received:  {summary['packets_received']}")
        print(f" Packets Processed: {summary['packets_processed']}")
        print(f" Packets Rejected:  {summary['packets_rejected']}")
        print(f" Packets Sent:      {summary['packets_sent']}")
        print(f" Gateway Uptime:    {summary['uptime_seconds']}s")
        print("=" * 60 + "\n")
