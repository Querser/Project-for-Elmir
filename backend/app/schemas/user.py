# app/schemas/user.py
from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class UserProfile(BaseModel):
    """
    Полный профиль пользователя, который отдаём наружу.
    """
    id: int
    telegram_id: int  # telegram_id ведём как int

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

    level_id: Optional[int] = None

    rating: int
    cups: int

    gender: Optional[str] = None
    birth_date: Optional[date] = None
    is_telegram_public: bool

    payer_id: Optional[str] = None
    card_last4: Optional[str] = None

    # Pydantic v2: разрешаем валидировать объект из атрибутов ORM-модели User
    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """
    Тело PATCH /api/v1/profile/me
    Все поля опциональны — передаём только то, что хотим изменить.
    """

    first_name: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)

    gender: Optional[str] = None  # 'male', 'female', 'other'
    birth_date: Optional[date] = None
    level_id: Optional[int] = None
    is_telegram_public: Optional[bool] = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"male", "female", "other"}
        if v not in allowed:
            raise ValueError(f"gender must be one of {', '.join(allowed)}")
        return v

    # Запрещаем лишние поля в JSON
    model_config = ConfigDict(extra="forbid")
