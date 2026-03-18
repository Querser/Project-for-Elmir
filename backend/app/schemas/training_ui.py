from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class TrainingReadUI(BaseModel):
    """
    DTO под UI.
    extra='allow' - чтобы не ломаться, если у Training есть дополнительные поля.
    """

    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: int = Field(..., description="Training id")

    starts_at: Optional[datetime] = None
    start_at: Optional[datetime] = None

    ends_at: Optional[datetime] = None
    title: Optional[str] = None
    location: Optional[str] = None
    location_id: Optional[int] = None
    location_name: Optional[str] = None
    price: Optional[float] = None

    capacity_main: Optional[int] = None
    capacity_reserve: Optional[int] = None
    training_type: Optional[str] = None
    amplua_positions: Optional[dict[str, int]] = None

    free_places: int = 0
    occupied_main: int = 0
    occupied_reserve: int = 0
    can_enroll: bool = False
    can_enroll_reserve: bool = False
    position_slots: list[dict[str, Any]] = Field(default_factory=list)
    available_positions: list[dict[str, Any]] = Field(default_factory=list)
    user_position_key: Optional[str] = None
    user_position_label: Optional[str] = None

    user_enrollment_status: str = "none"

    price_tiers: list[dict[str, Any]] = Field(default_factory=list)


class TrainingsPageUI(BaseModel):
    model_config = ConfigDict(extra="allow")

    items: list[TrainingReadUI]
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None
