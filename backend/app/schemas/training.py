# backend/app/schemas/training.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

CANONICAL_LEVEL_NAMES = ('Новичок', 'Средний-', 'Средний', 'Средний+')
LEVEL_ORDER = {name: idx for idx, name in enumerate(CANONICAL_LEVEL_NAMES)}


def _normalize_level_name(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip().replace('−', '-')
    if not raw:
        return None
    return raw


def _ensure_level_range(min_level_name: str | None, max_level_name: str | None) -> None:
    if min_level_name is None or max_level_name is None:
        return
    if LEVEL_ORDER[min_level_name] > LEVEL_ORDER[max_level_name]:
        raise ValueError('min_level_name must not be higher than max_level_name')


def _normalize_media_url(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_media_url_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        source = list(value)
    else:
        source = [value]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in source:
        url = _normalize_media_url(item)
        if not url or url in seen:
            continue
        normalized.append(url)
        seen.add(url)
    return normalized


class TrainingBase(BaseModel):
    """
    Базовые поля тренировки - общие для создания и чтения.
    """

    title: str = Field(..., max_length=100, description='Название / тип тренировки')
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description='Краткое описание',
    )

    start_at: datetime = Field(..., description='Дата и время начала (ISO)')
    duration_minutes: int = Field(
        default=90,
        ge=1,
        le=600,
        description='Длительность тренировки в минутах',
    )

    min_level_name: Optional[str] = Field(
        default=None,
        max_length=50,
        description='Минимальный уровень допуска (например L3)',
    )
    max_level_name: Optional[str] = Field(
        default=None,
        max_length=50,
        description='Максимальный уровень допуска (например L6)',
    )

    price: float = Field(
        default=0,
        ge=0,
        description='Стоимость тренировки',
    )

    capacity_main: int = Field(
        default=12,
        ge=0,
        le=1000,
        description='Лимит мест в основе',
    )
    capacity_reserve: int = Field(
        default=4,
        ge=0,
        le=1000,
        description='Лимит мест в резерве',
    )

    training_type: Optional[str] = Field(
        default=None,
        max_length=32,
        description='Тип тренировки',
    )
    amplua_positions: Optional[dict[str, int]] = Field(
        default=None,
        description='Позиции для тренировок типа амплуа',
    )

    coach_name: Optional[str] = Field(
        default=None,
        max_length=100,
        description='Имя тренера',
    )

    image_url: Optional[str] = Field(
        default=None,
        max_length=255,
        description='URL фото площадки / тренировки',
    )
    image_urls: Optional[list[str]] = Field(
        default=None,
        description='Список URL фото (первый элемент используется как основное фото)',
    )
    video_url: Optional[str] = Field(
        default=None,
        max_length=255,
        description='URL видео (обзор, разбор и т.п.)',
    )

    location_id: Optional[int] = Field(
        default=None,
        description='ID Location (если уже существует)',
    )
    location_name: Optional[str] = Field(
        default=None,
        max_length=120,
        description='Название локации; если нет в БД, будет создана автоматически',
    )

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError('price must be >= 0')
        return round(v, 2)

    @field_validator('min_level_name', 'max_level_name')
    @classmethod
    def validate_level_name(cls, v: Optional[str]) -> Optional[str]:
        normalized = _normalize_level_name(v)
        if normalized is None:
            return None
        if normalized not in CANONICAL_LEVEL_NAMES:
            raise ValueError(f"level must be one of: {', '.join(CANONICAL_LEVEL_NAMES)}")
        return normalized

    @field_validator('image_urls', mode='before')
    @classmethod
    def validate_image_urls(cls, v: Any) -> Optional[list[str]]:
        values = _normalize_media_url_list(v)
        return values or None

    @model_validator(mode='after')
    def validate_level_range(self):
        _ensure_level_range(self.min_level_name, self.max_level_name)
        return self


class TrainingCreate(TrainingBase):
    """
    Тело POST /api/v1/trainings (админ).
    """


class TrainingUpdate(BaseModel):
    """
    Тело PATCH /api/v1/trainings/{id} (админ).
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

    training_type: Optional[str] = Field(default=None, max_length=32)
    amplua_positions: Optional[dict[str, int]] = None

    coach_name: Optional[str] = Field(default=None, max_length=100)

    image_url: Optional[str] = Field(default=None, max_length=255)
    image_urls: Optional[list[str]] = None
    video_url: Optional[str] = Field(default=None, max_length=255)

    location_id: Optional[int] = None
    location_name: Optional[str] = Field(default=None, max_length=120)

    is_cancelled: Optional[bool] = Field(
        default=None,
        description='Флаг отмены; обычно лучше использовать отдельный endpoint /cancel',
    )

    @field_validator('min_level_name', 'max_level_name')
    @classmethod
    def validate_level_name(cls, v: Optional[str]) -> Optional[str]:
        normalized = _normalize_level_name(v)
        if normalized is None:
            return None
        if normalized not in CANONICAL_LEVEL_NAMES:
            raise ValueError(f"level must be one of: {', '.join(CANONICAL_LEVEL_NAMES)}")
        return normalized

    @field_validator('image_urls', mode='before')
    @classmethod
    def validate_image_urls(cls, v: Any) -> Optional[list[str]]:
        values = _normalize_media_url_list(v)
        return values or None

    @model_validator(mode='after')
    def validate_level_range(self):
        _ensure_level_range(self.min_level_name, self.max_level_name)
        return self

    class Config:
        extra = 'forbid'


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

    training_type: Optional[str]
    amplua_positions: Optional[dict[str, int]]

    coach_name: Optional[str]
    image_url: Optional[str]
    image_urls: Optional[list[str]]
    video_url: Optional[str]

    location_id: Optional[int]

    is_cancelled: bool

    class Config:
        from_attributes = True
