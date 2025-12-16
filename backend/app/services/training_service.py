# backend/app/services/training_service.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.training import Training
from app.schemas.training import TrainingCreate, TrainingUpdate


def get_training_or_404(db: Session, training_id: int) -> Training:
    training = db.query(Training).filter(Training.id == training_id).one_or_none()
    if training is None:
        raise AppException(
            error_code="NOT_FOUND",
            message="Тренировка не найдена",
        )
    return training


def create_training(db: Session, data: TrainingCreate) -> Training:
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
        location_id=data.location_id,
    )
    db.add(training)
    db.commit()
    db.refresh(training)
    return training


def update_training(db: Session, training: Training, data: TrainingUpdate) -> Training:
    """
    Частичное обновление тренировки: только те поля, которые реально пришли в запросе.
    """
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if not hasattr(training, field):
            # на всякий случай (extra="forbid" в схеме уже отсечёт лишнее)
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


def list_trainings(
    db: Session,
    *,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    location_id: Optional[int] = None,
    coach_name: Optional[str] = None,
    min_level_name: Optional[str] = None,
    max_level_name: Optional[str] = None,
    include_cancelled: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Training], int]:
    """
    Список тренировок с фильтрами и пагинацией.
    Возвращает (items, total).
    """
    query = db.query(Training)

    if date_from is not None:
        query = query.filter(Training.start_at >= date_from)
    if date_to is not None:
        query = query.filter(Training.start_at <= date_to)

    if location_id is not None:
        query = query.filter(Training.location_id == location_id)

    if coach_name:
        # регистронезависимый поиск по имени тренера
        query = query.filter(Training.coach_name.ilike(f"%{coach_name}%"))

    if min_level_name:
        query = query.filter(Training.min_level_name == min_level_name)
    if max_level_name:
        query = query.filter(Training.max_level_name == max_level_name)

    if not include_cancelled:
        query = query.filter(Training.is_cancelled.is_(False))

    total = query.count()

    items = (
        query.order_by(Training.start_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return items, total
