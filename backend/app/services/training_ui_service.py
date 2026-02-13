from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.policies import cancel_deadline_at, pick_price_for_user, is_late_cancel
from app.models.setting import Setting
from app.services.ban_service import get_active_ban

# Пытаемся подцепить твою модель price tiers (как ты её назвал в новых файлах)
PriceTierModel = None
for _path in (
    "app.models.price_tier",
    "app.models.training_price_tier",
    "app.models.price_tiers",
):
    try:
        mod = __import__(_path, fromlist=["PriceTier", "TrainingPriceTier"])
        PriceTierModel = getattr(mod, "PriceTier", None) or getattr(mod, "TrainingPriceTier", None)
        if PriceTierModel is not None:
            break
    except Exception:
        pass

# Enrollment модель — нужна для can_enroll/user_enrollment_status/occupied_*
EnrollmentModel = None
try:
    from app.models.enrollment import Enrollment as EnrollmentModel  # type: ignore
except Exception:
    EnrollmentModel = None


def _status_value(v: Any) -> str:
    # Enum/строка/что угодно → строка
    if v is None:
        return ""
    return getattr(v, "value", None) or str(v)


def _safe_text(v: Any) -> str:
    if v is None:
        return ""
    try:
        return str(v).strip()
    except Exception:
        return ""


def _get_setting_value(db: Session, key: str, default: str) -> str:
    try:
        row = db.query(Setting).filter(Setting.key == key).one_or_none()
    except Exception:
        return default
    if row is None:
        return default
    value = _safe_text(getattr(row, "value", None))
    return value or default


def _participant_payload(enrollment: Any, *, is_reserve: bool) -> dict[str, Any]:
    user_obj = getattr(enrollment, "user", None)
    user_id = getattr(enrollment, "user_id", None)

    first_name = _safe_text(getattr(user_obj, "first_name", None))
    last_name = _safe_text(getattr(user_obj, "last_name", None))
    username = _safe_text(getattr(user_obj, "username", None))

    full_name = " ".join(x for x in (first_name, last_name) if x).strip()
    if not full_name and username:
        full_name = f"@{username}"
    if not full_name and user_id is not None:
        full_name = f"Игрок #{user_id}"

    level_name = _safe_text(getattr(getattr(user_obj, "level", None), "name", None))

    return {
        "enrollment_id": getattr(enrollment, "id", None),
        "user_id": user_id,
        "first_name": first_name or None,
        "last_name": last_name or None,
        "username": username or None,
        "full_name": full_name or None,
        "level_name": level_name or None,
        "is_reserve": bool(is_reserve),
    }


