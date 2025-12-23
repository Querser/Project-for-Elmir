from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.ban import Ban, BanType


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _active_until_filter(now: datetime):
    # active=true AND (until is null OR until >= now)
    return (Ban.active.is_(True)) & (or_(Ban.until.is_(None), Ban.until >= now))


def has_active_ban(db: Session, user_id: int) -> bool:
    """
    Имя ожидает enrollment_service.py
    """
    now = _now_utc()
    return (
        db.query(Ban.id)
        .filter(Ban.user_id == user_id)
        .filter(_active_until_filter(now))
        .first()
        is not None
    )


# ---- Backward-compatible aliases (на случай старых импортов) ----
user_has_active_ban = has_active_ban
is_user_banned = has_active_ban


def list_bans(
    db: Session,
    *,
    user_id: Optional[int] = None,
    active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Ban]:
    """
    Имя ожидает admin_billing.py
    """
    q = db.query(Ban)

    if user_id is not None:
        q = q.filter(Ban.user_id == user_id)

    if active is True:
        q = q.filter(_active_until_filter(_now_utc()))
    elif active is False:
        # "неактивные" = active=false OR until < now
        now = _now_utc()
        q = q.filter(or_(Ban.active.is_(False), (Ban.until.is_not(None) & (Ban.until < now))))

    return q.order_by(Ban.id.desc()).offset(offset).limit(limit).all()


def _create_ban(
    db: Session,
    *,
    user_id: int,
    ban_type: BanType,
    reason: str,
    until: Optional[datetime] = None,
) -> Ban:
    ban = Ban(
        user_id=user_id,
        type=ban_type,
        reason=reason,
        active=True,
        created_at=_now_utc(),
        until=until,
    )
    db.add(ban)
    db.commit()
    db.refresh(ban)
    return ban


def manual_ban_user(db: Session, *, user_id: int, reason: str, until: Optional[datetime] = None) -> Ban:
    """
    Имя ожидает admin_billing.py
    """
    return _create_ban(db, user_id=user_id, ban_type=BanType.MANUAL, reason=reason, until=until)


def create_auto_debt_ban(db: Session, *, user_id: int, reason: str, until: Optional[datetime] = None) -> Ban:
    """
    Для autoban_job: создаём авто-бан за долг.
    """
    return _create_ban(db, user_id=user_id, ban_type=BanType.AUTO_DEBT, reason=reason, until=until)


# alias на случай другого имени в job
ensure_auto_debt_ban = create_auto_debt_ban


def deactivate_auto_debt_bans_if_any(db: Session, *, user_id: int) -> int:
    """
    Снимает ТОЛЬКО AUTO_DEBT баны.
    Возвращает количество снятых банов.
    """
    now = _now_utc()
    bans = (
        db.query(Ban)
        .filter(Ban.user_id == user_id, Ban.type == BanType.AUTO_DEBT)
        .filter(_active_until_filter(now))
        .all()
    )

    for b in bans:
        b.active = False
        b.until = now

    if bans:
        db.commit()

    return len(bans)


def manual_unban_user(db: Session, *, user_id: int) -> int:
    """
    ВОТ ЭТОГО ИМЕНИ ТЕБЕ НЕ ХВАТАЛО.
    admin_billing.py импортирует manual_unban_user.
    Снимает ТОЛЬКО MANUAL баны.
    """
    now = _now_utc()
    bans = (
        db.query(Ban)
        .filter(Ban.user_id == user_id, Ban.type == BanType.MANUAL)
        .filter(_active_until_filter(now))
        .all()
    )

    for b in bans:
        b.active = False
        b.until = now

    if bans:
        db.commit()

    return len(bans)


def unban_user_if_no_open_debts(db: Session, *, user_id: int) -> int:
    """
    Имя ожидает admin_billing.py:
    снимаем AUTO_DEBT бан, если нет открытых долгов.
    """
    try:
        from app.services.debt_service import has_open_debts
    except Exception:
        # если debt_service недоступен  не ломаем приложение
        return 0

    if has_open_debts(db, user_id):
        return 0

    return deactivate_auto_debt_bans_if_any(db, user_id=user_id)


# Дополнительно (если где-то зовут так)
def unban_user(db: Session, *, user_id: int) -> int:
    """
    Снимает ВСЕ активные баны (и MANUAL, и AUTO_DEBT).
    """
    now = _now_utc()
    bans = (
        db.query(Ban)
        .filter(Ban.user_id == user_id)
        .filter(_active_until_filter(now))
        .all()
    )

    for b in bans:
        b.active = False
        b.until = now

    if bans:
        db.commit()

    return len(bans)
