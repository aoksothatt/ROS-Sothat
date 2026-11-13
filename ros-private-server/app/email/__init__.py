"""
Email provider package for ROS Sothat Private Server.
Provides pluggable email delivery providers: Mock, Console, and SMTP.
"""
from app.email.provider import BaseEmailProvider, MockEmailProvider, ConsoleEmailProvider, SmtpEmailProvider, get_email_provider, set_email_provider

__all__ = [
    "BaseEmailProvider",
    "MockEmailProvider",
    "ConsoleEmailProvider",
    "SmtpEmailProvider",
    "get_email_provider",
    "set_email_provider",
]
