# backend/app/schemas/training.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TrainingBase(BaseModel):
    """
    Базовые поля тренировки – общие для создания и чтения.
    """

    title: str = Field(..., max_length=100, description="Название / тип тренировки")
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Краткое описание",
    )

    start_at: datetime = Field(..., description="Дата и время начала (ISO)")
    duration_minutes: int = Field(
        default=90,
        ge=1,
        le=600,
        description="Длительность тренировки в минутах",
    )

    min_level_name: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Минимальный уровень допуска (строка, например L3)",
    )
    max_level_name: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Максимальный уровень допуска (строка, например L6)",
    )

    price: float = Field(
        default=0,
        ge=0,
        description="Стоимость тренировки",
    )

    capacity_main: int = Field(
        default=12,
        ge=0,
        le=1000,
        description="Лимит мест в основе",
    )
    capacity_reserve: int = Field(
        default=4,
        ge=0,
        le=1000,
        description="Лимит мест в резерве",
    )

    coach_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Имя тренера",
    )

    image_url: Optional[str] = Field(
        default=None,
        max_length=255,
        description="URL фото площадки / тренировки",
    )
    video_url: Optional[str] = Field(
        default=None,
        max_length=255,
        description="URL видео (обзор, разбор и т.п.)",
    )

    location_id: Optional[int] = Field(
        default=None,
        description="ID Location (если есть)",
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("price must be >= 0")
        # округляем до двух знаков, чтобы не было странных хвостов
        return round(v, 2)


class TrainingCreate(TrainingBase):
    """
    Тело POST /api/v1/trainings (админ).
    Наследуем все поля, но start_at и title обязательны.
    """

    # title и start_at уже обязательны в TrainingBase, поэтому здесь ничего добавлять не нужно
    pass


class TrainingUpdate(BaseModel):
    """
    Тело PATCH /api/v1/trainings/{id} (админ).
    Все поля опциональны – меняем только то, что прислали.
    """

    title: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)

    start_at: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=600)

    min_level_name: Optional[str] = Field(default=None, max_length=50)
    max_level_name: Optional[str] = Field(default=None, max_length=50)

    price: Optional[float] = Field(default=None, ge=0)

    capacity_main: Optional[int] = Field(default=None, ge=0, le=1000)
    capacity_reserve: Optional[int] = Field(default=None, ge=0, le=1000)

    coach_name: Optional[str] = Field(default=None, max_length=100)

    image_url: Optional[str] = Field(default=None, max_length=255)
    video_url: Optional[str] = Field(default=None, max_length=255)

    location_id: Optional[int] = None

    is_cancelled: Optional[bool] = Field(
        default=None,
        description="Флаг отмены; обычно лучше использовать отдельный endpoint /cancel",
    )

    class Config:
        extra = "forbid"


class TrainingPublic(BaseModel):
    """
    То, что отдаём фронтендам (мини-апп, админка).
    """

    id: int

    title: str
    description: Optional[str]

    start_at: datetime
    duration_minutes: int

    min_level_name: Optional[str]
    max_level_name: Optional[str]

    price: float

    capacity_main: int
    capacity_reserve: int

    coach_name: Optional[str]
    image_url: Optional[str]
    video_url: Optional[str]

    location_id: Optional[int]

    is_cancelled: bool

    class Config:
        # важное – говорим pydantic, что можно валидировать ORM-объекты
        from_attributes = True
