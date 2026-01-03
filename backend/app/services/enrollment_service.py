# backend/app/services/enrollment_service.py
from __future__ import annotations

from datetime import datetime
from typing import Tuple, List

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.training import Training
from app.models.user import User
from app.services.ban_service import has_active_ban
from app.services.debt_service import has_open_debts


# Настройки логики (пока нули — ограничения по времени не действуют,
# при необходимости поменяешь на нужное количество часов)
MIN_HOURS_BEFORE_ENROLL = 0
MIN_HOURS_BEFORE_CANCEL = 0


def _ensure_training_exists(db: Session, training_id: int) -> Training:
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
    if min_hours <= 0:
        return

    now = datetime.utcnow()
    delta_seconds = (start_at - now).total_seconds()
    if delta_seconds < min_hours * 3600:
        raise AppException(error_code=error_code, message=message)


def enroll_user_to_training(
    db: Session,
    *,
    user: User,
    training_id: int,
) -> Enrollment:
    """
    Записываем пользователя на тренировку:
    - проверка тренировки (существует/не отменена)
    - проверка ограничений: баны + долги (этап 8)
    - обработка повторной записи (учёт UNIQUE (user_id, training_id)):
        * если уже ACTIVE -> ALREADY_ENROLLED
        * если есть CANCELLED -> реактивируем (UPDATE), а не INSERT (чиним 500)
    - расчёт: основа или резерв
    """

    # ЭТАП 8: запрет при активном бане или открытых долгах
    if has_active_ban(db, user_id=user.id):
        raise AppException(error_code="FORBIDDEN", message="Запись недоступна: у вас активный бан")

    if has_open_debts(db, user_id=user.id):
        raise AppException(error_code="FORBIDDEN", message="Запись недоступна: у вас есть неоплаченный долг")

    training = _ensure_training_exists(db, training_id)

    _check_time_before(
        training.start_at,
        MIN_HOURS_BEFORE_ENROLL,
        error_code="TOO_LATE",
        message="Запись на тренировку уже недоступна",
    )

    # ВАЖНО: ищем ЛЮБУЮ запись (ACTIVE/CANCELLED), потому что в БД UNIQUE (user_id, training_id)
    existing_any = (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == user.id,
            Enrollment.training_id == training.id,
        )
        .one_or_none()
    )

    if existing_any and existing_any.status == EnrollmentStatus.ACTIVE:
        # как раньше
        raise AppException(
            error_code="ALREADY_ENROLLED",
            message="Вы уже записаны на эту тренировку",
        )

    # Считаем заполненность (только ACTIVE!)
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

    if main_count < training.capacity_main:
        is_reserve = False
    elif reserve_count < training.capacity_reserve:
        is_reserve = True
    else:
        raise AppException(
            error_code="TRAINING_FULL",
            message="Свободных мест на тренировке нет",
        )

    # ✅ ФИКС: если запись была CANCELLED — реактивируем её (UPDATE вместо INSERT)
    if existing_any and existing_any.status == EnrollmentStatus.CANCELLED:
        existing_any.status = EnrollmentStatus.ACTIVE
        existing_any.is_reserve = is_reserve
        existing_any.is_paid = False
        # Чтобы очередь/резерв были честными как при новой записи
        existing_any.created_at = datetime.utcnow()

        db.add(existing_any)
        db.commit()
        db.refresh(existing_any)
        return existing_any

    # Если записи не было вообще — создаём новую
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


def cancel_enrollment_for_user(
    db: Session,
    *,
    user: User,
    enrollment_id: int,
) -> Enrollment:
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

    _check_time_before(
        training.start_at,
        MIN_HOURS_BEFORE_CANCEL,
        error_code="TOO_LATE_TO_CANCEL",
        message="Слишком поздно отменять запись",
    )

    enrollment.status = EnrollmentStatus.CANCELLED

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


def get_training_roster(
    db: Session,
    training_id: int,
) -> Tuple[List[Enrollment], List[Enrollment]]:
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
