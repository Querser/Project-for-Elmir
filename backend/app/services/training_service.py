from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional, Sequence, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ErrorCode
from app.models.location import Location
from app.models.training import Training
from app.schemas.training import CANONICAL_LEVEL_NAMES, TrainingCreate, TrainingUpdate

_LEVEL_ORDER = {name: idx for idx, name in enumerate(CANONICAL_LEVEL_NAMES)}

AMPLUA_TRAINING_TYPE = "амплуа"
_AMPLUA_TEAMS: tuple[dict[str, str], ...] = (
    {"key": "team_1", "label": "Team 1"},
    {"key": "team_2", "label": "Team 2"},
)
_AMPLUA_TEAM_POSITIONS: tuple[dict[str, str], ...] = (
    {"key": "outside", "label": "доигровка"},
    {"key": "middle", "label": "ЦБ"},
    {"key": "setter", "label": "связка"},
    {"key": "opposite", "label": "диагональный"},
    {"key": "libero", "label": "либеро"},
)

_AMPLUA_MAIN_STATUSES = {"active", "enrolled", "confirmed"}
_AMPLUA_RESERVED_STATUSES = {"reserve", "waitlist", "standby"}


def _build_amplua_position_specs() -> tuple[dict[str, str], ...]:
    specs: list[dict[str, str]] = []
    for team in _AMPLUA_TEAMS:
        for position in _AMPLUA_TEAM_POSITIONS:
            key = f'{team["key"]}_{position["key"]}'
            specs.append(
                {
                    "key": key,
                    "label": f'{team["label"]} · {position["label"]}',
                    "team_key": team["key"],
                    "team_label": team["label"],
                    "position_key": position["key"],
                    "position_label": position["label"],
                }
            )
    return tuple(specs)


AMPLUA_POSITION_SPECS = _build_amplua_position_specs()
_AMPLUA_SPECS_BY_KEY: dict[str, dict[str, str]] = {spec["key"]: spec for spec in AMPLUA_POSITION_SPECS}
_AMPLUA_LEGACY_KEY_ALIASES: dict[str, str] = {
    # Backward compatibility for old keys:
    # doigrovka/ЦБ were historically encoded as *_1/*_2 without explicit team,
    # now they map to Team 1 / Team 2 respectively.
    "outside_1": "team_1_outside",
    "outside_2": "team_2_outside",
    "middle_1": "team_1_middle",
    "middle_2": "team_2_middle",
    "setter": "team_1_setter",
    "opposite": "team_1_opposite",
    "libero": "team_1_libero",
    "outside": "team_1_outside",
    "middle": "team_1_middle",
    # Tolerant aliases that can come from external clients.
    "team1_outside": "team_1_outside",
    "team1_middle": "team_1_middle",
    "team1_setter": "team_1_setter",
    "team1_opposite": "team_1_opposite",
    "team1_libero": "team_1_libero",
    "team2_outside": "team_2_outside",
    "team2_middle": "team_2_middle",
    "team2_setter": "team_2_setter",
    "team2_opposite": "team_2_opposite",
    "team2_libero": "team_2_libero",
}


def _amplua_slots_per_team(position_key: str) -> int:
    key = str(position_key or "").strip().lower()
    # Fixed business rules:
    # - доигровка/outside and ЦБ/middle: 1 slot per team
    # - every other position: 2 slots per team
    if key in {"outside", "middle"}:
        return 1
    return 2


_AMPLUA_DEFAULT_POSITIONS: dict[str, int] = {
    spec["key"]: _amplua_slots_per_team(spec["position_key"])
    for spec in AMPLUA_POSITION_SPECS
}


def normalize_training_type(value: Any) -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    if raw in {AMPLUA_TRAINING_TYPE, "amplua"}:
        return AMPLUA_TRAINING_TYPE
    if raw in {"обычная", "standard", "regular", "default"}:
        return None
    return raw


def is_amplua_training(training: Any) -> bool:
    return normalize_training_type(getattr(training, "training_type", training)) == AMPLUA_TRAINING_TYPE


