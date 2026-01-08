from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

try:
    from pydantic import ConfigDict  # pydantic v2
    _V2 = True
except Exception:
    ConfigDict = None  # type: ignore
    _V2 = False


class EnrollmentCreateRequest(BaseModel):
    training_id: int
    is_paid: bool = False
    price_tier_id: Optional[int] = None


class EnrollmentRead(BaseModel):
    id: int
    user_id: int
    training_id: int
    is_paid: bool
    status: str

    price_tier_id: Optional[int] = None
    created_at: Optional[datetime] = None

    if _V2:
        model_config = ConfigDict(from_attributes=True)  # type: ignore
    else:
        class Config:
            orm_mode = True
