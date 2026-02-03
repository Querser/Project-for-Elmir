# backend/tools/seed_demo_data.py
"""
Seeder for development/demo environment.

What it creates (idempotent, careful):
- Locations (even if Location model has only `id`)
- Demo users (with telegram_id + username)
- Trainings for demo locations
- Notifications for ALL users (so the currently-authenticated dev user sees them)

Safe behavior:
- Does NOT delete existing data
- Skips objects that already exist by stable keys
- Uses SQLAlchemy model inspection to avoid breaking when column names differ
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable, Optional

sys.path.append("/app")

from sqlalchemy import inspect as sa_inspect

from app.db.session import SessionLocal
from app.models.location import Location
from app.models.notification import Notification
from app.models.training import Training
from app.models.user import User

# Optional: levels (if your Training uses min_level_id/max_level_id)
try:
    from app.models.level import Level  # type: ignore
except Exception:
    Level = None  # type: ignore


# -------------------- helpers -------------------- #
def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _next_weekday_at(hour: int, minute: int, weekday: int) -> datetime:
    """
    Returns datetime at (hour:minute) UTC for the next given weekday.
    weekday: 0=Mon ... 6=Sun
    """
    now = _now_utc()
    days_ahead = (weekday - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (now + timedelta(days=days_ahead)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )


def _model_columns(model: Any) -> dict[str, Any]:
    return {c.key: c for c in sa_inspect(model).columns}


def _pick_col(model: Any, candidates: list[str], *, required: bool = False) -> Optional[str]:
    cols = _model_columns(model)
    for c in candidates:
        if c in cols:
            return c
    if required:
        raise RuntimeError(
            f"{model.__name__}: не найдено ни одной колонки из {candidates}. "
            f"Доступные колонки: {sorted(cols.keys())}"
        )
    return None


def _set_if_hascol(obj: Any, colname: Optional[str], value: Any) -> None:
    if colname and hasattr(obj, colname):
        setattr(obj, colname, value)


def _coerce_dt_for_model(model: Any, colname: str, dt_utc: datetime) -> datetime:
    """
    If DB column is timezone-aware -> keep tz-aware UTC.
    If not -> store naive UTC (tzinfo removed).
    """
    cols = _model_columns(model)
    col = cols.get(colname)
    if col is not None and hasattr(col.type, "timezone"):
        if getattr(col.type, "timezone", False):
            return dt_utc
        return dt_utc.replace(tzinfo=None)
    return dt_utc.replace(tzinfo=None)


def _safe_username(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("@"):
        s = s[1:]
    return s


def _split_full_name(full_name: str) -> tuple[str, str]:
    full_name = (full_name or "").strip()
    if not full_name:
        return ("Демо", "Пользователь")
    parts = [p for p in full_name.split(" ") if p]
    if len(parts) == 1:
        return (parts[0], "")
    return (parts[0], " ".join(parts[1:]))


def _normalize_phone_if_possible(raw_phone: str) -> Optional[str]:
    raw_phone = (raw_phone or "").strip()
    if not raw_phone:
        return None
    try:
        from app.services.user_service import normalize_phone  # local import

        return normalize_phone(raw_phone)
    except Exception:
        return raw_phone


def _enum_allowed_values(model: Any, colname: str) -> Optional[list[str]]:
    cols = _model_columns(model)
    col = cols.get(colname)
    if col is None:
        return None
    t = col.type
    enums = getattr(t, "enums", None)
    if isinstance(enums, (list, tuple)) and enums:
        return [str(x) for x in enums]
    return None


def _pick_enum_value(preferred: str, allowed: Optional[list[str]]) -> str:
    if not allowed:
        return preferred
    if preferred in allowed:
        return preferred
    for v in allowed:
        if v.lower() == preferred.lower():
            return v
    return allowed[0]


def _nn_str(s: Optional[str]) -> str:
    """Non-null string for NOT NULL DB columns."""
    return (s or "").strip()


def _autofill_required_simple(obj: Any, model: Any, *, now_utc: Optional[datetime] = None) -> None:
    """
    Подстраховка от NOT NULL колонок, которые появились в модели/схеме,
    но не покрыты сидером. Заполняем только безопасные типы: str/bool/datetime.
    """
    now_utc = now_utc or _now_utc()
    cols = _model_columns(model)

    for name, col in cols.items():
        if getattr(col, "primary_key", False):
            continue
        if getattr(col, "nullable", True):
            continue
        if getattr(col, "default", None) is not None or getattr(col, "server_default", None) is not None:
            continue

        # Уже заполнено
        if hasattr(obj, name) and getattr(obj, name, None) is not None:
            continue

        # Пытаемся определить python_type
        try:
            py_t = col.type.python_type
        except Exception:
            continue

        if py_t is str:
            setattr(obj, name, "")
        elif py_t is bool:
            setattr(obj, name, False)
        elif py_t is datetime:
            setattr(obj, name, _coerce_dt_for_model(model, name, now_utc))


# -------------------- demo data -------------------- #
DEMO_LOCATIONS = [
    {"name": "Зал на Невском (демо)", "address": "Санкт-Петербург, Невский пр., 1"},
    {"name": "Площадка у парка (демо)", "address": "Санкт-Петербург, Парковая ул., 10"},
]

DEMO_USERS = [
    {
        "telegram_id": 123456789,
        "username": "test_user",
        "full_name": "Тестовый Игрок",
        "phone": "+79990000000",
        "role": "user",
        "is_active": True,
        "is_telegram_public": True,
    },
    {
        "telegram_id": 123456790,
        "username": "demo_player_1",
        "full_name": "Демо Игрок 1",
        "phone": "+79990000001",
        "role": "user",
        "is_active": True,
        "is_telegram_public": True,
    },
    {
        "telegram_id": 123456791,
        "username": "demo_player_2",
        "full_name": "Демо Игрок 2",
        "phone": "+79990000002",
        "role": "user",
        "is_active": True,
        "is_telegram_public": True,
    },
    {
        "telegram_id": 999000111,
        "username": "admin_demo",
        "full_name": "Админ Демо",
        "phone": "+79990000999",
        "role": "admin",
        "is_active": True,
        "is_telegram_public": True,
    },
]


# -------------------- seeders -------------------- #
def seed_locations(db) -> list[Location]:
    """
    If Location has name/title/address columns -> seed by those.
    If Location has only `id` -> just ensure N rows exist and return first N.
    """
    created_or_existing: list[Location] = []

    loc_name_col = _pick_col(Location, ["name", "title", "location_name"], required=False)
    loc_address_col = _pick_col(Location, ["address", "addr", "location_address"], required=False)
    loc_is_active_col = _pick_col(Location, ["is_active", "active", "enabled"], required=False)

    need_n = max(1, len(DEMO_LOCATIONS))

    # Fallback: Location model without any meaningful columns besides id
    if not loc_name_col and not loc_address_col:
        existing = db.query(Location).order_by(getattr(Location, "id")).all()
        if len(existing) < need_n:
            for _ in range(need_n - len(existing)):
                loc = Location()
                _set_if_hascol(loc, loc_is_active_col, True)
                _autofill_required_simple(loc, Location)
                db.add(loc)
                db.flush()
                existing.append(loc)
        return existing[:need_n]

    for item in DEMO_LOCATIONS:
        name_val = item.get("name")
        address_val = item.get("address")

        loc = None
        if loc_name_col and name_val:
            loc = db.query(Location).filter(getattr(Location, loc_name_col) == name_val).first()

        if loc is None and loc_address_col and address_val:
            loc = db.query(Location).filter(getattr(Location, loc_address_col) == address_val).first()

        if loc is None:
            kwargs: dict[str, Any] = {}
            if loc_name_col and name_val:
                kwargs[loc_name_col] = name_val
            if loc_address_col and address_val:
                kwargs[loc_address_col] = address_val
            loc = Location(**kwargs)
            _set_if_hascol(loc, loc_is_active_col, True)
            _autofill_required_simple(loc, Location)
            db.add(loc)
            db.flush()

        created_or_existing.append(loc)

    return created_or_existing


def _load_levels_map(db) -> dict[str, int]:
    if Level is None:
        return {}

    name_col = _pick_col(Level, ["name", "title"], required=False)
    id_col = _pick_col(Level, ["id"], required=True)
    if not name_col:
        return {}

    levels = db.query(Level).all()
    out: dict[str, int] = {}
    for lv in levels:
        key = getattr(lv, name_col, None)
        if key:
            out[str(key)] = int(getattr(lv, id_col))
    return out


def seed_users(db) -> list[User]:
    created_or_existing: list[User] = []

    tg_id_col = _pick_col(User, ["telegram_id", "tg_id", "telegramId"], required=True)
    username_col = _pick_col(User, ["username", "telegram_username", "tg_username", "login"], required=False)
    first_name_col = _pick_col(User, ["first_name", "firstname", "name"], required=False)
    last_name_col = _pick_col(User, ["last_name", "lastname", "surname"], required=False)
    phone_col = _pick_col(User, ["phone", "phone_number", "tel", "mobile"], required=False)

    role_col = _pick_col(User, ["role", "user_role"], required=False)
    role_allowed = _enum_allowed_values(User, role_col) if role_col else None

    is_admin_col = _pick_col(User, ["is_admin", "admin"], required=False)
    is_active_col = _pick_col(User, ["is_active", "active", "enabled"], required=False)
    is_tg_public_col = _pick_col(User, ["is_telegram_public", "telegram_public", "tg_public"], required=False)

    for u in DEMO_USERS:
        tg_id = int(u["telegram_id"])
        username = _safe_username(u.get("username") or "")
        first_name, last_name = _split_full_name(u.get("full_name") or "")
        phone = _normalize_phone_if_possible(u.get("phone") or "")
        preferred_role = str(u.get("role") or "user")
        role_value = _pick_enum_value(preferred_role, role_allowed) if role_col else preferred_role

        user = db.query(User).filter(getattr(User, tg_id_col) == tg_id).first()
        if user is None:
            kwargs: dict[str, Any] = {tg_id_col: tg_id}

            if username_col:
                # если username NOT NULL — подставим безопасное значение
                kwargs[username_col] = username or f"demo_{tg_id}"
            if first_name_col:
                kwargs[first_name_col] = (first_name or "Демо")
            if last_name_col:
                kwargs[last_name_col] = (last_name or "Пользователь")
            if phone_col and phone:
                kwargs[phone_col] = phone

            user = User(**kwargs)

            if is_active_col:
                setattr(user, is_active_col, bool(u.get("is_active", True)))
            if is_tg_public_col:
                setattr(user, is_tg_public_col, bool(u.get("is_telegram_public", True)))

            if role_col:
                setattr(user, role_col, role_value)
            if is_admin_col:
                setattr(user, is_admin_col, preferred_role.lower() == "admin")

            _autofill_required_simple(user, User)

            db.add(user)
            db.flush()
        else:
            if username_col:
                cur = getattr(user, username_col, None)
                if (cur in (None, "")) and (username or tg_id):
                    setattr(user, username_col, username or f"demo_{tg_id}")

            if first_name_col:
                cur = getattr(user, first_name_col, None)
                if cur in (None, "") and first_name:
                    setattr(user, first_name_col, first_name or "Демо")

            if last_name_col:
                cur = getattr(user, last_name_col, None)
                if cur in (None, "") and (last_name or first_name):
                    setattr(user, last_name_col, last_name or "Пользователь")

            if phone_col and phone:
                cur = getattr(user, phone_col, None)
                if cur in (None, ""):
                    setattr(user, phone_col, phone)

            if is_active_col:
                setattr(user, is_active_col, True)
            if is_tg_public_col:
                setattr(user, is_tg_public_col, True)

            if role_col:
                cur = getattr(user, role_col, None)
                if cur in (None, ""):
                    setattr(user, role_col, role_value)
            if is_admin_col:
                setattr(user, is_admin_col, preferred_role.lower() == "admin")

            _autofill_required_simple(user, User)

        created_or_existing.append(user)

    return created_or_existing


def seed_trainings(db, locations: list[Location]) -> None:
    title_col = _pick_col(Training, ["title", "name"], required=True)
    desc_col = _pick_col(Training, ["description", "details", "text", "body"], required=False)
    start_col = _pick_col(Training, ["start_at", "starts_at", "start_time", "start_datetime"], required=True)
    duration_col = _pick_col(Training, ["duration_minutes", "duration", "duration_min"], required=False)
    price_col = _pick_col(Training, ["price", "cost"], required=False)
    cap_main_col = _pick_col(Training, ["capacity_main", "capacity", "capacity_total", "slots"], required=False)
    cap_res_col = _pick_col(
        Training, ["capacity_reserve", "reserve_capacity", "capacity_waitlist", "waitlist_slots"], required=False
    )
    coach_col = _pick_col(Training, ["coach_name", "coach", "trainer_name", "trainer"], required=False)
    image_col = _pick_col(Training, ["image_url", "image", "poster_url", "cover_url"], required=False)
    video_col = _pick_col(Training, ["video_url", "video", "video_link"], required=False)
    location_id_col = _pick_col(Training, ["location_id", "place_id"], required=True)
    is_cancelled_col = _pick_col(Training, ["is_cancelled", "is_canceled", "canceled"], required=False)
    is_active_col = _pick_col(Training, ["is_active", "active", "enabled"], required=False)

    min_level_id_col = _pick_col(Training, ["min_level_id"], required=False)
    max_level_id_col = _pick_col(Training, ["max_level_id"], required=False)
    min_level_name_col = _pick_col(Training, ["min_level_name"], required=False)
    max_level_name_col = _pick_col(Training, ["max_level_name"], required=False)

    levels_map = _load_levels_map(db) if (min_level_id_col or max_level_id_col) else {}

    start_mon = _next_weekday_at(19, 0, weekday=0)  # Monday
    start_wed = _next_weekday_at(18, 0, weekday=2)  # Wednesday
    start_thu = _next_weekday_at(19, 30, weekday=3)  # Thursday

    loc1 = locations[0]
    loc2 = locations[1] if len(locations) > 1 else locations[0]

    trainings_data = [
        {
            "title": "Тренировка новичков (демо)",
            "description": "Тренировка для начинающих с упором на базовую технику.",
            "start_at": start_mon,
            "duration_minutes": 90,
            "price": Decimal("350.00"),
            "capacity_main": 12,
            "capacity_reserve": 6,
            "coach_name": "Тренер Демо",
            "min_level_name": "Beginner",
            "max_level_name": "Intermediate",
            "image_url": None,
            "video_url": None,
            "location_id": int(getattr(loc1, "id")),
            "is_cancelled": False,
        },
        {
            "title": "Продвинутая техника (демо)",
            "description": "Работа над техникой и тактикой.",
            "start_at": start_wed,
            "duration_minutes": 90,
            "price": Decimal("450.00"),
            "capacity_main": 12,
            "capacity_reserve": 6,
            "coach_name": "Тренер Демо",
            "min_level_name": "Intermediate",
            "max_level_name": "Advanced",
            "image_url": None,
            "video_url": None,
            "location_id": int(getattr(loc2, "id")),
            "is_cancelled": False,
        },
        {
            "title": "Спарринги (демо)",
            "description": "Игровая практика и разбор ошибок.",
            "start_at": start_thu,
            "duration_minutes": 120,
            "price": Decimal("550.00"),
            "capacity_main": 16,
            "capacity_reserve": 8,
            "coach_name": "Тренер Демо",
            "min_level_name": "Intermediate",
            "max_level_name": "Advanced",
            "image_url": None,
            "video_url": None,
            "location_id": int(getattr(loc1, "id")),
            "is_cancelled": False,
        },
        {
            "title": "Отменённая тренировка (демо)",
            "description": "Нужна, чтобы проверить UI статуса отмены.",
            "start_at": start_thu + timedelta(days=2),
            "duration_minutes": 90,
            "price": Decimal("400.00"),
            "capacity_main": 12,
            "capacity_reserve": 6,
            "coach_name": "Тренер Демо",
            "min_level_name": None,
            "max_level_name": None,
            "image_url": None,
            "video_url": None,
            "location_id": int(getattr(loc2, "id")),
            "is_cancelled": True,
        },
    ]

    for t in trainings_data:
        title_val = t["title"]
        start_val = _coerce_dt_for_model(Training, start_col, t["start_at"])

        exists = (
            db.query(Training)
            .filter(getattr(Training, title_col) == title_val)
            .filter(getattr(Training, start_col) == start_val)
            .first()
            is not None
        )
        if exists:
            continue

        kwargs: dict[str, Any] = {
            title_col: title_val,
            start_col: start_val,
            location_id_col: t["location_id"],
        }

        if desc_col:
            kwargs[desc_col] = t["description"]
        if duration_col:
            kwargs[duration_col] = t["duration_minutes"]
        if price_col:
            kwargs[price_col] = t["price"]
        if cap_main_col:
            kwargs[cap_main_col] = t["capacity_main"]
        if cap_res_col:
            kwargs[cap_res_col] = t["capacity_reserve"]
        if coach_col:
            kwargs[coach_col] = t["coach_name"]
        if image_col:
            kwargs[image_col] = t["image_url"]
        if video_col:
            kwargs[video_col] = t["video_url"]

        min_name = t.get("min_level_name")
        max_name = t.get("max_level_name")

        if min_level_id_col and min_name and min_name in levels_map:
            kwargs[min_level_id_col] = levels_map[min_name]
        elif min_level_name_col:
            kwargs[min_level_name_col] = min_name

        if max_level_id_col and max_name and max_name in levels_map:
            kwargs[max_level_id_col] = levels_map[max_name]
        elif max_level_name_col:
            kwargs[max_level_name_col] = max_name

        tr = Training(**kwargs)

        if is_cancelled_col:
            setattr(tr, is_cancelled_col, bool(t["is_cancelled"]))
        if is_active_col:
            setattr(tr, is_active_col, True)

        _autofill_required_simple(tr, Training)

        db.add(tr)


def seed_notifications(db, users: Iterable[User]) -> None:
    """
    Creates a couple of INFO notifications + one TRAINING notification
    for each user. Idempotent (won't duplicate same messages).

    IMPORTANT: гарантируем заполнение NOT NULL полей (type/title/body/text),
    чтобы не было ошибок вида:
    - null value in column "type" violates not-null constraint
    - null value in column "body" violates not-null constraint
    """
    now = _now_utc()

    notif_cols = _model_columns(Notification)

    user_id_col = _pick_col(Notification, ["user_id", "recipient_id", "to_user_id"], required=True)

    # type/title — в твоей схеме NOT NULL, поэтому стараемся взять их явно
    type_col = "type" if "type" in notif_cols else _pick_col(
        Notification, ["type", "kind", "notification_type"], required=False
    )
    title_col = _pick_col(Notification, ["title", "subject", "header"], required=True)

    # Текстовые поля: в твоей модели NOT NULL body + text
    text_field_candidates = ["body", "text", "message", "content"]
    text_cols = [c for c in text_field_candidates if c in notif_cols]

    if not text_cols:
        raise RuntimeError(
            f"{Notification.__name__}: не найдено ни одной колонки для текста уведомления "
            f"(ожидалось одно из {text_field_candidates}). Доступные: {sorted(notif_cols.keys())}"
        )

    # Для проверки дублей лучше использовать "text", если он есть (у тебя он есть)
    dedupe_text_col = "text" if "text" in text_cols else text_cols[0]

    is_read_col = _pick_col(Notification, ["is_read", "read", "seen"], required=False)
    created_at_col = _pick_col(Notification, ["created_at", "created", "created_on"], required=False)

    entity_type_col = _pick_col(Notification, ["entity_type"], required=False)
    entity_id_col = _pick_col(Notification, ["entity_id"], required=False)
    url_col = _pick_col(Notification, ["url", "link", "href"], required=False)

    # Allowed enum values (если когда-нибудь станет Enum)
    type_allowed = _enum_allowed_values(Notification, type_col) if type_col else None
    info_type = _pick_enum_value("INFO", type_allowed)
    training_type = _pick_enum_value("TRAINING", type_allowed)

    # pick a training to link (if any)
    training_id_col = _pick_col(Training, ["id"], required=False)
    training_start_col = _pick_col(
        Training, ["start_at", "starts_at", "start_time", "start_datetime"], required=False
    )

    training_id: Optional[int] = None
    if training_id_col:
        q = db.query(Training)
        if training_start_col:
            q = q.order_by(getattr(Training, training_start_col).asc())
        else:
            q = q.order_by(getattr(Training, training_id_col).desc())
        tr = q.first()
        if tr is not None:
            training_id = int(getattr(tr, training_id_col))

    templates_info = [
        ("Добро пожаловать!", "Это тестовое уведомление. Оно должно быть видно в приложении."),
        ("Напоминание", "Проверь переход в Telegram из профиля игрока."),
    ]

    def _build_kwargs(uid: int, title: str, msg: str, ntype: str) -> dict[str, Any]:
        msg_nn = _nn_str(msg)
        title_nn = _nn_str(title) or "Уведомление"

        kwargs: dict[str, Any] = {
            user_id_col: uid,
            title_col: title_nn,
        }

        # Гарантированно заполняем все найденные текстовые колонки (body/text/...)
        for c in text_cols:
            kwargs[c] = msg_nn

        # Гарантированно проставляем type, если колонка есть
        if type_col:
            kwargs[type_col] = ntype

        return kwargs

    for user in users:
        uid = int(getattr(user, "id"))

        # INFO notifications
        for idx, (title, msg) in enumerate(templates_info, start=1):
            exists = (
                db.query(Notification)
                .filter(getattr(Notification, user_id_col) == uid)
                .filter(getattr(Notification, title_col) == title)
                .filter(getattr(Notification, dedupe_text_col) == _nn_str(msg))
                .first()
                is not None
            )
            if exists:
                continue

            kwargs = _build_kwargs(uid, title, msg, info_type)
            n = Notification(**kwargs)

            if is_read_col:
                setattr(n, is_read_col, False)

            if created_at_col:
                setattr(
                    n,
                    created_at_col,
                    _coerce_dt_for_model(Notification, created_at_col, now - timedelta(hours=idx)),
                )

            _autofill_required_simple(n, Notification, now_utc=now)
            db.add(n)

        # TRAINING notification
        title = "Тренировка завтра"
        msg = "Не забудь: завтра тренировка! Проверь расписание."

        exists_tr = (
            db.query(Notification)
            .filter(getattr(Notification, user_id_col) == uid)
            .filter(getattr(Notification, title_col) == title)
            .filter(getattr(Notification, dedupe_text_col) == _nn_str(msg))
            .first()
            is not None
        )
        if exists_tr:
            continue

        kwargs = _build_kwargs(uid, title, msg, training_type)
        n = Notification(**kwargs)

        if entity_type_col:
            setattr(n, entity_type_col, "training")
        if entity_id_col and training_id is not None:
            setattr(n, entity_id_col, training_id)
        if url_col and training_id is not None:
            setattr(n, url_col, f"/trainings/{training_id}")

        if is_read_col:
            setattr(n, is_read_col, False)
        if created_at_col:
            setattr(
                n,
                created_at_col,
                _coerce_dt_for_model(Notification, created_at_col, now - timedelta(minutes=30)),
            )

        _autofill_required_simple(n, Notification, now_utc=now)
        db.add(n)


def main() -> None:
    with SessionLocal() as db:
        try:
            locations = seed_locations(db)
            demo_users = seed_users(db)

            seed_trainings(db, locations)
            db.flush()

            # IMPORTANT: add notifications for ALL users in DB (so current dev-auth user sees them)
            all_users = db.query(User).all()
            seed_notifications(db, all_users)

            db.commit()
            print("✅ seed_demo_data: данные успешно добавлены в БД")
            print("📍 Локации:")
            for loc in locations:
                print(f"   - id={getattr(loc, 'id', None)}")
            print("👤 Демо-пользователи (telegram_id / username):")
            for u in demo_users:
                uname = getattr(u, "username", None) or getattr(u, "telegram_username", None) or ""
                print(f"   - {getattr(u, 'telegram_id', None)} / @{uname}")
            print(f"🔔 Уведомления: добавлены для пользователей = {len(all_users)}")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()