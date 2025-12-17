# app/schemas/enrollment.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enrollment import EnrollmentStatus


class EnrollmentCreateRequest(BaseModel):
    """
    Тело запроса на запись на тренировку.
    """
    training_id: int = Field(..., gt=0)


class EnrollmentUserShort(BaseModel):
    """
    Краткая информация о пользователе в составе тренировки.
    """
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


class EnrollmentResponse(BaseModel):
    """
    Ответ API по одной записи на тренировку.
    """
    id: int
    training_id: int
    user_id: int

    is_reserve: bool
    status: EnrollmentStatus
    is_paid: bool
    created_at: datetime

    # Для состава тренировки можно отдавать краткие данные пользователя
    user: Optional[EnrollmentUserShort] = None

    class Config:
        from_attributes = True
