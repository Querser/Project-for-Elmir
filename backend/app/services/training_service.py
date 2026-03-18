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
AMPLUA_POSITION_SPECS: tuple[dict[str, str], ...] = (
    {"key": "outside_1", "label": "доигровка"},
    {"key": "outside_2", "label": "доигровка"},
    {"key": "middle_1", "label": "ЦБ"},
    {"key": "middle_2", "label": "ЦБ"},
    {"key": "setter", "label": "связка"},
    {"key": "opposite", "label": "диагональный"},
    {"key": "libero", "label": "либеро"},
)

_AMPLUA_MAIN_STATUSES = {"active", "enrolled", "confirmed"}
_AMPLUA_RESERVED_STATUSES = {"reserve", "waitlist", "standby"}
_AMPLUA_OCCUPIED_STATUSES = _AMPLUA_MAIN_STATUSES | _AMPLUA_RESERVED_STATUSES


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


def normalize_amplua_positions(value: Any) -> dict[str, int]:
    raw = value if isinstance(value, dict) else {}
    normalized: dict[str, int] = {}
    for spec in AMPLUA_POSITION_SPECS:
        key = spec["key"]
        item = raw.get(key, 0)
        try:
            count = int(float(item))
        except Exception:
            count = 0
        normalized[key] = max(0, count)
    return normalized


def get_amplua_position_label(position_key: str | None) -> str:
    key = str(position_key or "").strip()
    for spec in AMPLUA_POSITION_SPECS:
        if spec["key"] == key:
            return spec["label"]
    return ""


def build_amplua_position_snapshot(
    *,
    positions: Any,
    enrollments: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    capacities = normalize_amplua_positions(positions)
    occupied: dict[str, int] = {spec["key"]: 0 for spec in AMPLUA_POSITION_SPECS}

    for enrollment in enrollments or []:
        status = str(getattr(getattr(enrollment, "status", None), "value", getattr(enrollment, "status", "")) or "").strip().lower()
        if status not in _AMPLUA_OCCUPIED_STATUSES:
            continue
        position_key = str(getattr(enrollment, "position_key", "") or "").strip()
        if position_key in occupied:
            occupied[position_key] += 1

    snapshot: list[dict[str, Any]] = []
    for spec in AMPLUA_POSITION_SPECS:
        key = spec["key"]
        capacity = capacities.get(key, 0)
        used = occupied.get(key, 0)
        free = max(capacity - used, 0)
        snapshot.append(
            {
                "key": key,
                "label": spec["label"],
                "capacity": capacity,
                "occupied": used,
                "free": free,
                "has_free_slots": free > 0,
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

    training = Training(
        title=data.title,
        description=data.description,
        start_at=data.start_at,
        duration_minutes=data.duration_minutes,
        min_level_name=data.min_level_name,
        max_level_name=data.max_level_name,
        price=data.price,
        capacity_main=data.capacity_main,
        capacity_reserve=data.capacity_reserve,
        training_type=normalize_training_type(getattr(data, "training_type", None)),
        amplua_positions=normalize_amplua_positions(getattr(data, "amplua_positions", None)),
        coach_name=data.coach_name,
        image_url=data.image_url,
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

    if 'training_type' in update_data:
        update_data['training_type'] = normalize_training_type(update_data.get('training_type'))

    if 'amplua_positions' in update_data:
        update_data['amplua_positions'] = normalize_amplua_positions(update_data.get('amplua_positions'))

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
