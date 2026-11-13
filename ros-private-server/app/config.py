import os
from typing import Optional
from pydantic import BaseModel, Field

class Settings(BaseModel):
    PROJECT_NAME: str = "ROS Private Server Foundation"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database Configuration (Defaults to SQLite for local development; supports PostgreSQL via asyncpg)
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ros_private.db")
    )
    
    # Security Configuration
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "ros-private-insecure-dev-secret-key-change-in-prod-32bytes")
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    )
    
    # Lobby & Presence Configuration
    LOBBY_HEARTBEAT_TIMEOUT_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("LOBBY_HEARTBEAT_TIMEOUT_SECONDS", "60"))
    )
    
    # Matchmaking Configuration
    MATCHMAKING_MIN_PLAYERS_PER_MATCH: int = Field(
        default_factory=lambda: int(os.getenv("MATCHMAKING_MIN_PLAYERS_PER_MATCH", "2"))
    )
    MATCHMAKING_TICK_INTERVAL_SECONDS: float = Field(
        default_factory=lambda: float(os.getenv("MATCHMAKING_TICK_INTERVAL_SECONDS", "1.0"))
    )
    
    # Server Binding & Architecture Safeguard
    HOST: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    PORT: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    DEBUG: bool = Field(default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true")
    WORKER_GUARD_ENABLED: bool = Field(default_factory=lambda: os.getenv("WORKER_GUARD_ENABLED", "true").lower() == "true")
    MAX_WORKERS_ALLOWED: int = 1

    # Cleanup & TTL Configuration (SEC-03, SEC-04)
    MATCHMAKING_TICKET_TTL_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("MATCHMAKING_TICKET_TTL_SECONDS", "300"))
    )
    MATCHMAKING_TICKET_TIMEOUT_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("MATCHMAKING_TICKET_TIMEOUT_SECONDS", "300"))
    )
    ROOM_IDLE_TIMEOUT_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("ROOM_IDLE_TIMEOUT_SECONDS", "3600"))
    )
    CLEANUP_INTERVAL_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("CLEANUP_INTERVAL_SECONDS", "15"))
    )

    # In-Memory Rate Limiting Configuration (SEC-06)
    RATE_LIMIT_ENABLED: bool = Field(
        default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true")
    RATE_LIMIT_LOGIN_MAX_REQUESTS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_LOGIN_MAX_REQUESTS", "5"))
    )
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_LOGIN_WINDOW_SECONDS", "60"))
    )
    RATE_LIMIT_REGISTER_MAX_REQUESTS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_REGISTER_MAX_REQUESTS", "3"))
    )
    RATE_LIMIT_REGISTER_WINDOW_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_REGISTER_WINDOW_SECONDS", "60"))
    )

    # Email & OTP Configuration (Phase P02)
    OTP_EXPIRE_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("OTP_EXPIRE_SECONDS", "300"))
    )
    OTP_RESEND_COOLDOWN_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
    )
    OTP_MAX_ATTEMPTS: int = Field(
        default_factory=lambda: int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
    )
    OTP_CODE_LENGTH: int = Field(
        default_factory=lambda: int(os.getenv("OTP_CODE_LENGTH", "6"))
    )
    RATE_LIMIT_OTP_REQUEST_MAX: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_OTP_REQUEST_MAX", "5"))
    )
    RATE_LIMIT_OTP_REQUEST_WINDOW_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_OTP_REQUEST_WINDOW_SECONDS", "60"))
    )
    RATE_LIMIT_OTP_VERIFY_MAX: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_OTP_VERIFY_MAX", "10"))
    )
    RATE_LIMIT_OTP_VERIFY_WINDOW_SECONDS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_OTP_VERIFY_WINDOW_SECONDS", "60"))
    )
    EMAIL_PROVIDER: str = Field(
        default_factory=lambda: os.getenv("EMAIL_PROVIDER", "mock")
    )
    SMTP_HOST: str = Field(
        default_factory=lambda: os.getenv("SMTP_HOST", "localhost")
    )
    SMTP_PORT: int = Field(
        default_factory=lambda: int(os.getenv("SMTP_PORT", "587"))
    )
    SMTP_USER: str = Field(
        default_factory=lambda: os.getenv("SMTP_USER", "")
    )
    SMTP_PASSWORD: str = Field(
        default_factory=lambda: os.getenv("SMTP_PASSWORD", "")
    )
    SMTP_FROM: str = Field(
        default_factory=lambda: os.getenv("SMTP_FROM", "noreply@ros-sothat.internal")
    )
    SMTP_TLS: bool = Field(
        default_factory=lambda: os.getenv("SMTP_TLS", "true").lower() == "true"
    )
    OTP_SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("OTP_SECRET_KEY", "")
    )

settings = Settings()
