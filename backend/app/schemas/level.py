# app/schemas/level.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LevelDTO(BaseModel):
    """
    Уровень игрока (для вывода на фронт).
    Пример: Новичок, Средний-, Средний, Средний+.
    """
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        # Разрешаем создавать объект из ORM-модели (SQLAlchemy)
        from_attributes = True
