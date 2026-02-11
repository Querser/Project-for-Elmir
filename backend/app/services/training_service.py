from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import AppException, ErrorCode
from app.models.location import Location
from app.models.training import Training
from app.schemas.training import TrainingCreate, TrainingUpdate


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


def create_training(db: Session, data: TrainingCreate) -> Training:
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
