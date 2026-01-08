from __future__ import annotations

from typing import Any, Optional, Tuple

from app.schemas.training_ui import TrainingReadUI


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        for n in names:
            if n in obj:
                return obj.get(n)
        return default
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


def _to_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _try_get_roster(db: Any, training_id: Any) -> Tuple[Optional[list], Optional[list]]:
    """
    Пытаемся использовать существующий get_training_roster (как в enrollments endpoint).
    Если не нашли — вернём (None, None) и посчитаем по-минимуму.
    """
    for path in (
        "app.services.enrollment_service",
        "app.services.enrollments_service",
        "app.services.enrollment",
        "app.services.enrollments",
    ):
        try:
            mod = __import__(path, fromlist=["get_training_roster"])
            fn = getattr(mod, "get_training_roster", None)
            if fn:
                main, reserve = fn(db, training_id)
                return list(main or []), list(reserve or [])
        except Exception:
            continue
    return None, None


def build_training_ui_payload(db: Any, training: Any, current_user: Any = None) -> TrainingReadUI:
    """
    Собирает TrainingReadUI из ORM/dict + вычисляет UI-поля.
    Ничего не ломает: если часть данных неизвестна — отдаём дефолты.
    """
    training_id = _get(training, "id", default=None)

    # вместимости (под разные названия полей)
    cap_main = _to_int(_get(training, "capacity_main", "main_capacity", "max_players", "players_limit", default=0), 0)
    cap_res = _to_int(_get(training, "capacity_reserve", "reserve_capacity", "reserve_limit", default=0), 0)

    # занятость: пробуем реальный roster
    main_roster, reserve_roster = _try_get_roster(db, training_id)
    occupied_main = len(main_roster) if main_roster is not None else 0
    occupied_reserve = len(reserve_roster) if reserve_roster is not None else 0

    free_places = max(0, cap_main - occupied_main)

    # статус пользователя (если можем определить)
    user_status = "unknown"
    can_enroll = free_places > 0

    try:
        user_id = _get(current_user, "id", "user_id", default=None)
        if user_id is not None and main_roster is not None and reserve_roster is not None:
            def _roster_has(roster: list) -> bool:
                for x in roster:
                    if _get(x, "id", "user_id", default=None) == user_id:
                        return True
                return False

            if _roster_has(main_roster):
                user_status = "main"
                can_enroll = False
            elif _roster_has(reserve_roster):
                user_status = "reserve"
                can_enroll = False
            else:
                user_status = "none"
                can_enroll = free_places > 0
    except Exception:
        pass

    payload = {
        "id": training_id,
        "starts_at": _get(training, "starts_at", "start_at", "start_time", "datetime", default=None),
        "ends_at": _get(training, "ends_at", "end_at", "end_time", default=None),
        "title": _get(training, "title", "name", default=None),
        "location": _get(training, "location", "place", default=None),
        "price": _get(training, "price", "cost", default=None),
        "capacity_main": cap_main,
        "capacity_reserve": cap_res,
        "free_places": free_places,
        "occupied_main": occupied_main,
        "occupied_reserve": occupied_reserve,
        "can_enroll": bool(can_enroll),
        "user_enrollment_status": user_status,
    }

    # если training — ORM, extra='allow' пропустит доп поля, но нам достаточно payload
    return TrainingReadUI.model_validate(payload)
