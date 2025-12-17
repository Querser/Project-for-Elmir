# app/services/rating_service.py
from __future__ import annotations

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.training import Training


def get_leaderboard(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[User], int]:
    """
    Возвращает пользователей, отсортированных по рейтингу (таблица лидеров)
    и общее количество активных пользователей.
    """
    base_q = db.query(User).filter(User.is_active.is_(True))

    total = base_q.count()

    users = (
        base_q
        .order_by(
            User.rating.desc(),
            User.cups.desc(),
            User.id.asc(),  # детерминированный порядок при равных значениях
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return users, total


def get_user_position(db: Session, user: User) -> int:
    """
    Вычисляем место пользователя в рейтинге.
    Пользователь A считается выше B, если:
    - rating больше, или
    - rating равен, но cups больше, или
    - rating и cups равны, но id меньше (чтобы порядок был стабильным).
    """
    if not user.is_active:
        # Неактивным можно возвращать, например, хвост рейтинга,
        # но для простоты считаем место как будто он участвует.
        pass

    ahead_count = (
        db.query(User)
        .filter(
            User.is_active.is_(True),
            or_(
                User.rating > user.rating,
                and_(User.rating == user.rating, User.cups > user.cups),
                and_(
                    User.rating == user.rating,
                    User.cups == user.cups,
                    User.id < user.id,
                ),
            ),
        )
        .count()
    )

    return ahead_count + 1


def get_total_active_users(db: Session) -> int:
    """
    Общее количество активных пользователей.
    """
    return db.query(User).filter(User.is_active.is_(True)).count()


def recalc_ratings_for_training(
    db: Session,
    training: Training,
) -> None:
    """
    Пересчёт рейтинга по результатам конкретной тренировки.

    ⚠️ Правила из реального ТЗ мне неизвестны, поэтому здесь
    реализована *простая примерная логика*:

    - всем с статусом ACTIVE +10 к рейтингу;
    - всем с статусом NO_SHOW -10 к рейтингу.

    Эту функцию можно вызывать из админских сценариев,
    когда тренировка завершена и статусы участников зафиксированы.
    """
    enrollments = (
        db.query(Enrollment)
        .filter(
            Enrollment.training_id == training.id,
            Enrollment.status.in_(
                [EnrollmentStatus.ACTIVE, EnrollmentStatus.NO_SHOW]
            ),
        )
        .all()
    )

    for e in enrollments:
        # На всякий случай проверим, что у юзера есть rating
        if e.user is None:
            continue

        if e.status == EnrollmentStatus.ACTIVE:
            e.user.rating += 10
        elif e.status == EnrollmentStatus.NO_SHOW:
            e.user.rating -= 10

    db.commit()
