from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ErrorCode
from app.policies import CANCEL_MIN_DELTA

from app.models.training import Training
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.user import User
from app.services.ban_service import get_active_ban


def _now_aware() -> datetime:
    """UTC aware datetime."""
    return datetime.now(timezone.utc)


def _now_like(dt: datetime) -> datetime:
    """
    Возвращает now в формате, совместимом с dt:
    - dt aware -> now aware (UTC)
    - dt naive -> now naive (UTC naive)
    """
    if dt.tzinfo is None:
        return datetime.utcnow()
    return _now_aware()


def _enum_member(enum_cls: Any, *names: str, fallback_value: str) -> Any:
    """
    Пытаемся взять enum-атрибут, иначе возвращаем значение по умолчанию.
    Работает и если EnrollmentStatus = Enum, и если это просто набор строк.
    """
    for n in names:
        if hasattr(enum_cls, n):
            return getattr(enum_cls, n)
    try:
        return enum_cls(fallback_value)
    except Exception:
        return fallback_value


def ACTIVE_STATUS() -> Any:
    return _enum_member(EnrollmentStatus, "ACTIVE", "ENROLLED", "CONFIRMED", fallback_value="active")


def CANCELLED_STATUS() -> Any:
    return _enum_member(EnrollmentStatus, "CANCELLED", "CANCELED", fallback_value="cancelled")


def CANCELLED_LATE_STATUS() -> Any:
    return _enum_member(EnrollmentStatus, "CANCELLED_LATE", "CANCELED_LATE", fallback_value="cancelled_late")


def RESERVE_STATUS() -> Any:
    return _enum_member(EnrollmentStatus, "RESERVE", "WAITLIST", "STANDBY", fallback_value="reserve")


def _status_to_str(st: Any) -> str:
    if st is None:
        return ""
    # SQLAlchemy Enum часто приходит как EnumMember, у которого есть .value
    v = getattr(st, "value", st)
    try:
        s = str(v)
    except Exception:
        return ""
    return s.lower().strip()


def _counts_for_training(db: Session, training_id: int) -> tuple[int, int]:
    """
    Возвращает (active_cnt, reserve_cnt) по факту из БД.
    """
    rows: Sequence[tuple[Any]] = (
        db.query(Enrollment.status)
        .filter(Enrollment.training_id == training_id)
        .all()
    )

    active_cnt = 0
    reserve_cnt = 0
    for (st,) in rows:
        if _is_active(st):
            active_cnt += 1
        elif _is_reserve(st):
            reserve_cnt += 1
    return active_cnt, reserve_cnt



def _is_active(st: Any) -> bool:
    if st == ACTIVE_STATUS():
        return True
    return _status_to_str(st) in {"active", "enrolled", "confirmed"}


def _is_reserve(st: Any) -> bool:
    if st == RESERVE_STATUS():
        return True
    return _status_to_str(st) in {"reserve", "waitlist", "standby"}


def _is_cancelled(st: Any) -> bool:
    if st in (CANCELLED_STATUS(), CANCELLED_LATE_STATUS()):
        return True
    return _status_to_str(st) in {"cancelled", "canceled", "cancelled_late", "canceled_late"}


def _get_training(db: Session, training_id: int) -> Training:
    t = db.query(Training).filter(Training.id == training_id).first()
    if not t:
        raise AppException.not_found(ErrorCode.TRAINING_NOT_FOUND, f"Training {training_id} not found")

    # отменённые тренировки не записываем
    st = getattr(t, "status", None)
    if isinstance(st, str) and st.lower() in {"cancelled", "canceled"}:
        raise AppException.conflict(ErrorCode.TRAINING_CANCELLED, "Training is cancelled")

    return t


def _training_capacity(t: Training) -> tuple[int, int]:
    main = getattr(t, "capacity_main", None)
    reserve = getattr(t, "capacity_reserve", None)
    return int(main or 0), int(reserve or 0)


def _active_enrollments_count(t: Training) -> int:
    enrollments = getattr(t, "enrollments", []) or []
    cnt = 0
    for e in enrollments:
        if _is_active(getattr(e, "status", None)):
            cnt += 1
    return cnt


