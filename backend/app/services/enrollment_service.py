from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Sequence

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException, ErrorCode
from app.policies import CANCEL_MIN_DELTA

from app.models.training import Training
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.level import Level
from app.models.payment import Payment, PaymentStatus
from app.models.setting import Setting
from app.models.user import User
from app.schemas.training import CANONICAL_LEVEL_NAMES
from app.services.ban_service import get_active_ban
from app.services.training_service import (
    build_amplua_position_snapshot,
    is_amplua_training,
    normalize_amplua_position_key,
)
from app.services.yookassa_service import create_refund

_LEVEL_ORDER = {name: idx for idx, name in enumerate(CANONICAL_LEVEL_NAMES)}


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


def _training_enrollment_rows(db: Session, training_id: int) -> list[Enrollment]:
    return (
        db.query(Enrollment)
        .filter(Enrollment.training_id == training_id)
        .order_by(Enrollment.id.asc())
        .all()
    )


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


def _build_amplua_context(training: Training, rows: list[Enrollment]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    slots = build_amplua_position_snapshot(
        positions=getattr(training, "amplua_positions", None),
        enrollments=rows,
    )
    by_key = {str(slot["key"]): slot for slot in slots}
    return slots, by_key



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


def _default_cancel_hours() -> int:
    try:
        return max(0, int(CANCEL_MIN_DELTA.total_seconds() // 3600))
    except Exception:
        return 2


def _get_cancel_hours_before_training(db: Session) -> int:
    default_hours = _default_cancel_hours()
    try:
        row = db.query(Setting).filter(Setting.key == "cancel_hours_before_training").one_or_none()
    except Exception:
        return default_hours

    raw = str(getattr(row, "value", "") or "").strip() if row is not None else ""
    if not raw:
        return default_hours
    try:
        value = int(float(raw))
    except Exception:
        return default_hours
    return max(0, min(value, 168))


def _coerce_dt_to_training_tz(dt: datetime, training_dt: datetime) -> datetime:
    if training_dt.tzinfo is None and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    if training_dt.tzinfo is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _refund_allowed_by_enrollment_time(
    *,
    enrollment: Enrollment,
    cancel_deadline: datetime,
    cancel_hours: int,
) -> bool:
    if cancel_hours <= 0:
        return True

    enrolled_at = getattr(enrollment, "created_at", None)
    if not isinstance(enrolled_at, datetime):
        return False

    enroll_time = _coerce_dt_to_training_tz(enrolled_at, cancel_deadline)
    refund_cutoff = cancel_deadline - timedelta(hours=cancel_hours)
    return enroll_time <= refund_cutoff


def _find_latest_paid_yookassa_payment(
    db: Session,
    *,
    user_id: int,
    training_id: int,
) -> Payment | None:
    return (
        db.query(Payment)
        .filter(Payment.user_id == int(user_id), Payment.training_id == int(training_id))
        .filter(Payment.status == PaymentStatus.PAID)
        .filter(Payment.provider_payment_id.isnot(None))
        .order_by(Payment.id.desc())
        .first()
    )


# ---------------------------------------------------------------------
# PUBLIC API (то, что обычно импортируют роутеры)
# ---------------------------------------------------------------------

def _canonical_level_name(value: Any) -> str | None:
    raw = str(value or "").strip().replace("−", "-")
    if not raw:
        return None
    if raw in _LEVEL_ORDER:
        return raw

    lowered = raw.lower()
    if "нович" in lowered:
        return "Новичок"
    if "средний-" in lowered:
        return "Средний-"
    if lowered == "средний":
        return "Средний"
    if "средний+" in lowered:
        return "Средний+"
    if "лайтпро" in lowered or "lightpro" in lowered:
        return "Средний+"
    if "лайт+" in lowered or "light+" in lowered:
        return "Средний"
    if "лайт" in lowered or "light" in lowered:
        return "Средний-"
    if "медиум" in lowered or "medium" in lowered:
        return "Средний+"
    return None


def _resolve_user_level_name(db: Session, user: User) -> str | None:
    direct_level = _canonical_level_name(getattr(getattr(user, "level", None), "name", None))
    if direct_level:
        return direct_level

    level_id = getattr(user, "level_id", None)
    if level_id is None:
        return None

    level_row = db.query(Level).filter(Level.id == int(level_id)).first()
    return _canonical_level_name(getattr(level_row, "name", None))


def _get_enrollment_block_reason(db: Session, user_id: int, *, user: User | None = None) -> str | None:
    active_ban = get_active_ban(db, user_id=user_id)
    if active_ban is not None:
        ban_reason = (getattr(active_ban, "reason", None) or "").strip()
        return ban_reason or "Пользователь находится в бане"

    if user is None:
        user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AppException.not_found(ErrorCode.USER_NOT_FOUND, f"User {user_id} not found")

    if not bool(getattr(user, "is_active", True)):
        return "Пользователь деактивирован администратором"

    return None


def _get_level_block_reason(db: Session, *, user: User, training: Training) -> str | None:
    min_level_name = _canonical_level_name(getattr(training, "min_level_name", None))
    max_level_name = _canonical_level_name(getattr(training, "max_level_name", None))

    if min_level_name is None and max_level_name is None:
        return None

    required_min = min_level_name or CANONICAL_LEVEL_NAMES[0]
    required_max = max_level_name or CANONICAL_LEVEL_NAMES[-1]

    min_idx = _LEVEL_ORDER.get(required_min)
    max_idx = _LEVEL_ORDER.get(required_max)
    if min_idx is None or max_idx is None:
        return None

    if min_idx > max_idx:
        min_idx, max_idx = max_idx, min_idx
        required_min, required_max = required_max, required_min

    user_level_name = _resolve_user_level_name(db, user)
    if user_level_name is None:
        return (
            "Вы не можете записаться, потому что у вас не указан уровень игрока. "
            "Обратитесь к администратору."
        )

    user_level_idx = _LEVEL_ORDER.get(user_level_name)
    if user_level_idx is None:
        return (
            "Вы не можете записаться, потому что ваш уровень не распознан. "
            "Обратитесь к администратору."
        )

    if user_level_idx < min_idx or user_level_idx > max_idx:
        required_range = required_min if required_min == required_max else f"{required_min} — {required_max}"
        return (
            f'Вы не можете записаться, потому что ваш уровень "{user_level_name}" '
            f'не соответствует требуемому "{required_range}".'
        )

    return None


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
    position_key: Optional[str] = None,
) -> Enrollment:
    training = _get_training(db, training_id)

    user = (
        db.query(User)
        .options(selectinload(User.level))
        .filter(User.id == user_id)
        .first()
    )
    if user is None:
        raise AppException.not_found(ErrorCode.USER_NOT_FOUND, f"User {user_id} not found")

    blocked_reason = _get_enrollment_block_reason(db, user_id=user_id, user=user)
    if blocked_reason:
        raise AppException.forbidden(
            message=blocked_reason,
            details={"user_id": user_id, "reason": blocked_reason},
        )

    level_block_reason = _get_level_block_reason(db, user=user, training=training)
    if level_block_reason:
        raise AppException.forbidden(
            message=level_block_reason,
            details={
                "user_id": user_id,
                "training_id": training_id,
                "reason": level_block_reason,
                "user_level_name": _resolve_user_level_name(db, user),
                "min_level_name": getattr(training, "min_level_name", None),
                "max_level_name": getattr(training, "max_level_name", None),
            },
        )

    training_is_amplua = is_amplua_training(training)
    requested_position_key = normalize_amplua_position_key(position_key) if training_is_amplua else None

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
    rows = _training_enrollment_rows(db, training_id)

    amplua_slots: list[dict[str, Any]] = []
    amplua_by_key: dict[str, dict[str, Any]] = {}
    selected_slot: dict[str, Any] | None = None
    can_put_to_reserve = False
    if training_is_amplua:
        amplua_slots, amplua_by_key = _build_amplua_context(training, rows)
        main_cap = sum(int(slot.get("capacity_main", slot.get("capacity", 0)) or 0) for slot in amplua_slots)
        reserve_cap = sum(int(slot.get("capacity_reserve", 0) or 0) for slot in amplua_slots)
        can_put_to_reserve = bool(main_cap and active_cnt >= main_cap and reserve_cap and reserve_cnt < reserve_cap)

        if requested_position_key:
            selected_slot = amplua_by_key.get(requested_position_key)
            if not selected_slot:
                raise AppException.validation(
                    message="Выберите корректную позицию",
                    details={
                        "training_id": training_id,
                        "requested_position_key": requested_position_key,
                        "available_positions": [slot for slot in amplua_slots if slot.get("has_free_slots")],
                        "position_slots": amplua_slots,
                    },
                )
            slot_can_reserve = bool(can_put_to_reserve and selected_slot.get("has_free_reserve_slots"))
            if not selected_slot.get("has_free_slots") and not slot_can_reserve:
                raise AppException.conflict(
                    ErrorCode.TRAINING_FULL,
                    f'На позиции "{selected_slot["label"]}" нет свободных мест',
                    details={
                        "training_id": training_id,
                        "requested_position_key": requested_position_key,
                        "requested_position_label": selected_slot["label"],
                        "requested_team_key": selected_slot.get("team_key"),
                        "requested_team_label": selected_slot.get("team_label"),
                        "requested_position_name": selected_slot.get("position_label"),
                        "available_positions": [slot for slot in amplua_slots if slot.get("has_free_slots")],
                        "position_slots": amplua_slots,
                    },
                )
        else:
            raise AppException.validation(
                message="Для тренировки типа \"амплуа\" выберите позицию",
                details={
                    "training_id": training_id,
                    "available_positions": [slot for slot in amplua_slots if slot.get("has_free_slots")],
                    "position_slots": amplua_slots,
                },
            )

    status = ACTIVE_STATUS()
    is_reserve_flag = False

    # main заполнен -> reserve
    if main_cap and active_cnt >= main_cap:
        if reserve_cap and reserve_cnt < reserve_cap:
            if training_is_amplua and selected_slot is not None and not bool(selected_slot.get("has_free_reserve_slots")):
                raise AppException.conflict(
                    ErrorCode.TRAINING_FULL,
                    f'На позиции "{selected_slot["label"]}" нет свободных мест в резерве',
                    details={
                        "training_id": training_id,
                        "requested_position_key": requested_position_key,
                        "requested_position_label": selected_slot["label"],
                        "requested_team_key": selected_slot.get("team_key"),
                        "requested_team_label": selected_slot.get("team_label"),
                        "requested_position_name": selected_slot.get("position_label"),
                        "available_positions": [slot for slot in amplua_slots if slot.get("has_free_slots")],
                        "position_slots": amplua_slots,
                    },
                )
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
        if hasattr(existing, "position_key"):
            setattr(existing, "position_key", requested_position_key)
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
    if hasattr(e, "position_key"):
        setattr(e, "position_key", requested_position_key)
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

    cancel_hours = _get_cancel_hours_before_training(db)
    cancel_deadline = start_at - timedelta(hours=cancel_hours)
    now = _now_like(start_at)
    late = now >= cancel_deadline

    paid_payment = _find_latest_paid_yookassa_payment(db, user_id=user_id, training_id=training_id)
    enrollment_paid_flag = bool(getattr(e, "is_paid", False))
    was_paid = enrollment_paid_flag or paid_payment is not None

    if not late and paid_payment is not None:
        refund_by_time_allowed = _refund_allowed_by_enrollment_time(
            enrollment=e,
            cancel_deadline=cancel_deadline,
            cancel_hours=cancel_hours,
        )

        if refund_by_time_allowed:
            refund_amount = getattr(paid_payment, "amount", 0) or 0
            provider_payment_id = str(getattr(paid_payment, "provider_payment_id", "") or "").strip()
            if refund_amount > 0 and provider_payment_id:
                refund_obj = create_refund(
                    db,
                    provider_payment_id=provider_payment_id,
                    amount_rub=refund_amount,
                    description=f"Возврат за отмену записи #{enrollment_id}",
                    metadata={
                        "enrollment_id": str(enrollment_id),
                        "training_id": str(training_id),
                        "user_id": str(user_id),
                    },
                )
                refund_status = str(refund_obj.get("status") or "").strip().lower()
                if refund_status not in {"succeeded", "pending"}:
                    raise AppException.conflict(
                        message="Не удалось оформить возврат средств в ЮKassa",
                        details={"refund": refund_obj},
                    )
                paid_payment.status = PaymentStatus.REFUNDED
                db.add(paid_payment)
                if hasattr(e, "is_paid"):
                    setattr(e, "is_paid", False)

    if hasattr(e, "status"):
        setattr(e, "status", CANCELLED_LATE_STATUS() if late else CANCELLED_STATUS())
    if hasattr(e, "cancelled_at"):
        # cancelled_at лучше хранить aware; но если колонка у тебя naive — БД сама сконвертит
        setattr(e, "cancelled_at", _now_aware())

    db.add(e)

    if late and not was_paid:
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
