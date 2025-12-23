from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.ban import BanType


class BanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: BanType
    reason: str
    active: bool
    created_at: datetime
    until: Optional[datetime] = None


class BanListResponse(BaseModel):
    items: List[BanResponse]
    total: int = 0
    limit: int = 50
    offset: int = 0


class BanCreateRequest(BaseModel):
    # user_id приходит в path (/bans/{user_id}/ban). Оставляем поле опциональным,
    # чтобы не ловить 422, если фронт/ручка его не присылает.
    user_id: Optional[int] = Field(default=None, ge=1)
    reason: str = Field(..., min_length=1, max_length=500)
    until: Optional[datetime] = None