def _estimate_amount(training: Training, enrollment: Optional[Enrollment] = None) -> float:
    for obj in (enrollment, training):
        if obj is None:
            continue
        for attr in ("amount", "price", "final_price"):
            v = getattr(obj, attr, None)
            if isinstance(v, (int, float)):
                return float(v)
    return 0.0


def _get_enrollment_block_reason(db: Session, user_id: int) -> str | None:
    active_ban = get_active_ban(db, user_id=user_id)
    if active_ban is not None:
        ban_reason = (getattr(active_ban, "reason", None) or "").strip()
        return ban_reason or "Пользователь находится в бане"

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AppException.not_found(ErrorCode.USER_NOT_FOUND, f"User {user_id} not found")

    if not bool(getattr(user, "is_active", True)):
        return "Пользователь деактивирован администратором"

    return None


# ---------------------------------------------------------------------
# PUBLIC API (то, что обычно импортируют роутеры)
# ---------------------------------------------------------------------

def get_enrollment_by_id(db: Session, *, enrollment_id: int) -> Enrollment:
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise AppException.not_found(ErrorCode.ENROLLMENT_NOT_FOUND, f"Enrollment {enrollment_id} not found")
    return e


def get_user_enrollments(
    db: Session,
    *,
    user_id: int,
    include_cancelled: bool = False,
) -> list[Enrollment]:
    q = db.query(Enrollment).filter(Enrollment.user_id == user_id)

    enrollments = q.order_by(Enrollment.id.desc()).all()
    if include_cancelled:
        return enrollments

    return [e for e in enrollments if not _is_cancelled(getattr(e, "status", None))]


def get_training_roster(
    db: Session,
    *,
    training_id: int,
    include_reserve: bool = True,
    include_cancelled: bool = False,
) -> list[Enrollment]:
    """
    Роутеры обычно ждут эту функцию.
    По умолчанию возвращает активных + (опционально) резерв.
    """
    # проверим, что тренировка существует (и не отменена)
    _get_training(db, training_id)

    enrollments: list[Enrollment] = (
        db.query(Enrollment)
        .filter(Enrollment.training_id == training_id)
        .order_by(Enrollment.id.asc())
        .all()
    )

    if include_cancelled:
        return enrollments

    filtered: list[Enrollment] = []
    for e in enrollments:
        st = getattr(e, "status", None)
        if _is_active(st):
            filtered.append(e)
            continue
        if include_reserve and _is_reserve(st):
            filtered.append(e)
            continue

    return filtered