def normalize_amplua_position_key(position_key: str | None) -> str | None:
    raw = str(position_key or "").strip().lower()
    if not raw:
        return None
    normalized = raw.replace("-", "_")
    if normalized in _AMPLUA_SPECS_BY_KEY:
        return normalized
    return _AMPLUA_LEGACY_KEY_ALIASES.get(normalized)


def get_fixed_amplua_positions() -> dict[str, int]:
    return dict(_AMPLUA_DEFAULT_POSITIONS)


def normalize_amplua_positions(value: Any) -> dict[str, int]:
    raw = value if isinstance(value, dict) else {}
    normalized: dict[str, int] = {spec["key"]: 0 for spec in AMPLUA_POSITION_SPECS}
    for raw_key, raw_value in raw.items():
        key = normalize_amplua_position_key(str(raw_key))
        if not key:
            continue
        try:
            count = int(float(raw_value))
        except Exception:
            count = 0
        normalized[key] = max(normalized.get(key, 0), max(0, count))
    return normalized


def amplua_capacity_main(value: Any) -> int:
    positions = normalize_amplua_positions(value)
    return int(sum(max(0, int(v)) for v in positions.values()))


def amplua_capacity_reserve(value: Any) -> int:
    # Reserve capacity mirrors static main capacity for ampLua rules.
    return amplua_capacity_main(value)


