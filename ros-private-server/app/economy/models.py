from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, BigInteger, String, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class DiamondTransaction(Base):
    __tablename__ = "diamond_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_diamond_tx_amount_positive"),
        CheckConstraint("balance_before >= 0", name="chk_diamond_tx_balance_before_non_negative"),
        CheckConstraint("balance_after >= 0", name="chk_diamond_tx_balance_after_non_negative"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        index=True
    )
    character_gid: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("characters.gid"),
        nullable=False,
        index=True
    )
    admin_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id"),
        nullable=False,
        index=True
    )
    operation_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False
    ) # 'GRANT' or 'DEDUCT'
    amount: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    balance_before: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    balance_after: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )
    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    character: Mapped["Character"] = relationship("Character", back_populates="diamond_transactions")
    admin_account: Mapped["Account"] = relationship("Account")
