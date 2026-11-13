from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, and_, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.account.models import Account, EmailOTP

class AccountRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(
        self,
        username: str,
        password_hash: str,
        salt: str,
        device_id: Optional[str] = None,
        role: str = "player",
        email: Optional[str] = None,
    ) -> Account:
        normalized_email = email.strip().lower() if email else None
        account = Account(
            username=username,
            email=normalized_email,
            device_id=device_id,
            password_hash=password_hash,
            salt=salt,
            role=role,
            created_at=datetime.utcnow()
        )
        self.session.add(account)
        try:
            await self.session.commit()
            await self.session.refresh(account)
            return account
        except IntegrityError:
            await self.session.rollback()
            raise

    async def get_by_device_id(self, device_id: str, load_character: bool = True) -> Optional[Account]:
        stmt = select(Account).where(Account.device_id == device_id)
        if load_character:
            stmt = stmt.options(selectinload(Account.character))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, username: str, load_character: bool = True) -> Optional[Account]:
        stmt = select(Account).where(Account.username == username)
        if load_character:
            stmt = stmt.options(selectinload(Account.character))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_email(self, email: str, load_character: bool = True) -> Optional[Account]:
        stmt = select(Account).where(Account.email == email.strip().lower())
        if load_character:
            stmt = stmt.options(selectinload(Account.character))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, account_id: int, load_character: bool = True) -> Optional[Account]:
        stmt = select(Account).where(Account.id == account_id)
        if load_character:
            stmt = stmt.options(selectinload(Account.character))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_last_login(self, account_id: int, login_time: Optional[datetime] = None) -> None:
        if login_time is None:
            login_time = datetime.utcnow()
        stmt = update(Account).where(Account.id == account_id).values(last_login=login_time)
        await self.session.execute(stmt)
        await self.session.commit()

    async def update_role(self, account_id: int, new_role: str) -> Optional[Account]:
        stmt = update(Account).where(Account.id == account_id).values(role=new_role)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(account_id, load_character=True)

    async def set_banned(self, account_id: int, is_banned: bool, reason: Optional[str] = None) -> Optional[Account]:
        stmt = update(Account).where(Account.id == account_id).values(is_banned=is_banned, ban_reason=reason)
        await self.session.execute(stmt)
        await self.session.commit()
        return await self.get_by_id(account_id, load_character=True)

    async def list_accounts(self, limit: int = 50, offset: int = 0) -> List[Account]:
        stmt = select(Account).order_by(Account.id).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------
    # OTP Repository Methods (Phase P02)
    # -------------------------------------------------------------

    async def create_otp(
        self,
        email: str,
        otp_hash: str,
        salt: str,
        purpose: str,
        expires_at: datetime,
        attempts_left: int = 5,
    ) -> EmailOTP:
        otp_entry = EmailOTP(
            email=email.strip().lower(),
            otp_hash=otp_hash,
            salt=salt,
            purpose=purpose,
            expires_at=expires_at,
            attempts_left=attempts_left,
            is_used=False,
            created_at=datetime.utcnow()
        )
        self.session.add(otp_entry)
        await self.session.commit()
        await self.session.refresh(otp_entry)
        return otp_entry

    async def get_latest_otp(self, email: str, purpose: Optional[str] = None) -> Optional[EmailOTP]:
        """Fetch the most recent OTP record for cooldown checks."""
        stmt = select(EmailOTP).where(EmailOTP.email == email.strip().lower())
        if purpose:
            stmt = stmt.where(EmailOTP.purpose == purpose)
        stmt = stmt.order_by(desc(EmailOTP.created_at)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_active_otp(self, email: str, purpose: str) -> Optional[EmailOTP]:
        """Fetch currently valid, unexpired, and unused OTP for verification."""
        now = datetime.utcnow()
        stmt = (
            select(EmailOTP)
            .where(
                and_(
                    EmailOTP.email == email.strip().lower(),
                    EmailOTP.purpose == purpose,
                    EmailOTP.is_used == False,
                    EmailOTP.expires_at > now,
                    EmailOTP.attempts_left > 0
                )
            )
            .order_by(desc(EmailOTP.created_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def invalidate_otps_for_email(self, email: str, purpose: Optional[str] = None) -> None:
        """Invalidate existing unused OTPs when a new OTP is issued."""
        stmt = update(EmailOTP).where(
            and_(
                EmailOTP.email == email.strip().lower(),
                EmailOTP.is_used == False
            )
        )
        if purpose:
            stmt = stmt.where(EmailOTP.purpose == purpose)
        stmt = stmt.values(is_used=True)
        await self.session.execute(stmt)
        await self.session.commit()

    async def decrement_otp_attempts(self, otp_id: int) -> int:
        """Decrement attempts_left by 1; if it hits 0, invalidate."""
        stmt = select(EmailOTP).where(EmailOTP.id == otp_id)
        result = await self.session.execute(stmt)
        otp = result.scalars().first()
        if not otp:
            return 0

        otp.attempts_left = max(0, otp.attempts_left - 1)
        if otp.attempts_left == 0:
            otp.is_used = True
        await self.session.commit()
        return otp.attempts_left

    async def mark_otp_used(self, otp_id: int) -> None:
        """Mark OTP as consumed upon successful verification."""
        stmt = update(EmailOTP).where(EmailOTP.id == otp_id).values(is_used=True)
        await self.session.execute(stmt)
        await self.session.commit()
