# app/schemas/ban.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ban import BanType


class BanResponse(BaseModel):
    id: int
    user_id: int
    reason: str
    type: BanType
    is_active: bool
    is_auto: bool
    created_at: datetime
    revoked_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class BanListResponse(BaseModel):
    items: list[BanResponse]
    total: int
    limit: int
    offset: int


class BanCreateRequest(BaseModel):
    # Тело запроса для ручного бана
    reason: str
