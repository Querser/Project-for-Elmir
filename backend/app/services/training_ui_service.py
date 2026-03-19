from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.services.policies import cancel_deadline_at, pick_price_for_user, is_late_cancel
from app.models.setting import Setting
from app.models.level import Level
from app.schemas.training import CANONICAL_LEVEL_NAMES
from app.services.ban_service import get_active_ban
from app.services.training_service import (
    AMPLUA_TRAINING_TYPE,
    build_amplua_position_snapshot,
    get_amplua_position_meta,
    get_fixed_amplua_positions,
    normalize_training_type,
)

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


_LEVEL_ORDER = {name: idx for idx, name in enumerate(CANONICAL_LEVEL_NAMES)}


def _canonical_level_name(value: Any) -> str | None:
    raw = _safe_text(value).replace("−", "-")
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


def _resolve_user_level_name(db: Session, user: Any) -> str | None:
    direct = _canonical_level_name(getattr(getattr(user, "level", None), "name", None))
    if direct:
        return direct

    level_id = getattr(user, "level_id", None)
    if level_id is None:
        return None

    row = db.query(Level).filter(Level.id == int(level_id)).first()
    return _canonical_level_name(getattr(row, "name", None))


def _get_level_block_reason(db: Session, *, user: Any, training: Any) -> tuple[str | None, str | None]:
    min_level_name = _canonical_level_name(getattr(training, "min_level_name", None))
    max_level_name = _canonical_level_name(getattr(training, "max_level_name", None))

    user_level_name = _resolve_user_level_name(db, user)

    if min_level_name is None and max_level_name is None:
        return None, user_level_name

    required_min = min_level_name or CANONICAL_LEVEL_NAMES[0]
    required_max = max_level_name or CANONICAL_LEVEL_NAMES[-1]
    min_idx = _LEVEL_ORDER.get(required_min)
    max_idx = _LEVEL_ORDER.get(required_max)
    if min_idx is None or max_idx is None:
        return None, user_level_name

    if min_idx > max_idx:
        min_idx, max_idx = max_idx, min_idx
        required_min, required_max = required_max, required_min

    if user_level_name is None:
        return (
            "Вы не можете записаться: у вас не указан уровень игрока. Обратитесь к администратору.",
            None,
        )

    user_idx = _LEVEL_ORDER.get(user_level_name)
    if user_idx is None:
        return (
            "Вы не можете записаться: ваш уровень не распознан. Обратитесь к администратору.",
            user_level_name,
        )

    if user_idx < min_idx or user_idx > max_idx:
        required = required_min if required_min == required_max else f"{required_min} — {required_max}"
        return (
            f'Вы не можете записаться: ваш уровень "{user_level_name}" не соответствует требуемому "{required}".',
            user_level_name,
        )

    return None, user_level_name


def _get_setting_value(db: Session, key: str, default: str) -> str:
    try:
        row = db.query(Setting).filter(Setting.key == key).one_or_none()
    except Exception:
        return default
    if row is None:
        return default
    value = _safe_text(getattr(row, "value", None))
    return value or default


def _get_cancel_hours_before_training(db: Session) -> int:
    raw = _get_setting_value(db, "cancel_hours_before_training", "2")
    try:
        value = int(float(raw))
    except Exception:
        value = 2
    return max(0, min(value, 168))


