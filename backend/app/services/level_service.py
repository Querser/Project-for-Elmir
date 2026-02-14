from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.level import Level


def _normalized_level_name(value: str | None) -> str:
    raw = (value or "").strip().lower()
    return raw.replace("ё", "е").replace("-", " ").replace("_", " ")


def get_default_level_id(db: Session) -> int | None:
    levels = (
        db.query(Level)
        .order_by(Level.sort_order.asc(), Level.id.asc())
        .all()
    )
    if not levels:
        return None

    for level in levels:
        if "нович" in _normalized_level_name(level.name):
            return int(level.id)

    return int(levels[0].id)


def get_all_levels(db: Session) -> list[Level]:
    return (
        db.query(Level)
        .order_by(Level.sort_order.asc(), Level.id.asc())
        .all()
    )
