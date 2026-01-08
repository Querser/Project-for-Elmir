from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TrainingReadUI(BaseModel):
    """
    DTO под UI. extra='allow' чтобы не ломаться, если у Training есть дополнительные поля.
    """
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: int = Field(..., description="Training id")

    # базовые поля (оставляем optional, чтобы не ломать текущие данные)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    title: Optional[str] = None
    location: Optional[str] = None
    price: Optional[float] = None

    capacity_main: Optional[int] = None
    capacity_reserve: Optional[int] = None

    # UI-поля (важно: они должны быть в ответе)
    free_places: int = 0
    occupied_main: int = 0
    occupied_reserve: int = 0
    can_enroll: bool = False
    user_enrollment_status: Literal["none", "main", "reserve", "unknown"] = "unknown"


class TrainingsPageUI(BaseModel):
    model_config = ConfigDict(extra="allow")

    items: list[TrainingReadUI]
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None
