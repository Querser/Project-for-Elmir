# backend/app/schemas/ban.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.ban import BanType


class BanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    ban_type: BanType
    debt_id: int | None = None
    is_active: bool
    reason: str | None = None
    message: str | None = None
    created_at: datetime
    created_by_user_id: int | None = None
    revoked_at: datetime | None = None
    revoked_by_user_id: int | None = None
    revoke_reason: str | None = None


class ManualBanCreateRequest(BaseModel):
    reason: str | None = None
    message: str | None = None


class BanRevokeRequest(BaseModel):
    revoke_reason: str | None = None
