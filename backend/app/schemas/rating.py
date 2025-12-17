# app/schemas/rating.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RatingUserDTO(BaseModel):
    """
    Запись в таблице рейтинга.
    """
    position: int
    user_id: int
    telegram_id: int

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    rating: int
    cups: int
    level_id: Optional[int] = None

    class Config:
        from_attributes = False  # мы заполняем DTO вручную


class RatingLeaderboardResponse(BaseModel):
    items: list[RatingUserDTO]
    total: int
    limit: int
    offset: int


class RatingUserInfoDTO(BaseModel):
    """
    Информация о рейтинге конкретного игрока.
    """
    user_id: int
    position: int
    total: int

    rating: int
    cups: int
    level_id: Optional[int] = None

    class Config:
        from_attributes = False
