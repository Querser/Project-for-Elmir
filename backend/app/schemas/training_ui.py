from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TrainingReadUI(BaseModel):
    """
    DTO под UI.
    extra='allow' — чтобы не ломаться, если у Training есть дополнительные поля.
    """
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: int = Field(..., description="Training id")

    # Бэк реально может отдавать оба поля (у тебя в ответах есть starts_at и start_at)
    starts_at: Optional[datetime] = None
    start_at: Optional[datetime] = None

    ends_at: Optional[datetime] = None
    title: Optional[str] = None
    location: Optional[str] = None
    price: Optional[float] = None

    capacity_main: Optional[int] = None
    capacity_reserve: Optional[int] = None

    # UI-поля (бэк уже отдаёт их)
    free_places: int = 0
    occupied_main: int = 0
    occupied_reserve: int = 0
    can_enroll: bool = False

    # НЕ зажимаем Literal — иначе легко поймать падение при новых статусах
    user_enrollment_status: str = "none"

    # Бэк отдаёт массив: "price_tiers": []
    price_tiers: list[dict[str, Any]] = Field(default_factory=list)


class TrainingsPageUI(BaseModel):
    model_config = ConfigDict(extra="allow")

    items: list[TrainingReadUI]
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None
