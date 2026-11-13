"""
Structured JSON Security and Audit Logger.

Ensures complete operational visibility while guaranteeing:
- ZERO credential exposure (passwords are never logged).
- ZERO private key or session key leakage.
- Clean structured output for integration into server dashboards.
"""

from typing import Any, Dict, Optional
import json
import logging
import time


class AuditLogger:
    """Emits structured security and operational log events."""

    def __init__(self, logger_name: str = "ros_loginapp_audit"):
        self._logger = logging.getLogger(logger_name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def log_event(self, event_type: str, client_ip: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Formats and emits a sanitized structured audit event.
        """
        # Ensure sensitive fields are never logged
        sanitized_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ['password', 'plain_password', 'private_key', 'session_key']
        }

        record = {
            "timestamp": time.time(),
            "event": event_type,
            "client_ip": client_ip,
            **sanitized_kwargs
        }
        self._logger.info(json.dumps(record))
        return record
