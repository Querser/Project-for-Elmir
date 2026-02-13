# app/schemas/user.py
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict, AliasChoices


class UserProfile(BaseModel):
    """
    Полный профиль пользователя, который отдаём наружу.
    """
    id: int
    telegram_id: int

    username: Optional[str] = None
    avatar_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

    level_id: Optional[int] = None

    rating: int
    cups: int

    gender: Optional[str] = None
    birth_date: Optional[date] = None
    is_telegram_public: bool
    has_active_ban: bool = False
    active_ban_reason: Optional[str] = None
    active_ban_until: Optional[datetime] = None

    payer_id: Optional[str] = None
    card_last4: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserPublicProfile(BaseModel):
    """
    Публичный профиль пользователя (для просмотра из рейтинга).
    Telegram username отдаём только если is_telegram_public=True (или это self).
    """
    id: int
    avatar_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    level_id: Optional[int] = None
    level_name: Optional[str] = None

    rating: int
    cups: int

    username: Optional[str] = None
    is_telegram_public: bool

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """
    Тело PATCH/PUT /api/v1/profile/me
    Все поля опциональны — передаём только то, что хотим изменить.
    """

    first_name: Optional[str] = Field(default=None, max_length=255)
    last_name: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)

    gender: Optional[str] = None  # 'male', 'female', 'other'
    birth_date: Optional[date] = None
    level_id: Optional[int] = None

    # ✅ ВАЖНО: принимаем show_telegram как алиас (старое имя из фронта)
    is_telegram_public: Optional[bool] = Field(
        default=None,
        validation_alias=AliasChoices(
            "is_telegram_public",
            "show_telegram",
            "telegram_visible",
            "telegram_public",
        ),
    )

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"male", "female", "other"}
        if v not in allowed:
            raise ValueError(f"gender must be one of {', '.join(allowed)}")
        return v

    model_config = ConfigDict(extra="forbid")
