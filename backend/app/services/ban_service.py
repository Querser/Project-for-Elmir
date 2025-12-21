# backend/app/services/ban_service.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.ban import Ban, BanType


def has_active_ban(db: Session, *, user_id: int) -> bool:
    return (
        db.query(Ban)
        .filter(
            Ban.user_id == user_id,
            Ban.active.is_(True),
        )
        .first()
        is not None
    )


def ensure_auto_debt_ban(db: Session, *, user_id: int, reason: str) -> Ban:
    """
    Идемпотентно: если уже есть активный AUTO_DEBT бан — возвращаем его.
    """
    existing = (
        db.query(Ban)
        .filter(
            Ban.user_id == user_id,
            Ban.active.is_(True),
            Ban.type == BanType.AUTO_DEBT.value,
        )
        .order_by(Ban.created_at.desc())
        .first()
    )
    if existing:
        # можно обновлять reason, чтобы он был актуальный
        existing.reason = reason
        db.commit()
        db.refresh(existing)
        return existing

    ban = Ban(
        user_id=user_id,
        type=BanType.AUTO_DEBT.value,
        reason=reason,
        active=True,
        created_at=datetime.utcnow(),
        until=None,
    )
    db.add(ban)
    db.commit()
    db.refresh(ban)
    return ban


def deactivate_auto_debt_bans_if_any(db: Session, *, user_id: int) -> int:
    """
    Снимаем активные AUTO_DEBT баны.
    Возвращаем количество снятых банов.
    """
    bans = (
        db.query(Ban)
        .filter(
            Ban.user_id == user_id,
            Ban.active.is_(True),
            Ban.type == BanType.AUTO_DEBT.value,
        )
        .all()
    )

    for b in bans:
        b.active = False
        b.until = datetime.utcnow()

    if bans:
        db.commit()

    return len(bans)
