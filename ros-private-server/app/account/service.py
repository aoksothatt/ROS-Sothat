import hashlib
import hmac
import secrets
import base64
import json
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import get_db
from app.account.models import Account, EmailOTP
from app.account.repository import AccountRepository
from app.account.schemas import (
    AccountRegister,
    AccountLogin,
    TokenResponse,
    AccountOut,
    OTPRequest,
    OTPResponse,
    OTPVerifyRequest,
)
from app.email.provider import get_email_provider, mask_email
from app.logging_config import get_logger

logger = get_logger("account_service")
security = HTTPBearer(auto_error=False)

class AccountService:
    @staticmethod
    def generate_salt() -> str:
        return secrets.token_hex(16)

    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()

    @classmethod
    def verify_password(cls, plain_password: str, salt: str, password_hash: str) -> bool:
        if password_hash.startswith("*OTP_ONLY_"):
            return False
        computed = cls.hash_password(plain_password, salt)
        return hmac.compare_digest(computed, password_hash)

    # -------------------------------------------------------------
    # OTP Cryptographic Helpers (Phase P02 / P02.1 HMAC-SHA256)
    # -------------------------------------------------------------

    @classmethod
    def get_otp_hmac_secret(cls) -> bytes:
        """
        Retrieve and validate the server-side HMAC secret for OTP hashing.
        Prefers dedicated OTP_SECRET_KEY; falls back to SECRET_KEY if not configured.
        Raises ValueError if the secret is missing or too short (< 16 bytes).
        Never logs or exposes the raw secret bytes.
        """
        secret = (settings.OTP_SECRET_KEY or "").strip()
        if not secret:
            secret = (settings.SECRET_KEY or "").strip()

        if not secret:
            raise ValueError("Missing OTP secret key: neither OTP_SECRET_KEY nor SECRET_KEY is configured.")

        if len(secret) < 16:
            raise ValueError("Invalid OTP secret key: must be at least 16 bytes for cryptographic security.")

        return secret.encode("utf-8")

    @staticmethod
    def generate_otp_code() -> str:
        """Cryptographically secure 6-digit numeric OTP [100000, 999999]."""
        return f"{secrets.randbelow(900000) + 100000:06d}"

    @classmethod
    def hash_otp(cls, code: str, salt: str, secret: Optional[bytes] = None) -> str:
        """
        Server-side keyed HMAC-SHA256 hash of verification code.
        Format: HMAC-SHA256(secret, salt:code) -> 64-char hex string.
        """
        if secret is None:
            secret = cls.get_otp_hmac_secret()
        message = f"{salt}:{code}".encode("utf-8")
        return hmac.new(secret, message, hashlib.sha256).hexdigest()

    @classmethod
    def verify_otp_hash(
        cls,
        code: str,
        salt: str,
        expected_hash: str,
        secret: Optional[bytes] = None
    ) -> bool:
        """Timing-safe verification of OTP hash using constant-time comparison."""
        computed = cls.hash_otp(code, salt, secret=secret)
        return hmac.compare_digest(computed, expected_hash)

    # -------------------------------------------------------------
    # Token Helpers
    # -------------------------------------------------------------

    @staticmethod
    def create_token(account_id: int, username: str, role: str = "player") -> str:
        expires_at = int(time.time()) + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
        payload = {
            "sub": account_id,
            "username": username,
            "role": role,
            "exp": expires_at
        }
        raw_json = json.dumps(payload, separators=(',', ':')).encode("utf-8")
        b64_payload = base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")
        
        signature = hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            b64_payload.encode("ascii"),
            hashlib.sha256
        ).digest()
        b64_sig = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        
        return f"{b64_payload}.{b64_sig}"

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None
            b64_payload, b64_sig = parts
            
            # Reconstruct signature
            expected_sig = hmac.new(
                settings.SECRET_KEY.encode("utf-8"),
                b64_payload.encode("ascii"),
                hashlib.sha256
            ).digest()
            expected_b64_sig = base64.urlsafe_b64encode(expected_sig).decode("ascii").rstrip("=")
            
            if not hmac.compare_digest(b64_sig, expected_b64_sig):
                return None
            
            # Decode payload
            padding = 4 - (len(b64_payload) % 4)
            if padding != 4:
                b64_payload += "=" * padding
            raw_json = base64.urlsafe_b64decode(b64_payload.encode("ascii")).decode("utf-8")
            payload = json.loads(raw_json)
            
            # Check expiry
            if time.time() > payload.get("exp", 0):
                return None
                
            return payload
        except Exception:
            return None

    def __init__(self, repository: AccountRepository):
        self.repository = repository

    # -------------------------------------------------------------
    # Traditional Account Workflows
    # -------------------------------------------------------------

    async def register(self, req: AccountRegister) -> AccountOut:
        existing = await self.repository.get_by_username(req.username, load_character=False)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{req.username}' is already registered."
            )
        
        salt = self.generate_salt()
        pwd_hash = self.hash_password(req.password, salt)
        try:
            account = await self.repository.create(req.username, pwd_hash, salt)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{req.username}' is already registered."
            )
        return AccountOut(
            id=account.id,
            username=account.username,
            email=account.email,
            role=account.role,
            is_banned=account.is_banned,
            created_at=account.created_at,
            last_login=account.last_login,
            has_character=False
        )

    async def register_guest(self, device_id: Optional[str] = None) -> Tuple[AccountOut, TokenResponse]:
        clean_device_id = device_id.strip() if device_id else None

        # 1. Returning guest check
        if clean_device_id:
            existing = await self.repository.get_by_device_id(clean_device_id, load_character=True)
            if existing:
                if existing.is_banned:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Guest account is banned. Reason: {existing.ban_reason or 'No reason provided.'}"
                    )
                await self.repository.update_last_login(existing.id)
                token = self.create_token(existing.id, existing.username, existing.role)
                account_out = AccountOut(
                    id=existing.id,
                    username=existing.username,
                    email=existing.email,
                    role=existing.role,
                    is_banned=existing.is_banned,
                    created_at=existing.created_at,
                    last_login=datetime.utcnow(),
                    has_character=existing.character is not None
                )
                token_out = TokenResponse(
                    access_token=token,
                    account_id=existing.id,
                    username=existing.username
                )
                return account_out, token_out

        # 2. Brand new guest account
        random_suffix = secrets.token_hex(4)
        guest_username = f"guest_{random_suffix}"
        guest_password = secrets.token_urlsafe(16)
        salt = self.generate_salt()
        pwd_hash = self.hash_password(guest_password, salt)

        try:
            account = await self.repository.create(
                guest_username,
                pwd_hash,
                salt,
                device_id=clean_device_id
            )
        except IntegrityError:
            # Concurrent registration with identical device_id
            if clean_device_id:
                existing = await self.repository.get_by_device_id(clean_device_id, load_character=True)
                if existing:
                    if existing.is_banned:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is banned.")
                    await self.repository.update_last_login(existing.id)
                    token = self.create_token(existing.id, existing.username, existing.role)
                    return (
                        AccountOut(
                            id=existing.id,
                            username=existing.username,
                            email=existing.email,
                            role=existing.role,
                            is_banned=existing.is_banned,
                            created_at=existing.created_at,
                            last_login=datetime.utcnow(),
                            has_character=existing.character is not None
                        ),
                        TokenResponse(
                            access_token=token,
                            account_id=existing.id,
                            username=existing.username
                        )
                    )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Guest registration conflict. Please retry."
            )

        await self.repository.update_last_login(account.id)
        token = self.create_token(account.id, account.username, account.role)
        account_out = AccountOut(
            id=account.id,
            username=account.username,
            email=account.email,
            role=account.role,
            is_banned=account.is_banned,
            created_at=account.created_at,
            last_login=datetime.utcnow(),
            has_character=False
        )
        token_out = TokenResponse(
            access_token=token,
            account_id=account.id,
            username=account.username
        )
        return account_out, token_out

    async def authenticate(self, req: AccountLogin) -> TokenResponse:
        account = await self.repository.get_by_username(req.username, load_character=False)
        if not account or not self.verify_password(req.password, account.salt, account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password."
            )
            
        if account.is_banned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is banned. Reason: {account.ban_reason or 'No reason provided.'}"
            )
            
        await self.repository.update_last_login(account.id)
        token = self.create_token(account.id, account.username, account.role)
        return TokenResponse(
            access_token=token,
            account_id=account.id,
            username=account.username
        )

    async def get_account_profile(self, account_id: int) -> AccountOut:
        account = await self.repository.get_by_id(account_id, load_character=True)
        if not account:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
        return AccountOut(
            id=account.id,
            username=account.username,
            email=account.email,
            role=account.role,
            is_banned=account.is_banned,
            created_at=account.created_at,
            last_login=account.last_login,
            has_character=account.character is not None
        )

    # -------------------------------------------------------------
    # Email OTP Workflows (Phase P02)
    # -------------------------------------------------------------

    async def request_otp(self, req: OTPRequest) -> OTPResponse:
        """
        Request a 6-digit OTP verification code for registration or login.
        Implements cooldown protection and user enumeration mitigation.
        """
        email = req.email.strip().lower()
        masked = mask_email(email)

        # 1. Cooldown enforcement per email and purpose
        latest_otp = await self.repository.get_latest_otp(email, req.purpose)
        if latest_otp:
            elapsed = (datetime.utcnow() - latest_otp.created_at).total_seconds()
            if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                wait_time = max(1, int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {wait_time}s before requesting a new verification code.",
                    headers={"Retry-After": str(wait_time)}
                )

        # 2. Account existence checks & enumeration mitigation
        existing_account = await self.repository.get_by_email(email, load_character=False)

        if req.purpose == "login":
            if not existing_account:
                # User enumeration defense: return identical response without generating OTP
                logger.info(f"Login OTP requested for non-existent email {masked} (enumeration defense)")
                return OTPResponse(
                    status="ok",
                    message="If this email is registered, a verification code has been sent.",
                    cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
                    masked_email=masked
                )
            if existing_account.is_banned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account is banned. Reason: {existing_account.ban_reason or 'No reason provided.'}"
                )

        elif req.purpose == "registration":
            if existing_account:
                # Account already exists: return generic message without issuing registration code
                logger.info(f"Registration OTP requested for existing email {masked} (enumeration defense)")
                return OTPResponse(
                    status="ok",
                    message="If this email is valid, a verification code has been sent.",
                    cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
                    masked_email=masked
                )

        # 3. Invalidate previous active OTPs for this email and purpose
        await self.repository.invalidate_otps_for_email(email, req.purpose)

        # 4. Generate cryptographically random 6-digit OTP
        code = self.generate_otp_code()
        salt = secrets.token_hex(16)
        otp_hash = self.hash_otp(code, salt)
        expires_at = datetime.utcnow() + timedelta(seconds=settings.OTP_EXPIRE_SECONDS)

        # 5. Persist salted OTP record
        await self.repository.create_otp(
            email=email,
            otp_hash=otp_hash,
            salt=salt,
            purpose=req.purpose,
            expires_at=expires_at,
            attempts_left=settings.OTP_MAX_ATTEMPTS
        )

        # 6. Dispatch via configured email provider
        provider = get_email_provider()
        await provider.send_otp(email, code, req.purpose)

        logger.info(f"Issued {req.purpose} OTP for {masked} (expires in {settings.OTP_EXPIRE_SECONDS}s)")

        return OTPResponse(
            status="ok",
            message="If this email is valid, a verification code has been sent.",
            cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
            masked_email=masked
        )

    async def verify_otp(self, req: OTPVerifyRequest) -> TokenResponse:
        """
        Verify a 6-digit OTP code and authenticate or create the player account.
        """
        email = req.email.strip().lower()
        masked = mask_email(email)

        # 1. Fetch active OTP record
        otp = await self.repository.get_active_otp(email, req.purpose)
        if not otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or previously used verification code."
            )

        # 2. Timing-safe verification using server-side HMAC-SHA256
        if not self.verify_otp_hash(req.code, otp.salt, otp.otp_hash):
            # Check if this was an outstanding challenge issued under legacy un-keyed salted SHA-256
            legacy_hash = hashlib.sha256(f"{otp.salt}:{req.code}".encode("utf-8")).hexdigest()
            if hmac.compare_digest(legacy_hash, otp.otp_hash):
                # Safely invalidate the incompatible legacy record
                await self.repository.mark_otp_used(otp.id)
                logger.warning(f"Invalidated legacy un-keyed OTP challenge for {masked}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code format has been upgraded for security. Please request a new verification code."
                )

            remaining = await self.repository.decrement_otp_attempts(otp.id)
            if remaining <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Verification code has been invalidated due to too many failed attempts."
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification code. {remaining} attempt(s) remaining."
            )

        # 3. Successful verification -> mark OTP as consumed
        await self.repository.mark_otp_used(otp.id)

        # 4. Handle Registration vs Login
        if req.purpose == "registration":
            existing = await self.repository.get_by_email(email, load_character=False)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this email already exists. Please log in."
                )

            # Determine unique username
            if req.username:
                clean_username = req.username.strip()
                taken = await self.repository.get_by_username(clean_username, load_character=False)
                if taken:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Username '{clean_username}' is already taken."
                    )
                chosen_username = clean_username
            else:
                # Generate unique username from email local-part
                local_raw = email.split("@")[0]
                sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", local_raw)[:20]
                if len(sanitized) < 3:
                    sanitized = f"player_{secrets.token_hex(3)}"
                
                # Check uniqueness
                chosen_username = sanitized
                existing_user = await self.repository.get_by_username(chosen_username, load_character=False)
                if existing_user:
                    chosen_username = f"{sanitized}_{secrets.token_hex(2)}"

            # Create passwordless account with sentinel hash
            salt = self.generate_salt()
            password_hash = f"*OTP_ONLY_{secrets.token_hex(16)}*"
            try:
                account = await self.repository.create(
                    username=chosen_username,
                    password_hash=password_hash,
                    salt=salt,
                    role="player",
                    email=email
                )
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Account registration conflict. Please retry."
                )

            await self.repository.update_last_login(account.id)
            token = self.create_token(account.id, account.username, account.role)
            logger.info(f"Registered new passwordless account id={account.id} ({account.username}) via OTP")
            return TokenResponse(
                access_token=token,
                account_id=account.id,
                username=account.username
            )

        elif req.purpose == "login":
            account = await self.repository.get_by_email(email, load_character=False)
            if not account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No account associated with this email address."
                )
            if account.is_banned:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Account is banned. Reason: {account.ban_reason or 'No reason provided.'}"
                )

            await self.repository.update_last_login(account.id)
            token = self.create_token(account.id, account.username, account.role)
            logger.info(f"Authenticated account id={account.id} ({account.username}) via OTP")
            return TokenResponse(
                access_token=token,
                account_id=account.id,
                username=account.username
            )

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported OTP purpose.")

# Dependency injection helpers
async def get_account_service(session: AsyncSession = Depends(get_db)) -> AccountService:
    repo = AccountRepository(session)
    return AccountService(repo)

async def get_current_account(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    service: AccountService = Depends(get_account_service)
) -> Account:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Bearer authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    payload = service.verify_token(auth.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    account_id = payload.get("sub")
    account = await service.repository.get_by_id(account_id, load_character=True)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")
    if account.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is banned.")
    return account

async def get_current_admin(
    account: Account = Depends(get_current_account)
) -> Account:
    if account.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required."
        )
    return account
