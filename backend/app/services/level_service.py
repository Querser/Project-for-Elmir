# app/services/level_service.py
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.level import Level


def get_all_levels(db: Session) -> list[Level]:
    """
    Возвращает список всех уровней.

    Сейчас сортируем по id, при желании можно сортировать по полю sort_order,
    если оно есть в модели Level.
    """
    return (
        db.query(Level)
        .order_by(Level.id.asc())
        .all()
    )
