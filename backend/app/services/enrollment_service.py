# app/services/enrollment_service.py
from __future__ import annotations

from datetime import datetime
from typing import Tuple, List

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.training import Training
from app.models.user import User


# Настройки логики (пока нули — ограничения по времени не действуют,
# при необходимости поменяешь на нужное количество часов)
MIN_HOURS_BEFORE_ENROLL = 0     # минимальное количество часов до начала для записи
MIN_HOURS_BEFORE_CANCEL = 0     # минимальное количество часов до начала для отмены


def _ensure_training_exists(db: Session, training_id: int) -> Training:
    """
    Проверяем, что тренировка существует и не отменена.
    """
    training = (
        db.query(Training)
        .filter(Training.id == training_id)
        .one_or_none()
    )
    if training is None:
        raise AppException(
            error_code="NOT_FOUND",
            message="Тренировка не найдена",
        )
    if training.is_cancelled:
        raise AppException(
            error_code="BAD_REQUEST",
            message="Тренировка отменена",
        )
    return training


def _check_time_before(start_at: datetime, min_hours: int, *, error_code: str, message: str) -> None:
    """
    Общая проверка «не поздно ли» для записи/отмены.
    Пока min_hours = 0 — проверка фактически отключена.
    """
    if min_hours <= 0:
        return

    now = datetime.utcnow()
    delta_seconds = (start_at - now).total_seconds()
    if delta_seconds < min_hours * 3600:
        raise AppException(error_code=error_code, message=message)


# ==================== ЗАПИСЬ НА ТРЕНИРОВКУ ====================


def enroll_user_to_training(
    db: Session,
    *,
    user: User,
    training_id: int,
) -> Enrollment:
    """
    Записываем пользователя на тренировку:
    - проверка, что тренировка существует и не отменена;
    - проверка дупликата записи;
    - расчёт: основа или резерв;
    - учёт лимитов capacity_main / capacity_reserve.
    (Проверки уровня, банов и т.п. можно добавить позже.)
    """
    training = _ensure_training_exists(db, training_id)

    # Проверка «не поздно ли записываться»
    _check_time_before(
        training.start_at,
        MIN_HOURS_BEFORE_ENROLL,
        error_code="TOO_LATE",
        message="Запись на тренировку уже недоступна",
    )

    # Уже записан?
    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == user.id,
            Enrollment.training_id == training.id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .one_or_none()
    )
    if existing:
        raise AppException(
            error_code="ALREADY_ENROLLED",
            message="Вы уже записаны на эту тренировку",
        )

    # Сколько людей уже в основе и резерве (с активным статусом)
    main_count = (
        db.query(Enrollment)
        .filter(
            Enrollment.training_id == training.id,
            Enrollment.is_reserve.is_(False),
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .count()
    )

    reserve_count = (
        db.query(Enrollment)
        .filter(
            Enrollment.training_id == training.id,
            Enrollment.is_reserve.is_(True),
            Enrollment.status == EnrollmentStatus.ACTIVE,
        )
        .count()
    )

    # Решаем, куда ставим: основа / резерв
    if main_count < training.capacity_main:
        is_reserve = False
    elif reserve_count < training.capacity_reserve:
        is_reserve = True
    else:
        raise AppException(
            error_code="TRAINING_FULL",
            message="Свободных мест на тренировке нет",
        )

    enrollment = Enrollment(
        user_id=user.id,
        training_id=training.id,
        is_reserve=is_reserve,
        status=EnrollmentStatus.ACTIVE,
        is_paid=False,
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


# ==================== ОТМЕНА ЗАПИСИ ====================


def cancel_enrollment_for_user(
    db: Session,
    *,
    user: User,
    enrollment_id: int,
) -> Enrollment:
    """
    Отмена записи пользователем:
    - проверяем, что запись существует и принадлежит этому пользователю;
    - проверяем, что статус ACTIVE;
    - проверка N часов до тренировки;
    - если отменяется основа — поднимаем первого из резерва в основу.
    """
    enrollment = (
        db.query(Enrollment)
        .filter(Enrollment.id == enrollment_id)
        .one_or_none()
    )
    if enrollment is None or enrollment.user_id != user.id:
        raise AppException(
            error_code="NOT_FOUND",
            message="Запись не найдена",
        )

    training = enrollment.training or _ensure_training_exists(db, enrollment.training_id)

    if enrollment.status != EnrollmentStatus.ACTIVE:
        raise AppException(
            error_code="BAD_REQUEST",
            message="Нельзя отменить эту запись",
        )

    # Проверка «не поздно ли отменять»
    _check_time_before(
        training.start_at,
        MIN_HOURS_BEFORE_CANCEL,
        error_code="TOO_LATE_TO_CANCEL",
        message="Слишком поздно отменять запись",
    )

    enrollment.status = EnrollmentStatus.CANCELLED

    # Если отменяется основа — поднимаем первого из резерва
    if not enrollment.is_reserve:
        reserve = (
            db.query(Enrollment)
            .filter(
                Enrollment.training_id == training.id,
                Enrollment.is_reserve.is_(True),
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
            .order_by(Enrollment.created_at.asc())
            .first()
        )
        if reserve:
            reserve.is_reserve = False
            db.add(reserve)

    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


# ==================== СОСТАВ ТРЕНИРОВКИ ====================


def get_training_roster(
    db: Session,
    training_id: int,
) -> Tuple[List[Enrollment], List[Enrollment]]:
    """
    Возвращает кортеж (main, reserve):
    - main  — список записей в основе;
    - reserve — список записей в резерве.
    """
    _ensure_training_exists(db, training_id)

    main = (
        db.query(Enrollment)
        .filter(
            Enrollment.training_id == training_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
            Enrollment.is_reserve.is_(False),
        )
        .order_by(Enrollment.created_at.asc())
        .all()
    )

    reserve = (
        db.query(Enrollment)
        .filter(
            Enrollment.training_id == training_id,
            Enrollment.status == EnrollmentStatus.ACTIVE,
            Enrollment.is_reserve.is_(True),
        )
        .order_by(Enrollment.created_at.asc())
        .all()
    )

    return main, reserve
