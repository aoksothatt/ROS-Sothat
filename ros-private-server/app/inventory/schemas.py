import re
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

ITEM_CODE_REGEX = re.compile(r"^[A-Za-z0-9_]{2,64}$")

class ItemCreate(BaseModel):
    item_code: str = Field(
        ...,
        min_length=2,
        max_length=64,
        description="Unique programmatic identifier (alphanumeric and underscores)"
    )
    name: str = Field(..., min_length=1, max_length=128, description="Display name")
    description: str = Field("", max_length=512, description="Item description")
    item_type: str = Field(..., min_length=2, max_length=32, description="Type (e.g. WEAPON_SKIN, CLOTHING, CONSUMABLE)")
    icon: Optional[str] = Field(None, max_length=255, description="Asset or icon path")
    stackable: bool = Field(False, description="Whether items can stack in inventory")
    max_stack: int = Field(1, ge=1, le=9999, description="Maximum stack size")
    is_active: bool = Field(True, description="Whether item is active in catalog")

    @field_validator("item_code")
    @classmethod
    def validate_item_code(cls, v: str) -> str:
        clean = v.strip().upper()
        if not ITEM_CODE_REGEX.match(clean):
            raise ValueError("item_code must be 2-64 alphanumeric characters or underscores.")
        return clean

    @field_validator("name", "description")
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        clean = v.strip()
        return clean

    @field_validator("item_type")
    @classmethod
    def validate_item_type(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean:
            raise ValueError("item_type cannot be empty.")
        return clean

class ItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    icon: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    max_stack: Optional[int] = Field(None, ge=1, le=9999)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("name cannot be empty or whitespace-only.")
            return clean
        return v

class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_code: str
    name: str
    description: str
    item_type: str
    icon: Optional[str]
    stackable: bool
    max_stack: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class InventoryGrantRequest(BaseModel):
    item_id: int = Field(..., gt=0, description="Catalog item ID to grant")
    quantity: int = Field(..., gt=0, le=9999, description="Number of items to grant")
    idempotency_key: str = Field(..., min_length=1, max_length=64, description="Caller idempotency token")
    reason: str = Field(..., min_length=1, max_length=255, description="Audit justification")

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("idempotency_key must not be empty or whitespace-only.")
        if len(clean) > 64:
            raise ValueError("idempotency_key exceeds maximum length of 64 characters.")
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("reason must not be empty or whitespace-only.")
        if len(clean) > 255:
            raise ValueError("reason exceeds maximum length of 255 characters.")
        return clean

class InventoryRemoveRequest(BaseModel):
    item_id: int = Field(..., gt=0, description="Catalog item ID to remove")
    quantity: int = Field(..., gt=0, le=9999, description="Number of items to remove")
    idempotency_key: str = Field(..., min_length=1, max_length=64, description="Caller idempotency token")
    reason: str = Field(..., min_length=1, max_length=255, description="Audit justification")

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("idempotency_key must not be empty or whitespace-only.")
        if len(clean) > 64:
            raise ValueError("idempotency_key exceeds maximum length of 64 characters.")
        return clean

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("reason must not be empty or whitespace-only.")
        if len(clean) > 255:
            raise ValueError("reason exceeds maximum length of 255 characters.")
        return clean

class InventoryItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_gid: int
    item_id: int
    quantity: int
    created_at: datetime
    updated_at: datetime
    item: Optional[ItemOut] = None

class CharacterInventoryResponse(BaseModel):
    character_gid: int
    total_items: int
    items: List[InventoryItemOut]

class InventoryTransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    character_gid: int
    item_id: int
    admin_account_id: int
    operation_type: Literal["GRANT", "REMOVE"]
    quantity: int
    quantity_before: int
    quantity_after: int
    reason: str
    idempotency_key: str
    created_at: datetime

class InventoryHistoryResponse(BaseModel):
    character_gid: int
    total_transactions: int
    transactions: List[InventoryTransactionOut]
