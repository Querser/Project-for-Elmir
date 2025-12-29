# backend/app/schemas/notification.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AdminBroadcastNotificationIn(BaseModel):
    type: str = Field(..., examples=["INFO", "SYSTEM", "TRAINING"])
    text: str = Field(..., min_length=1)
    title: Optional[str] = None
    url: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


class AdminTrainingNotificationIn(BaseModel):
    type: str = Field(default="TRAINING")
    text: str = Field(..., min_length=1)
    title: Optional[str] = None
    url: Optional[str] = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    type: str
    title: str
    body: str
    text: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    url: Optional[str] = None
    is_read: bool
    created_at: datetime


class NotificationListOut(BaseModel):
    items: List[NotificationOut]
    total: int
    limit: int
    offset: int
