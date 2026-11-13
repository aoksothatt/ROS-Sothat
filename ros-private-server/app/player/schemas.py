import json
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

def _validate_payload_size(data: Any, max_bytes: int = 16384) -> None:
    try:
        serialized = json.dumps(data)
        if len(serialized.encode("utf-8")) > max_bytes:
            raise ValueError(f"Payload size exceeds maximum allowed limit of {max_bytes} bytes.")
    except (TypeError, OverflowError) as e:
        raise ValueError(f"Malformed or non-serializable payload: {e}")

class CharacterCreate(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=24, description="In-game nickname")
    char_type: int = Field(0, ge=0, le=1, description="0 for Male, 1 for Female")

class CharacterOut(BaseModel):
    gid: int
    account_id: int
    nickname: str
    char_type: int
    level: int
    exp: int
    gold: int
    diamonds: int
    appearances: Dict[str, Any]
    settings: Dict[str, Any]
    stats: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CharacterUpdateSettings(BaseModel):
    settings: Dict[str, Any] = Field(..., description="Key-value user settings dictionary")

    @field_validator("settings")
    @classmethod
    def validate_settings(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("Settings must be a key-value dictionary.")
        _validate_payload_size(v, max_bytes=16384)
        if len(v) > 30:
            raise ValueError("Settings dictionary exceeds maximum limit of 30 keys.")
        for k, val in v.items():
            if not isinstance(k, str) or not (1 <= len(k) <= 32) or not k.isidentifier():
                raise ValueError(f"Invalid settings key name '{k}'. Must be valid identifier of 1-32 chars.")
            if isinstance(val, dict):
                if len(val) > 15:
                    raise ValueError(f"Nested dictionary for '{k}' exceeds maximum 15 entries.")
                for sub_k, sub_val in val.items():
                    if not isinstance(sub_k, str) or not (1 <= len(sub_k) <= 32):
                        raise ValueError(f"Invalid subkey '{sub_k}' in '{k}'.")
                    if not isinstance(sub_val, (int, float, bool, str)):
                        raise ValueError(f"Invalid value type in '{k}.{sub_k}'. Must be primitive.")
                    if isinstance(sub_val, str) and len(sub_val) > 128:
                        raise ValueError(f"String value in '{k}.{sub_k}' exceeds maximum 128 characters.")
            elif isinstance(val, (int, float, bool)):
                continue
            elif isinstance(val, str):
                if len(val) > 128:
                    raise ValueError(f"String value for '{k}' exceeds maximum 128 characters.")
            else:
                raise ValueError(f"Unsupported value type for settings key '{k}'.")
        return v

class CharacterUpdateAppearances(BaseModel):
    appearances: Dict[str, Any] = Field(..., description="Key-value appearance & cosmetic dictionary")

    @field_validator("appearances")
    @classmethod
    def validate_appearances(cls, v: Any) -> Dict[str, Any]:
        if not isinstance(v, dict):
            raise ValueError("Appearances must be a key-value dictionary.")
        _validate_payload_size(v, max_bytes=16384)
        if len(v) > 20:
            raise ValueError("Appearances dictionary exceeds maximum limit of 20 keys.")
        for k, val in v.items():
            if not isinstance(k, str) or not (1 <= len(k) <= 32) or not k.isidentifier():
                raise ValueError(f"Invalid appearances key name '{k}'. Must be valid identifier of 1-32 chars.")
            if isinstance(val, list):
                if len(val) > 50:
                    raise ValueError(f"List for '{k}' exceeds maximum 50 elements.")
                for item in val:
                    if not isinstance(item, int) or item < 0 or item > 9999999:
                        raise ValueError(f"List element in '{k}' must be non-negative integer <= 9999999.")
            elif isinstance(val, int):
                if val < 0 or val > 9999999:
                    raise ValueError(f"Integer value for '{k}' must be non-negative and <= 9999999.")
            elif isinstance(val, str):
                if len(val) > 64:
                    raise ValueError(f"String value for '{k}' exceeds maximum 64 characters.")
            elif isinstance(val, bool):
                continue
            else:
                raise ValueError(f"Unsupported value type for appearances key '{k}'.")
        return v

class CharacterPublicProfile(BaseModel):
    gid: int
    nickname: str
    char_type: int
    level: int
    stats: Dict[str, Any]
