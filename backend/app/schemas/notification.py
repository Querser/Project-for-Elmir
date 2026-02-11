from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AdminBroadcastNotificationIn(BaseModel):
    type: str = Field(..., examples=["INFO", "SYSTEM", "TRAINING"])
    text: str = Field(..., min_length=1)
    title: str = Field(default="\u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435", min_length=1)
    url: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


class AdminTrainingNotificationIn(BaseModel):
    type: str = Field(default="TRAINING")
    text: str = Field(..., min_length=1)
    title: str = Field(default="\u0423\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u0435", min_length=1)
    url: Optional[str] = None


class AdminUserTargetedNotificationIn(BaseModel):
    user_ids: List[int] = Field(..., min_items=1)
    type: str = Field(default="SYSTEM")
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    url: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None


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


class AdminCreateNotificationsForTrainingIn(BaseModel):
    training_id: int
    type: str = Field(default="TRAINING")
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    url: Optional[str] = None