def _participant_payload(enrollment: Any, *, is_reserve: bool) -> dict[str, Any]:
    user_obj = getattr(enrollment, "user", None)
    user_id = getattr(enrollment, "user_id", None)

    first_name = _safe_text(getattr(user_obj, "first_name", None))
    last_name = _safe_text(getattr(user_obj, "last_name", None))
    username = _safe_text(getattr(user_obj, "username", None))
    avatar_url = _safe_text(getattr(user_obj, "avatar_url", None))

    full_name = " ".join(x for x in (first_name, last_name) if x).strip()
    if not full_name and username:
        full_name = f"@{username}"
    if not full_name and user_id is not None:
        full_name = f"Игрок #{user_id}"

    level_name = _safe_text(getattr(getattr(user_obj, "level", None), "name", None))

    position_key = _safe_text(getattr(enrollment, "position_key", None)) or None
    position_meta = get_amplua_position_meta(position_key) if position_key else None
    canonical_position_key = (position_meta or {}).get("key") or position_key

    return {
        "enrollment_id": getattr(enrollment, "id", None),
        "user_id": user_id,
        "position_key": canonical_position_key,
        "position_slot_label": (position_meta or {}).get("label"),
        "position_label": (position_meta or {}).get("position_label"),
        "team_key": (position_meta or {}).get("team_key"),
        "team_label": (position_meta or {}).get("team_label"),
        "first_name": first_name or None,
        "last_name": last_name or None,
        "username": username or None,
        "avatar_url": avatar_url or None,
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
    training_type = normalize_training_type(getattr(training, "training_type", None))
    is_amplua = training_type == AMPLUA_TRAINING_TYPE

    capacity_main = int(getattr(training, "capacity_main", 0) or 0)
    capacity_reserve = int(getattr(training, "capacity_reserve", 0) or 0)

    occupied_main = 0
    occupied_reserve = 0
    user_enrollment_status = "none"
    user_queue_position = None
    user_enrollment_id: Optional[int] = None
    user_position_key: str | None = None
    user_position_label: str | None = None
    user_position_name: str | None = None
    user_position_team_key: str | None = None
    user_position_team_label: str | None = None
    amplua_position_slots: list[dict[str, Any]] = []
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
                position_key = _safe_text(getattr(e, "position_key", None))
                if position_key:
                    position_meta = get_amplua_position_meta(position_key)
                    if position_meta:
                        user_position_key = position_meta.get("key")
                        user_position_label = position_meta.get("label") or None
                        user_position_name = position_meta.get("position_label") or None
                        user_position_team_key = position_meta.get("team_key") or None
                        user_position_team_label = position_meta.get("team_label") or None
                    else:
                        user_position_key = position_key

                if is_cancelled:
                    user_enrollment_status = "cancelled"
                else:
                    user_enrollment_status = "reserve" if is_reserve else "main"

    if is_amplua:
        amplua_position_slots = build_amplua_position_snapshot(
            positions=getattr(training, "amplua_positions", None),
            enrollments=rows if EnrollmentModel is not None and training_id is not None else [],
        )
        occupied_main = sum(int(slot.get("occupied", 0) or 0) for slot in amplua_position_slots)
        capacity_main = sum(int(slot.get("capacity", 0) or 0) for slot in amplua_position_slots)
        free_places = sum(int(slot.get("free", 0) or 0) for slot in amplua_position_slots)
    else:
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
    user_level_name: str | None = None
    user_level_block_reason: str | None = None
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
            user_level_block_reason, user_level_name = _get_level_block_reason(db, user=user, training=training)
            if not user_level_block_reason:
                can_enroll = free_places > 0
                can_enroll_reserve = (free_places <= 0) and is_reserve_available
        else:
            user_level_name = _resolve_user_level_name(db, user)
    elif user is not None:
        user_level_name = _resolve_user_level_name(db, user)

    cancel_hours = _get_cancel_hours_before_training(db)
    deadline = cancel_deadline_at(training, cancel_hours=cancel_hours)
    can_cancel = False
    if user is not None and user_enrollment_status not in ("none", "", "cancelled", "canceled"):
        can_cancel = True

    late_cancel = is_late_cancel(training, cancel_hours=cancel_hours)
    position_slots_payload = amplua_position_slots
    available_positions = [slot for slot in position_slots_payload if slot.get("has_free_slots")]
    if is_amplua and can_enroll_reserve and not available_positions:
        # Для резерва ampLua разрешаем выбрать любую позицию, даже если в основе нет свободных слотов.
        position_slots_payload = [
            {
                **slot,
                "free": None,
            }
            for slot in amplua_position_slots
        ]
        available_positions = [
            {
                **slot,
                "free": None,
                "reserve_only": True,
            }
            for slot in position_slots_payload
        ]

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
        "user_level_name": user_level_name,
        "user_level_block_reason": user_level_block_reason,
        "user_enrollment_status": user_enrollment_status,
        "user_queue_position": user_queue_position,
        "user_enrollment_id": user_enrollment_id,
        "price_tiers": tiers_payload,
        "price_min": float(pick.price_min),
        "price_max": float(pick.price_max),
        "final_price": float(pick.final_price),
        "picked_price_tier_id": pick.picked_tier_id,
        "training_type": training_type,
        "amplua_positions": get_fixed_amplua_positions() if is_amplua else None,
        "position_slots": position_slots_payload,
        "available_positions": available_positions,
        "user_position_key": user_position_key,
        "user_position_label": user_position_label,
        "user_position_name": user_position_name,
        "user_position_team_key": user_position_team_key,
        "user_position_team_label": user_position_team_label,
        "cancel_deadline_at": deadline.isoformat().replace("+00:00", "Z") if deadline else None,
        "is_late_cancel": late_cancel,
        "can_cancel": can_cancel,
    }

    if include_participants:
        payload["participants_main"] = participants_main
        payload["participants_reserve"] = participants_reserve
        payload["participants_total"] = len(participants_main) + len(participants_reserve)

    return payload
