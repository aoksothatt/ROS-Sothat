from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

class AccountRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, description="Unique username")
    password: str = Field(..., min_length=6, max_length=64, description="Raw password")

    model_config = ConfigDict(extra="forbid")

class AccountLogin(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Raw password")

class GuestRegister(BaseModel):
    device_id: Optional[str] = Field(
        None,
        min_length=4,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_\-\.:]+$",
        description="Optional client hardware/device ID"
    )

class AccountOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str = "player"
    is_banned: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    has_character: bool = False

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    account_id: int
    username: str

class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="Role to assign ('player' or 'admin')")

class BanUpdateRequest(BaseModel):
    is_banned: bool = Field(..., description="Ban status")
    ban_reason: Optional[str] = Field(None, max_length=255, description="Reason for ban")

# -------------------------------------------------------------
# Email OTP Schemas (Phase P02)
# -------------------------------------------------------------

class OTPRequest(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=128,
        description="Player email address"
    )
    purpose: Literal["registration", "login"] = Field(
        ...,
        description="Purpose of verification code ('registration' or 'login')"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(EMAIL_REGEX, clean):
            raise ValueError("Invalid email address format.")
        return clean

class OTPResponse(BaseModel):
    status: str = "ok"
    message: str
    cooldown_seconds: int
    masked_email: str

class OTPVerifyRequest(BaseModel):
    email: str = Field(
        ...,
        min_length=5,
        max_length=128,
        description="Player email address"
    )
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^[0-9]{6}$",
        description="6-digit numeric verification code"
    )
    purpose: Literal["registration", "login"] = Field(
        ...,
        description="Purpose of verification code ('registration' or 'login')"
    )
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=32,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional chosen username for registration"
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(EMAIL_REGEX, clean):
            raise ValueError("Invalid email address format.")
        return clean
