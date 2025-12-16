# backend/app/api/v1/trainings.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.middleware import get_current_user
from app.core.responses import success_response
from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.user import User
from app.schemas.training import TrainingCreate, TrainingUpdate, TrainingPublic
from app.services.training_service import (
    create_training,
    update_training,
    delete_training,
    cancel_training,
    get_training_or_404,
    list_trainings,
)

router = APIRouter(
    prefix="/trainings",
    tags=["trainings"],
)


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Простейшая проверка "админ / не админ".
    """
    if not current_user.is_admin:
        raise AppException(
            error_code="FORBIDDEN",
            message="Доступ разрешён только администраторам",
        )
    return current_user


# ---------- Публичные эндпоинты (пользовательское расписание) ----------


@router.get("")
async def list_public_trainings(
    db: Session = Depends(get_db),
    date_from: Optional[datetime] = Query(
        default=None,
        description="Фильтр: с даты (start_at >= date_from)",
    ),
    date_to: Optional[datetime] = Query(
        default=None,
        description="Фильтр: по дату (start_at <= date_to)",
    ),
    location_id: Optional[int] = Query(
        default=None,
        description="Фильтр по локации (location_id)",
    ),
    coach_name: Optional[str] = Query(
        default=None,
        description="Фильтр по имени тренера (ILIKE %coach_name%)",
    ),
    min_level_name: Optional[str] = Query(
        default=None,
        description="Фильтр по минимальному уровню допуска",
    ),
    max_level_name: Optional[str] = Query(
        default=None,
        description="Фильтр по максимальному уровню допуска",
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    Публичное расписание тренировок для пользователей.
    По умолчанию:
      * скрываем отменённые (is_cancelled = false)
      * можно фильтровать по дате, тренеру, уровню, локации
    """
    trainings, total = list_trainings(
        db,
        date_from=date_from,
        date_to=date_to,
        location_id=location_id,
        coach_name=coach_name,
        min_level_name=min_level_name,
        max_level_name=max_level_name,
        include_cancelled=False,
        limit=limit,
        offset=offset,
    )

    items: List[dict] = [
        TrainingPublic.model_validate(t, from_attributes=True).model_dump()
        for t in trainings
    ]

    return success_response(
        {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.get("/{training_id}")
async def get_training_detail(
    training_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Детальная информация по конкретной тренировке.
    Подходит как для мини-аппа, так и для админки.
    """
    training = get_training_or_404(db, training_id)
    dto = TrainingPublic.model_validate(training, from_attributes=True)
    return success_response(dto.model_dump())


# ---------- Админские эндпоинты ----------


@router.get("/admin", dependencies=[Depends(get_current_admin)])
async def list_admin_trainings(
    db: Session = Depends(get_db),
    date_from: Optional[datetime] = Query(
        default=None,
        description="Фильтр: с даты (start_at >= date_from)",
    ),
    date_to: Optional[datetime] = Query(
        default=None,
        description="Фильтр: по дату (start_at <= date_to)",
    ),
    location_id: Optional[int] = Query(
        default=None,
        description="Фильтр по локации",
    ),
    coach_name: Optional[str] = Query(
        default=None,
        description="Фильтр по имени тренера (ILIKE %coach_name%)",
    ),
    min_level_name: Optional[str] = Query(
        default=None,
        description="Фильтр по минимальному уровню допуска",
    ),
    max_level_name: Optional[str] = Query(
        default=None,
        description="Фильтр по максимальному уровню допуска",
    ),
    include_cancelled: bool = Query(
        default=True,
        description="Показывать отменённые тренировки",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    """
    Список тренировок для админ-панели (с возможностью видеть отменённые).
    """
    trainings, total = list_trainings(
        db,
        date_from=date_from,
        date_to=date_to,
        location_id=location_id,
        coach_name=coach_name,
        min_level_name=min_level_name,
        max_level_name=max_level_name,
        include_cancelled=include_cancelled,
        limit=limit,
        offset=offset,
    )

    items: List[dict] = [
        TrainingPublic.model_validate(t, from_attributes=True).model_dump()
        for t in trainings
    ]

    return success_response(
        {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@router.post("", dependencies=[Depends(get_current_admin)])
async def create_training_admin(
    data: TrainingCreate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Создание тренировки (админ).
    """
    training = create_training(db, data)
    dto = TrainingPublic.model_validate(training, from_attributes=True)
    return success_response(dto.model_dump())


@router.patch("/{training_id}", dependencies=[Depends(get_current_admin)])
async def update_training_admin(
    training_id: int,
    data: TrainingUpdate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Редактирование тренировки (админ).
    """
    training = get_training_or_404(db, training_id)
    training = update_training(db, training, data)
    dto = TrainingPublic.model_validate(training, from_attributes=True)
    return success_response(dto.model_dump())


@router.delete("/{training_id}", dependencies=[Depends(get_current_admin)])
async def delete_training_admin(
    training_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Удаление тренировки (админ).
    При необходимости, вместо физического удаления можно было бы
    просто ставить is_cancelled или отдельный флаг.
    """
    training = get_training_or_404(db, training_id)
    delete_training(db, training)
    return success_response({"deleted_id": training_id})


@router.post("/{training_id}/cancel", dependencies=[Depends(get_current_admin)])
async def cancel_training_admin(
    training_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """
    Отмена тренировки (ставим is_cancelled = true).
    """
    training = get_training_or_404(db, training_id)
    training = cancel_training(db, training)
    dto = TrainingPublic.model_validate(training, from_attributes=True)
    return success_response(dto.model_dump())
