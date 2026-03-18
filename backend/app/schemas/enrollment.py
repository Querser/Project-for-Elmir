from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel

try:
    from pydantic import ConfigDict, field_validator  # pydantic v2
    _V2 = True
except Exception:
    ConfigDict = None  # type: ignore
    field_validator = None  # type: ignore
    _V2 = False

try:
    from pydantic import validator  # pydantic v1
except Exception:
    validator = None  # type: ignore


class EnrollmentCreateRequest(BaseModel):
    training_id: int
    is_paid: bool = False
    price_tier_id: Optional[int] = None
    position_key: Optional[str] = None


class EnrollmentRead(BaseModel):
    id: int
    user_id: int
    training_id: int
    is_paid: bool
    status: str
    position_key: Optional[str] = None

    price_tier_id: Optional[int] = None
    created_at: Optional[datetime] = None

    if _V2:
        model_config = ConfigDict(from_attributes=True)  # type: ignore

        @field_validator("status", mode="before")  # type: ignore
        def _status_to_value(cls, v: Any):
            return getattr(v, "value", v)
    else:
        class Config:
            orm_mode = True

        @validator("status", pre=True)  # type: ignore
        def _status_to_value(cls, v: Any):
            return getattr(v, "value", v)
