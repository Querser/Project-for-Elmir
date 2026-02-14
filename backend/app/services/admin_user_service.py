from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, and_, cast, func, or_
from sqlalchemy.orm import Session, selectinload

from app.models.ban import Ban
from app.models.debt import Debt, DebtStatus
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.level import Level
from app.models.training import Training
from app.models.user import User


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _active_ban_filter(now: datetime):
    return and_(
        Ban.active.is_(True),
        or_(Ban.until.is_(None), Ban.until >= now),
    )


def _user_to_list_item(user: User, open_debts_count: int, has_active_ban: bool) -> dict:
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "phone": user.phone,
        "level_id": user.level_id,
        "level_name": user.level.name if user.level else None,
        "is_active": bool(user.is_active),
        "is_admin": bool(user.is_admin),
        "has_active_ban": bool(has_active_ban),
        "open_debts_count": int(open_debts_count or 0),
    }


def list_admin_users(
    db: Session,
    *,
    q: str | None,
    level_id: int | None,
    is_banned: bool | None,
    limit: int,
    offset: int,
):
    now = _now_utc()

    query = db.query(User).options(selectinload(User.level))

    if q:
        q_norm = q.strip()
        if q_norm:
            like = f"%{q_norm}%"
            query = query.filter(
                or_(
                    cast(User.id, String).ilike(like),
                    User.first_name.ilike(like),
                    User.last_name.ilike(like),
                    User.username.ilike(like),
                    User.phone.ilike(like),
                    cast(User.telegram_id, String).ilike(like),
                )
            )

    if level_id is not None:
        query = query.filter(User.level_id == level_id)

    if is_banned is True:
        query = query.filter(
            db.query(Ban.id).filter(Ban.user_id == User.id).filter(_active_ban_filter(now)).exists()
        )
    elif is_banned is False:
        query = query.filter(
            ~db.query(Ban.id).filter(Ban.user_id == User.id).filter(_active_ban_filter(now)).exists()
        )

    total = query.count()
    users = query.order_by(User.id.desc()).offset(offset).limit(limit).all()

    if not users:
        return [], total

    user_ids = [u.id for u in users]

    debt_rows = (
        db.query(Debt.user_id, func.count(Debt.id))
        .filter(Debt.user_id.in_(user_ids), Debt.status == DebtStatus.OPEN)
        .group_by(Debt.user_id)
        .all()
    )
    debts_map = {uid: int(cnt or 0) for uid, cnt in debt_rows}

    ban_rows = (
        db.query(Ban.user_id, func.count(Ban.id))
        .filter(Ban.user_id.in_(user_ids))
        .filter(_active_ban_filter(now))
        .group_by(Ban.user_id)
        .all()
    )
    bans_map = {uid: int(cnt or 0) > 0 for uid, cnt in ban_rows}

    items = [_user_to_list_item(u, debts_map.get(u.id, 0), bans_map.get(u.id, False)) for u in users]
    return items, total