def build_training_ui_payload(
    db: Session,
    training: Any,
    user: Any | None,
    *,
    include_participants: bool = True,
) -> Dict[str, Any]:
    training_id = getattr(training, "id", None)

    capacity_main = int(getattr(training, "capacity_main", 0) or 0)
    capacity_reserve = int(getattr(training, "capacity_reserve", 0) or 0)

    occupied_main = 0
    occupied_reserve = 0
    user_enrollment_status = "none"
    user_queue_position = None
    user_enrollment_id: Optional[int] = None
    participants_main: list[dict[str, Any]] = []
    participants_reserve: list[dict[str, Any]] = []

    if EnrollmentModel is not None and training_id is not None:
        q = db.query(EnrollmentModel).filter(EnrollmentModel.training_id == training_id)
        if hasattr(EnrollmentModel, "id"):
            q = q.order_by(getattr(EnrollmentModel, "id").asc())
        if include_participants and hasattr(EnrollmentModel, "user"):
            try:
                from sqlalchemy.orm import selectinload

                q = q.options(selectinload(getattr(EnrollmentModel, "user")))
            except Exception:
                # Если eager-loading недоступен, продолжим без него.
                pass

        rows: List[Any] = q.all()
        for e in rows:
            st = _status_value(getattr(e, "status", None)).lower()

            # максимально “толерантная” классификация, чтобы не сломаться на enum-ах
            is_cancelled = ("cancel" in st) or ("noshow" in st) or ("no_show" in st)
            is_reserve = ("reserve" in st) or ("wait" in st) or bool(getattr(e, "is_reserve", False))

            if not is_cancelled:
                if is_reserve:
                    occupied_reserve += 1
                else:
                    occupied_main += 1

                if include_participants:
                    participant = _participant_payload(e, is_reserve=is_reserve)
                    if is_reserve:
                        participants_reserve.append(participant)
                    else:
                        participants_main.append(participant)

            if user is not None and getattr(e, "user_id", None) == getattr(user, "id", None):
                # --- статус для UI (frontend ждёт main/reserve/none/cancelled) ---
                user_enrollment_id = getattr(e, "id", None)
                user_queue_position = getattr(e, "queue_position", None)

                if is_cancelled:
                    user_enrollment_status = "cancelled"
                else:
                    user_enrollment_status = "reserve" if is_reserve else "main"

    free_places = max(capacity_main - occupied_main, 0)

    # --- price tiers ---
    tiers_payload: List[Dict[str, Any]] = []
    tiers = []
    if PriceTierModel is not None and training_id is not None:
        tiers = (
            db.query(PriceTierModel)
            .filter(getattr(PriceTierModel, "training_id") == training_id)
            .order_by(getattr(PriceTierModel, "sort_order", getattr(PriceTierModel, "id")))
            .all()
        )

        for t in tiers:
            tiers_payload.append(
                {
                    "id": getattr(t, "id", None),
                    "title": getattr(t, "title", None) or getattr(t, "name", None) or "Tier",
                    "price": float(getattr(t, "price", 0) or 0),
                    "level_id": getattr(t, "level_id", None),
                }
            )

    pick = pick_price_for_user(training, user, tiers)

    # can_enroll/can_enroll_reserve:
    # - can_enroll: есть место в основе
    # - can_enroll_reserve: основа заполнена, но резерв доступен
    is_reserve_available = capacity_reserve > occupied_reserve
    can_enroll = False
    can_enroll_reserve = False
    user_has_active_ban = False
    user_active_ban_reason: str | None = None
    user_active_ban_until = None
    user_active_ban_text: str | None = None
    if user is not None and user_enrollment_status in ("none", "", "cancelled", "canceled"):
        user_id = getattr(user, "id", None)
        if user_id is not None:
            active_ban = get_active_ban(db, int(user_id))
            user_has_active_ban = active_ban is not None
            if active_ban is not None:
                user_active_ban_reason = _safe_text(getattr(active_ban, "reason", None)) or None
                user_active_ban_until = getattr(active_ban, "until", None)
                user_active_ban_text = (
                    user_active_ban_reason
                    or _get_setting_value(
                        db,
                        "ban_text_default",
                        "У вас бан. Обратитесь к администратору.",
                    )
                )

        if not user_has_active_ban:
            can_enroll = free_places > 0
            can_enroll_reserve = (free_places <= 0) and is_reserve_available

    deadline = cancel_deadline_at(training)
    can_cancel = False
    if user is not None and user_enrollment_status not in ("none", "", "cancelled", "canceled"):
        can_cancel = True

    late_cancel = is_late_cancel(training)

    payload = {
        "occupied_main": occupied_main,
        "occupied_reserve": occupied_reserve,
        "free_places": free_places,
        "can_enroll": can_enroll,
        "can_enroll_reserve": can_enroll_reserve,
        "is_reserve_available": is_reserve_available,
        "user_has_active_ban": user_has_active_ban,
        "user_active_ban_reason": user_active_ban_reason,
        "user_active_ban_until": user_active_ban_until,
        "user_active_ban_text": user_active_ban_text,
        "user_enrollment_status": user_enrollment_status,
        "user_queue_position": user_queue_position,
        "user_enrollment_id": user_enrollment_id,
        "price_tiers": tiers_payload,
        "price_min": float(pick.price_min),
        "price_max": float(pick.price_max),
        "final_price": float(pick.final_price),
        "picked_price_tier_id": pick.picked_tier_id,
        "cancel_deadline_at": deadline.isoformat().replace("+00:00", "Z") if deadline else None,
        "is_late_cancel": late_cancel,
        "can_cancel": can_cancel,
    }

    if include_participants:
        payload["participants_main"] = participants_main
        payload["participants_reserve"] = participants_reserve
        payload["participants_total"] = len(participants_main) + len(participants_reserve)

    return payload
