import abc
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from app.config import settings
from app.logging_config import get_logger

logger = get_logger("email_provider")

def mask_email(email: str) -> str:
    """Safely mask an email address for logs and responses (e.g., j***n@example.com)."""
    if not email or "@" not in email:
        return "***"
    local_part, domain = email.split("@", 1)
    if len(local_part) <= 2:
        masked_local = local_part[0] + "***"
    else:
        masked_local = local_part[0] + "***" + local_part[-1]
    return f"{masked_local}@{domain}"

class BaseEmailProvider(abc.ABC):
    """Abstract base class for email delivery providers."""

    @abc.abstractmethod
    async def send_otp(self, to_email: str, otp_code: str, purpose: str) -> bool:
        """Send a one-time verification password to the target email."""
        raise NotImplementedError

class MockEmailProvider(BaseEmailProvider):
    """
    In-memory mock email provider for testing and development.
    Records all dispatched emails in memory without external network calls.
    """
    def __init__(self):
        self.sent_messages: List[Dict[str, Any]] = []

    async def send_otp(self, to_email: str, otp_code: str, purpose: str) -> bool:
        record = {
            "to_email": to_email.strip().lower(),
            "otp_code": otp_code,
            "purpose": purpose,
        }
        self.sent_messages.append(record)
        logger.info(f"[MockEmail] Recorded OTP for {mask_email(to_email)} (purpose={purpose})")
        return True

    def get_latest_otp_for(self, email: str) -> Optional[str]:
        target = email.strip().lower()
        for msg in reversed(self.sent_messages):
            if msg["to_email"] == target:
                return msg["otp_code"]
        return None

    def clear(self) -> None:
        self.sent_messages.clear()

class ConsoleEmailProvider(BaseEmailProvider):
    """
    Console email provider that logs masked notifications for local development.
    """
    async def send_otp(self, to_email: str, otp_code: str, purpose: str) -> bool:
        masked = mask_email(to_email)
        logger.info(f"[ConsoleEmail] OTP generated for {masked} (purpose={purpose})")
        # In local debug mode, print formatted banner to stdout
        if settings.DEBUG:
            print(f"\n==================== [DEV OTP DISPATCH] ====================")
            print(f"Target:  {masked}")
            print(f"Purpose: {purpose}")
            print(f"Code:    {otp_code} (Valid for {settings.OTP_EXPIRE_SECONDS}s)")
            print(f"===========================================================\n")
        return True

class SmtpEmailProvider(BaseEmailProvider):
    """
    Production-grade SMTP email delivery provider with TLS/STARTTLS support.
    Runs blocking socket I/O in a separate thread pool.
    """
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        from_address: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.user = user if user is not None else settings.SMTP_USER
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.from_address = from_address or settings.SMTP_FROM
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_TLS

    def _send_sync(self, to_email: str, subject: str, text_body: str, html_body: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_address
        msg["To"] = to_email

        part1 = MIMEText(text_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")
        msg.attach(part1)
        msg.attach(part2)

        try:
            if self.port == 465:
                # Direct SSL connection
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=10)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=10)
                if self.use_tls:
                    server.starttls()

            if self.user and self.password:
                server.login(self.user, self.password)

            server.sendmail(self.from_address, [to_email], msg.as_string())
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP to {mask_email(to_email)}: {e}")
            return False

    async def send_otp(self, to_email: str, otp_code: str, purpose: str) -> bool:
        masked = mask_email(to_email)
        subject = f"ROS Sothat Verification Code: {otp_code}"
        
        purpose_label = "Registration" if purpose == "registration" else "Login"
        
        text_body = (
            f"Hello,\n\n"
            f"Your ROS Sothat one-time verification code is: {otp_code}\n\n"
            f"This code will expire in {int(settings.OTP_EXPIRE_SECONDS / 60)} minutes.\n"
            f"If you did not request this {purpose_label.lower()} code, please ignore this email.\n\n"
            f"— ROS Sothat Team"
        )
        
        html_body = (
            f"<html><body>"
            f"<h2>ROS Sothat Private Server</h2>"
            f"<p>Your one-time verification code for <strong>{purpose_label}</strong> is:</p>"
            f"<p style='font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #1a73e8;'>{otp_code}</p>"
            f"<p>This code will expire in {int(settings.OTP_EXPIRE_SECONDS / 60)} minutes.</p>"
            f"<p style='color: #666;'>If you did not request this verification code, please ignore this email.</p>"
            f"</body></html>"
        )

        logger.info(f"Dispatching SMTP OTP email to {masked} (purpose={purpose})")
        return await asyncio.to_thread(self._send_sync, to_email, subject, text_body, html_body)

# Singleton state management
_active_provider: Optional[BaseEmailProvider] = None

def get_email_provider() -> BaseEmailProvider:
    """Return the currently configured email provider singleton."""
    global _active_provider
    if _active_provider is not None:
        return _active_provider

    provider_type = (settings.EMAIL_PROVIDER or "mock").lower()
    if provider_type == "mock":
        _active_provider = MockEmailProvider()
    elif provider_type == "console":
        _active_provider = ConsoleEmailProvider()
    elif provider_type == "smtp":
        _active_provider = SmtpEmailProvider()
    else:
        logger.warning(f"Unknown EMAIL_PROVIDER '{provider_type}', falling back to MockEmailProvider")
        _active_provider = MockEmailProvider()

    return _active_provider

def set_email_provider(provider: Optional[BaseEmailProvider]) -> None:
    """Override or reset the active email provider singleton (used for tests)."""
    global _active_provider
    _active_provider = provider
