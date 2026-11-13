from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, BigInteger, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    admin_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    action_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True
    )  # e.g., "DIAMOND_GRANT", "DIAMOND_DEDUCT", "INVENTORY_GRANT", "INVENTORY_REMOVE", "ACCOUNT_SUSPEND", "ACCOUNT_REACTIVATE", "ROLE_CHANGE"
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False
    )  # "account" or "character"
    target_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        nullable=False,
        index=True
    )
    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    details: Mapped[str] = mapped_column(
        Text,
        default="{}",
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    admin_account: Mapped["Account"] = relationship("Account")
