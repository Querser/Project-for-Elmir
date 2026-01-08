from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.policies import cancel_deadline_at, pick_price_for_user, is_late_cancel

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


def build_training_ui_payload(db: Session, training: Any, user: Any | None) -> Dict[str, Any]:
    training_id = getattr(training, "id", None)

    capacity_main = int(getattr(training, "capacity_main", 0) or 0)
    capacity_reserve = int(getattr(training, "capacity_reserve", 0) or 0)

    occupied_main = 0
    occupied_reserve = 0
    user_enrollment_status = "none"
    user_queue_position = None

    if EnrollmentModel is not None and training_id is not None:
        q = db.query(EnrollmentModel).filter(EnrollmentModel.training_id == training_id)

        rows: List[Any] = q.all()
        for e in rows:
            st = _status_value(getattr(e, "status", None)).lower()

            # максимально “толерантная” классификация, чтобы не сломаться на твоих enum-ах
            is_cancelled = "cancel" in st
            is_reserve = ("reserve" in st) or ("wait" in st) or bool(getattr(e, "is_reserve", False))

            if not is_cancelled:
                if is_reserve:
                    occupied_reserve += 1
                else:
                    occupied_main += 1

            if user is not None and getattr(e, "user_id", None) == getattr(user, "id", None):
                # статус для UI (если есть)
                user_enrollment_status = st or "enrolled"
                user_queue_position = getattr(e, "queue_position", None)

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

    # can_enroll: НЕ ломаем поведение — если нет user → False
    can_enroll = False
    if user is not None and user_enrollment_status in ("none", "", "cancelled", "canceled"):
        can_enroll = free_places > 0 or capacity_reserve > occupied_reserve

    deadline = cancel_deadline_at(training)
    can_cancel = False
    if user is not None and user_enrollment_status not in ("none", "", "cancelled", "canceled"):
        # если поздно — can_cancel всё равно True, но UI покажет что будет штраф (см. флаг)
        can_cancel = True

    late_cancel = is_late_cancel(training)

    return {
        "occupied_main": occupied_main,
        "occupied_reserve": occupied_reserve,
        "free_places": free_places,
        "can_enroll": can_enroll,
        "user_enrollment_status": user_enrollment_status,
        "user_queue_position": user_queue_position,
        # price tiers UI
        "price_tiers": tiers_payload,
        "price_min": float(pick.price_min),
        "price_max": float(pick.price_max),
        "final_price": float(pick.final_price),
        "picked_price_tier_id": pick.picked_tier_id,
        # cancel policy UI hints
        "cancel_deadline_at": deadline.isoformat().replace("+00:00", "Z") if deadline else None,
        "is_late_cancel": late_cancel,
        "can_cancel": can_cancel,
    }
