import time
from typing import Dict, List, Optional
from fastapi import Request, HTTPException, status
from app.config import settings

class InMemoryRateLimiter:
    _instance: Optional["InMemoryRateLimiter"] = None

    @classmethod
    def get_instance(cls) -> "InMemoryRateLimiter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Maps key (e.g. "login:127.0.0.1") -> list of epoch timestamps
        self._history: Dict[str, List[float]] = {}

    def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> None:
        """
        Sliding-window rate limiter check.
        Raises HTTP 429 if request count exceeds max_requests within window_seconds.
        """
        if not settings.RATE_LIMIT_ENABLED:
            return

        now = time.time()
        cutoff = now - window_seconds

        history = self._history.setdefault(key, [])
        # Prune timestamps older than cutoff
        self._history[key] = [t for t in history if t > cutoff]
        active_history = self._history[key]

        if len(active_history) >= max_requests:
            oldest = active_history[0]
            retry_after = max(1, int(oldest + window_seconds - now) + 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests allowed per {window_seconds}s.",
                headers={"Retry-After": str(retry_after)}
            )

        self._history[key].append(now)

    def reset(self) -> None:
        """Clear all rate limiting state (useful for tests)."""
        self._history.clear()

def get_client_ip(request: Request) -> str:
    """Extract client IP from request, taking proxy forwarding into account."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"

def rate_limit_login(request: Request) -> None:
    ip = get_client_ip(request)
    limiter = InMemoryRateLimiter.get_instance()
    limiter.check(
        key=f"login:{ip}",
        max_requests=settings.RATE_LIMIT_LOGIN_MAX_REQUESTS,
        window_seconds=settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS
    )

def rate_limit_register(request: Request) -> None:
    ip = get_client_ip(request)
    limiter = InMemoryRateLimiter.get_instance()
    limiter.check(
        key=f"register:{ip}",
        max_requests=settings.RATE_LIMIT_REGISTER_MAX_REQUESTS,
        window_seconds=settings.RATE_LIMIT_REGISTER_WINDOW_SECONDS
    )

def rate_limit_otp_request(request: Request) -> None:
    ip = get_client_ip(request)
    limiter = InMemoryRateLimiter.get_instance()
    limiter.check(
        key=f"otp_request:{ip}",
        max_requests=settings.RATE_LIMIT_OTP_REQUEST_MAX,
        window_seconds=settings.RATE_LIMIT_OTP_REQUEST_WINDOW_SECONDS
    )

def rate_limit_otp_verify(request: Request) -> None:
    ip = get_client_ip(request)
    limiter = InMemoryRateLimiter.get_instance()
    limiter.check(
        key=f"otp_verify:{ip}",
        max_requests=settings.RATE_LIMIT_OTP_VERIFY_MAX,
        window_seconds=settings.RATE_LIMIT_OTP_VERIFY_WINDOW_SECONDS
    )