def get_admin_user_details(db: Session, *, user_id: int) -> dict | None:
    now = _now_utc()

    user = db.query(User).options(selectinload(User.level)).filter(User.id == user_id).first()
    if not user:
        return None

    active_bans_count = (
        db.query(func.count(Ban.id))
        .filter(Ban.user_id == user.id)
        .filter(_active_ban_filter(now))
        .scalar()
    )

    open_debts_count = (
        db.query(func.count(Debt.id))
        .filter(Debt.user_id == user.id, Debt.status == DebtStatus.OPEN)
        .scalar()
    )

    history_rows = (
        db.query(Enrollment, Training)
        .join(Training, Training.id == Enrollment.training_id)
        .filter(Enrollment.user_id == user.id)
        .order_by(Enrollment.created_at.desc())
        .limit(200)
        .all()
    )

    history = []
    for enr, tr in history_rows:
        history.append(
            {
                "enrollment_id": enr.id,
                "training_id": enr.training_id,
                "status": enr.status.value if hasattr(enr.status, "value") else str(enr.status),
                "is_reserve": bool(enr.is_reserve),
                "is_paid": bool(enr.is_paid),
                "created_at": enr.created_at,
                "training_title": tr.title,
                "training_start_at": tr.start_at,
                "coach_name": tr.coach_name,
                "location_id": tr.location_id,
            }
        )

    current_debts = (
        db.query(Debt)
        .filter(Debt.user_id == user.id, Debt.status == DebtStatus.OPEN)
        .order_by(Debt.created_at.desc())
        .all()
    )

    bans = db.query(Ban).filter(Ban.user_id == user.id).order_by(Ban.created_at.desc()).limit(100).all()

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "phone": user.phone,
        "gender": user.gender,
        "birth_date": user.birth_date,
        "level_id": user.level_id,
        "level_name": user.level.name if user.level else None,
        "rating": int(user.rating or 0),
        "cups": int(user.cups or 0),
        "is_active": bool(user.is_active),
        "is_admin": bool(user.is_admin),
        "has_active_ban": bool(active_bans_count and active_bans_count > 0),
        "open_debts_count": int(open_debts_count or 0),
        "training_history": history,
        "current_debts": [
            {
                "id": d.id,
                "training_id": d.training_id,
                "amount": d.amount,
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "created_at": d.created_at,
                "closed_at": d.closed_at,
            }
            for d in current_debts
        ],
        "bans": [
            {
                "id": b.id,
                "type": b.type.value if hasattr(b.type, "value") else str(b.type),
                "reason": b.reason,
                "active": bool(b.active),
                "created_at": b.created_at,
                "until": b.until,
            }
            for b in bans
        ],
    }


def set_user_level(db: Session, *, user_id: int, level_id: int | None) -> User | None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    if level_id is not None:
        level_exists = db.query(Level.id).filter(Level.id == level_id).first() is not None
        if not level_exists:
            return None

    user.level_id = level_id
    db.commit()
    db.refresh(user)
    return user


def mark_debt_paid_offline(db: Session, *, user_id: int, debt_id: int):
    debt = db.query(Debt).filter(Debt.id == debt_id, Debt.user_id == user_id).first()
    if not debt:
        return None

    debt.status = DebtStatus.CLOSED
    debt.closed_at = _now_utc()

    enr = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.training_id == debt.training_id)
        .first()
    )
    if enr:
        enr.is_paid = True

    db.commit()
    db.refresh(debt)
    if enr:
        db.refresh(enr)

    return debt


def _status_value(status: object) -> str:
    value = getattr(status, "value", status)
    try:
        return str(value).lower().strip()
    except Exception:
        return ""


def _is_active_or_reserve_status(status: object) -> bool:
    st = _status_value(status)
    return st in {"active", "enrolled", "confirmed", "reserve", "waitlist", "standby"}


def cancel_user_active_enrollments(
    db: Session,
    *,
    user_id: int,
    require_active_ban: bool = True,
) -> tuple[int, bool] | None:
    user_exists = db.query(User.id).filter(User.id == user_id).first() is not None
    if not user_exists:
        return None

    now = _now_utc()
    has_active_ban = (
        db.query(Ban.id)
        .filter(Ban.user_id == user_id)
        .filter(_active_ban_filter(now))
        .first()
        is not None
    )
    if require_active_ban and not has_active_ban:
        return 0, False

    cancelled_status = (
        getattr(EnrollmentStatus, "CANCELLED", None)
        or getattr(EnrollmentStatus, "CANCELED", None)
        or "cancelled"
    )

    enrollments = db.query(Enrollment).filter(Enrollment.user_id == user_id).all()
    cancelled_count = 0
    for enr in enrollments:
        if not _is_active_or_reserve_status(getattr(enr, "status", None)):
            continue
        enr.status = cancelled_status
        if hasattr(enr, "is_reserve"):
            enr.is_reserve = False
        if hasattr(enr, "cancelled_at"):
            enr.cancelled_at = now
        db.add(enr)
        cancelled_count += 1

    if cancelled_count:
        db.commit()

    return cancelled_count, has_active_ban
