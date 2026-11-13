from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, BigInteger, String, Boolean, DateTime, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("max_stack >= 1", name="chk_item_max_stack_positive"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True
    )
    item_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        default=""
    )
    item_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True
    )
    icon: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    stackable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    max_stack: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    inventory_items: Mapped[List["InventoryItem"]] = relationship(
        "InventoryItem",
        back_populates="item",
        cascade="all, delete-orphan"
    )

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("character_gid", "item_id", name="uq_character_inventory_item"),
        CheckConstraint("quantity > 0", name="chk_inventory_item_quantity_positive"),
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
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("items.id"),
        nullable=False,
        index=True
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    character: Mapped["Character"] = relationship("Character", back_populates="inventory_items")
    item: Mapped["Item"] = relationship("Item", back_populates="inventory_items", lazy="joined")

class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_inv_tx_quantity_positive"),
        CheckConstraint("quantity_before >= 0", name="chk_inv_tx_quantity_before_non_negative"),
        CheckConstraint("quantity_after >= 0", name="chk_inv_tx_quantity_after_non_negative"),
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
    item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("items.id"),
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
    )  # 'GRANT' or 'REMOVE'
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    quantity_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    quantity_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    # Relationships
    character: Mapped["Character"] = relationship("Character")
    item: Mapped["Item"] = relationship("Item", lazy="joined")
    admin_account: Mapped["Account"] = relationship("Account")