def normalize_media_url(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_media_url_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        source = list(value)
    else:
        source = [value]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in source:
        url = normalize_media_url(item)
        if not url or url in seen:
            continue
        normalized.append(url)
        seen.add(url)
    return normalized


def merge_image_gallery(
    *,
    image_url: Any,
    image_urls: Any,
) -> tuple[str | None, list[str] | None]:
    primary = normalize_media_url(image_url)
    gallery = normalize_media_url_list(image_urls)

    if primary:
        gallery = [primary] + [url for url in gallery if url != primary]
    elif gallery:
        primary = gallery[0]

    return primary, (gallery or None)


def get_amplua_position_label(position_key: str | None) -> str:
    meta = get_amplua_position_meta(position_key)
    if meta:
        return meta["label"]
    return ""


def get_amplua_position_meta(position_key: str | None) -> dict[str, str] | None:
    key = normalize_amplua_position_key(position_key)
    if not key:
        return None
    spec = _AMPLUA_SPECS_BY_KEY.get(key)
    if spec:
        return dict(spec)
    return None


def build_amplua_position_snapshot(
    *,
    positions: Any,
    enrollments: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    capacities = get_fixed_amplua_positions()
    occupied_main: dict[str, int] = {spec["key"]: 0 for spec in AMPLUA_POSITION_SPECS}
    occupied_reserve: dict[str, int] = {spec["key"]: 0 for spec in AMPLUA_POSITION_SPECS}

    for enrollment in enrollments or []:
        status = str(getattr(getattr(enrollment, "status", None), "value", getattr(enrollment, "status", "")) or "").strip().lower()
        position_key = normalize_amplua_position_key(getattr(enrollment, "position_key", None))
        if not position_key:
            continue
        if status in _AMPLUA_MAIN_STATUSES:
            occupied_main[position_key] = occupied_main.get(position_key, 0) + 1
        elif status in _AMPLUA_RESERVED_STATUSES:
            occupied_reserve[position_key] = occupied_reserve.get(position_key, 0) + 1

    snapshot: list[dict[str, Any]] = []
    for spec in AMPLUA_POSITION_SPECS:
        key = spec["key"]
        capacity_main = capacities.get(key, 0)
        capacity_reserve = capacities.get(key, 0)
        used_main = occupied_main.get(key, 0)
        used_reserve = occupied_reserve.get(key, 0)
        free_main = max(capacity_main - used_main, 0)
        free_reserve = max(capacity_reserve - used_reserve, 0)
        snapshot.append(
            {
                "key": key,
                "label": spec["label"],
                "team_key": spec["team_key"],
                "team_label": spec["team_label"],
                "position_key": spec["position_key"],
                "position_label": spec["position_label"],
                "capacity": capacity_main,
                "occupied": used_main,
                "free": free_main,
                "has_free_slots": free_main > 0,
                "capacity_main": capacity_main,
                "occupied_main": used_main,
                "free_main": free_main,
                "has_free_main_slots": free_main > 0,
                "capacity_reserve": capacity_reserve,
                "occupied_reserve": used_reserve,
                "free_reserve": free_reserve,
                "has_free_reserve_slots": free_reserve > 0,
            }
        )
    return snapshot


def get_training_or_404(db: Session, training_id: int) -> Training:
    training = db.query(Training).filter(Training.id == training_id).one_or_none()
    if training is None:
        raise AppException.not_found(
            code=ErrorCode.TRAINING_NOT_FOUND,
            message='Тренировка не найдена',
            details={'training_id': training_id},
        )
    return training


def _resolve_location_id(
    db: Session,
    *,
    location_id: int | None = None,
    location_name: str | None = None,
) -> int | None:
    normalized = (location_name or '').strip()
    if normalized:
        existing = (
            db.query(Location)
            .filter(func.lower(func.trim(Location.name)) == normalized.lower())
            .first()
        )
        if existing:
            return int(existing.id)

        created = Location(name=normalized, address=normalized)
        db.add(created)
        db.flush()
        return int(created.id)

    return location_id


def _validate_level_range(
    *,
    min_level_name: str | None,
    max_level_name: str | None,
) -> None:
    if min_level_name is None or max_level_name is None:
        return

    min_idx = _LEVEL_ORDER.get(min_level_name)
    max_idx = _LEVEL_ORDER.get(max_level_name)
    if min_idx is None or max_idx is None:
        # Допустимые значения уже валидируются Pydantic-схемой.
        return

    if min_idx > max_idx:
        raise AppException.validation(
            message='Минимальный уровень не может быть выше максимального',
            details={
                'min_level_name': min_level_name,
                'max_level_name': max_level_name,
            },
        )


def create_training(db: Session, data: TrainingCreate) -> Training:
    _validate_level_range(
        min_level_name=data.min_level_name,
        max_level_name=data.max_level_name,
    )

    resolved_location_id = _resolve_location_id(
        db,
        location_id=data.location_id,
        location_name=getattr(data, 'location_name', None),
    )

    normalized_training_type = normalize_training_type(getattr(data, "training_type", None))
    normalized_positions = (
        get_fixed_amplua_positions()
        if normalized_training_type == AMPLUA_TRAINING_TYPE
        else {}
    )

    resolved_capacity_main = (
        amplua_capacity_main(normalized_positions)
        if normalized_training_type == AMPLUA_TRAINING_TYPE
        else max(0, int(getattr(data, "capacity_main", 0) or 0))
    )
    resolved_capacity_reserve = (
        amplua_capacity_reserve(normalized_positions)
        if normalized_training_type == AMPLUA_TRAINING_TYPE
        else max(0, int(getattr(data, "capacity_reserve", 0) or 0))
    )
    primary_image_url, image_gallery = merge_image_gallery(
        image_url=getattr(data, "image_url", None),
        image_urls=getattr(data, "image_urls", None),
    )

    training = Training(
        title=data.title,
        description=data.description,
        start_at=data.start_at,
        duration_minutes=data.duration_minutes,
        min_level_name=data.min_level_name,
        max_level_name=data.max_level_name,
        price=data.price,
        capacity_main=resolved_capacity_main,
        capacity_reserve=resolved_capacity_reserve,
        training_type=normalized_training_type,
        amplua_positions=normalized_positions or None,
        coach_name=data.coach_name,
        image_url=primary_image_url,
        image_urls=image_gallery,
        video_url=data.video_url,
        location_id=resolved_location_id,
        is_cancelled=False,
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return training


def update_training(db: Session, training: Training, data: TrainingUpdate) -> Training:
    update_data = data.model_dump(exclude_unset=True)

    if 'location_name' in update_data:
        location_name = update_data.pop('location_name')
        location_id = update_data.get('location_id', getattr(training, 'location_id', None))
        update_data['location_id'] = _resolve_location_id(
            db,
            location_id=location_id,
            location_name=location_name,
        )

    current_training_type = normalize_training_type(getattr(training, 'training_type', None))
    next_training_type = current_training_type
    if 'training_type' in update_data:
        next_training_type = normalize_training_type(update_data.get('training_type'))
        update_data['training_type'] = next_training_type

    if 'amplua_positions' in update_data:
        update_data.pop('amplua_positions', None)

    if next_training_type == AMPLUA_TRAINING_TYPE:
        next_positions = get_fixed_amplua_positions()
        update_data['amplua_positions'] = next_positions
        update_data['capacity_main'] = amplua_capacity_main(next_positions)
        update_data['capacity_reserve'] = amplua_capacity_reserve(next_positions)
    elif 'training_type' in update_data and next_training_type != AMPLUA_TRAINING_TYPE:
        update_data['amplua_positions'] = None

    if 'image_url' in update_data or 'image_urls' in update_data:
        merged_primary, merged_gallery = merge_image_gallery(
            image_url=update_data.get('image_url', getattr(training, 'image_url', None)),
            image_urls=update_data.get('image_urls', getattr(training, 'image_urls', None)),
        )
        update_data['image_url'] = merged_primary
        update_data['image_urls'] = merged_gallery

    next_min_level = update_data.get('min_level_name', getattr(training, 'min_level_name', None))
    next_max_level = update_data.get('max_level_name', getattr(training, 'max_level_name', None))
    _validate_level_range(
        min_level_name=next_min_level,
        max_level_name=next_max_level,
    )

    for field, value in update_data.items():
        if not hasattr(training, field):
            continue
        setattr(training, field, value)

    db.commit()
    db.refresh(training)
    return training


def delete_training(db: Session, training: Training) -> None:
    db.delete(training)
    db.commit()


def cancel_training(db: Session, training: Training) -> Training:
    training.is_cancelled = True
    db.commit()
    db.refresh(training)
    return training


def restore_training(db: Session, training: Training) -> Training:
    training.is_cancelled = False
    db.commit()
    db.refresh(training)
    return training


def list_trainings(
    db: Session,
    *,
    q: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    location_id: Optional[int] = None,
    coach_name: Optional[str] = None,
    min_level_name: Optional[str] = None,
    max_level_name: Optional[str] = None,
    include_cancelled: bool = False,
    is_cancelled: Optional[bool] = None,
    order: str = 'asc',
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Training], int]:
    query = db.query(Training)

    if q:
        needle = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Training.title.ilike(needle),
                Training.description.ilike(needle),
                Training.coach_name.ilike(needle),
            )
        )

    if date_from is not None:
        query = query.filter(Training.start_at >= date_from)
    if date_to is not None:
        query = query.filter(Training.start_at <= date_to)

    if location_id is not None:
        query = query.filter(Training.location_id == location_id)

    if coach_name:
        query = query.filter(Training.coach_name.ilike(f"%{coach_name.strip()}%"))

    if min_level_name:
        query = query.filter(Training.min_level_name == min_level_name)
    if max_level_name:
        query = query.filter(Training.max_level_name == max_level_name)

    if is_cancelled is not None:
        query = query.filter(Training.is_cancelled.is_(bool(is_cancelled)))
    elif not include_cancelled:
        query = query.filter(Training.is_cancelled.is_(False))

    total = query.count()

    order_clean = (order or 'asc').strip().lower()
    if order_clean not in {'asc', 'desc'}:
        order_clean = 'asc'

    order_expr = Training.start_at.asc() if order_clean == 'asc' else Training.start_at.desc()
    try:
        order_expr = order_expr.nullslast()
    except Exception:
        pass

    items = query.order_by(order_expr).offset(offset).limit(limit).all()

    return items, total
