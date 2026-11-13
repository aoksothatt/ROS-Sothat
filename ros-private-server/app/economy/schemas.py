from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_DIAMOND_TRANSACTION_AMOUNT = 100_000_000

class DiamondGrantRequest(BaseModel):
    amount: int = Field(
        ...,
        gt=0,
        le=MAX_DIAMOND_TRANSACTION_AMOUNT,
        description="Number of diamonds to grant (must be a positive integer <= 100,000,000)"
    )
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique caller-supplied token to ensure exactly-once execution"
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Administrative audit reason for the grant"
    )

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Idempotency key must not be empty or whitespace-only.")
        if len(clean) > 64:
            raise ValueError("Idempotency key exceeds maximum length of 64 characters.")
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Reason must not be empty or whitespace-only.")
        if len(clean) > 255:
            raise ValueError("Reason exceeds maximum length of 255 characters.")
        return clean

class DiamondDeductRequest(BaseModel):
    amount: int = Field(
        ...,
        gt=0,
        le=MAX_DIAMOND_TRANSACTION_AMOUNT,
        description="Number of diamonds to deduct (must be a positive integer <= 100,000,000)"
    )
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique caller-supplied token to ensure exactly-once execution"
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Administrative audit reason for the deduction"
    )

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Idempotency key must not be empty or whitespace-only.")
        if len(clean) > 64:
            raise ValueError("Idempotency key exceeds maximum length of 64 characters.")
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Reason must not be empty or whitespace-only.")
        if len(clean) > 255:
            raise ValueError("Reason exceeds maximum length of 255 characters.")
        return clean

class DiamondTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_gid: int
    admin_account_id: int
    operation_type: Literal["GRANT", "DEDUCT"]
    amount: int
    balance_before: int
    balance_after: int
    idempotency_key: str
    reason: str
    created_at: datetime

class DiamondHistoryResponse(BaseModel):
    character_gid: int
    current_balance: int
    total_transactions: int
    transactions: List[DiamondTransactionOut]