def enroll_user_to_training(
    db: Session,
    *,
    training_id: int,
    user_id: int,
    is_paid: bool = False,
    price_tier_id: Optional[int] = None,
) -> Enrollment:
    training = _get_training(db, training_id)

    blocked_reason = _get_enrollment_block_reason(db, user_id=user_id)
    if blocked_reason:
        raise AppException.forbidden(
            message=blocked_reason,
            details={"user_id": user_id, "reason": blocked_reason},
        )

    existing = (
        db.query(Enrollment)
        .filter(Enrollment.training_id == training_id, Enrollment.user_id == user_id)
        .first()
    )

    # Если уже есть запись:
    # - ACTIVE/RESERVE -> конфликт (уже записан)
    # - CANCELLED/CANCELLED_LATE -> разрешаем "ре-запись" через ре-активацию той же строки
    if existing:
        st = getattr(existing, "status", None)
        if _is_active(st) or _is_reserve(st):
            raise AppException.conflict(ErrorCode.ALREADY_ENROLLED, "User already enrolled")
        if not _is_cancelled(st):
            # На всякий случай: если статус какой-то неизвестный, считаем что повтор нельзя
            raise AppException.conflict(ErrorCode.ALREADY_ENROLLED, "User already enrolled")

    main_cap, reserve_cap = _training_capacity(training)

    active_cnt, reserve_cnt = _counts_for_training(db, training_id)

    status = ACTIVE_STATUS()
    is_reserve_flag = False

    # main заполнен -> reserve
    if main_cap and active_cnt >= main_cap:
        if reserve_cap and reserve_cnt < reserve_cap:
            status = RESERVE_STATUS()
            is_reserve_flag = True
        else:
            raise AppException.conflict(ErrorCode.TRAINING_FULL, "Training is full")

    # Если была отменённая запись — обновляем её, а не создаём новую
    if existing:
        if hasattr(existing, "status"):
            setattr(existing, "status", status)
        if hasattr(existing, "is_paid"):
            setattr(existing, "is_paid", bool(is_paid))
        if hasattr(existing, "is_reserve"):
            setattr(existing, "is_reserve", bool(is_reserve_flag))
        if price_tier_id is not None and hasattr(existing, "price_tier_id"):
            setattr(existing, "price_tier_id", int(price_tier_id))
        # если есть cancelled_at — логично сбросить
        if hasattr(existing, "cancelled_at"):
            setattr(existing, "cancelled_at", None)

        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    # Иначе создаём новую запись
    e = Enrollment(training_id=training_id, user_id=user_id)

    if hasattr(e, "status"):
        setattr(e, "status", status)
    if hasattr(e, "is_paid"):
        setattr(e, "is_paid", bool(is_paid))
    if hasattr(e, "is_reserve"):
        setattr(e, "is_reserve", bool(is_reserve_flag))
    if price_tier_id is not None and hasattr(e, "price_tier_id"):
        setattr(e, "price_tier_id", int(price_tier_id))

    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def cancel_enrollment(db: Session, *, enrollment_id: int, user_id: int) -> Enrollment:
    e = db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()
    if not e:
        raise AppException.not_found(ErrorCode.ENROLLMENT_NOT_FOUND, f"Enrollment {enrollment_id} not found")
    if getattr(e, "user_id", None) != user_id:
        raise AppException.forbidden("Not your enrollment")

    training_id = int(getattr(e, "training_id"))
    training = _get_training(db, training_id)

    start_at = getattr(training, "start_at", None)
    if not isinstance(start_at, datetime):
        if hasattr(e, "status"):
            setattr(e, "status", CANCELLED_STATUS())
        db.commit()
        db.refresh(e)
        return e

    now = _now_like(start_at)
    late = now >= (start_at - CANCEL_MIN_DELTA)

    if hasattr(e, "status"):
        setattr(e, "status", CANCELLED_LATE_STATUS() if late else CANCELLED_STATUS())
    if hasattr(e, "cancelled_at"):
        # cancelled_at лучше хранить aware; но если колонка у тебя naive — БД сама сконвертит
        setattr(e, "cancelled_at", _now_aware())

    db.add(e)

    if late:
        amount = _estimate_amount(training, e)

        try:
            from app.services.debt_service import create_open_debt_if_missing  # type: ignore
            create_open_debt_if_missing(db, user_id=user_id, training_id=training.id, amount=amount)
        except Exception:
            pass

        try:
            from app.services.ban_service import ensure_auto_debt_ban  # type: ignore
            ensure_auto_debt_ban(db, user_id=user_id, training_id=training.id)
        except Exception:
            pass

    db.commit()
    db.refresh(e)
    return e


def cancel_enrollment_for_user(
    db: Session,
    *,
    user_id: int,
    training_id: Optional[int] = None,
    enrollment_id: Optional[int] = None,
) -> Enrollment:
    """
    Функция, которую импортирует роутер.

    Поддерживает оба сценария:
    - cancel_enrollment_for_user(db, user_id=..., training_id=...)
    - cancel_enrollment_for_user(db, user_id=..., enrollment_id=...)
    """
    if enrollment_id is None and training_id is None:
        raise AppException.validation("Either training_id or enrollment_id is required")

    if enrollment_id is not None:
        return cancel_enrollment(db, enrollment_id=int(enrollment_id), user_id=user_id)

    e = (
        db.query(Enrollment)
        .filter(Enrollment.user_id == user_id, Enrollment.training_id == int(training_id))
        .first()
    )
    if not e:
        raise AppException.not_found(
            ErrorCode.ENROLLMENT_NOT_FOUND,
            f"Enrollment for user {user_id} and training {training_id} not found",
        )

    return cancel_enrollment(db, enrollment_id=int(getattr(e, "id")), user_id=user_id)
