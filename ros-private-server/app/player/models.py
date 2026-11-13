from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import Integer, BigInteger, String, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (
        CheckConstraint("diamonds >= 0", name="chk_character_diamonds_non_negative"),
    )
    
    gid: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), unique=True, nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    char_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # 0: Male, 1: Female
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    exp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gold: Mapped[int] = mapped_column(BigInteger, default=1000, nullable=False)
    diamonds: Mapped[int] = mapped_column(BigInteger, default=100, nullable=False)
    
    # JSON stores for modular appearance & custom layout configurations
    appearances: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "equipped_clothing": [10001, 10002],
            "unlocked_items": [10001, 10002],
            "active_weapon_skin": 0
        },
        nullable=False
    )
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "control_mode": 1,
            "fov": 75,
            "gyroscope": False,
            "sensitivity": {"general": 100, "aim": 80, "scope2x": 60}
        },
        nullable=False
    )
    stats: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        default=lambda: {
            "total_matches": 0,
            "total_wins": 0,
            "total_kills": 0,
            "damage_dealt": 0.0
        },
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="character")
    diamond_transactions: Mapped[List["DiamondTransaction"]] = relationship(
        "DiamondTransaction",
        back_populates="character",
        cascade="all, delete-orphan"
    )
    inventory_items: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="character",
        cascade="all, delete-orphan"
    )
