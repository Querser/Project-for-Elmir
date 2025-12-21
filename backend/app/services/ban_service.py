# app/services/ban_service.py
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ban import Ban, BanType
from app.models.debt import Debt
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.training import Training


async def get_active_ban_for_user(
    db: AsyncSession,
    user_id: int,
) -> Ban | None:
    res = await db.execute(
        select(Ban).where(Ban.user_id == user_id, Ban.is_active.is_(True))
    )
    return res.scalar_one_or_none()


# ---------- Ручной бан / разбан ----------


async def manual_ban_user(
    db: AsyncSession,
    *,
    user_id: int,
    reason: str,
) -> Ban:
    """
    Ручной бан пользователя администратором.
    """
    res = await db.execute(
        select(Ban).where(Ban.user_id == user_id, Ban.is_active.is_(True))
    )
    now = datetime.now(timezone.utc)
    for ban in res.scalars().all():
        ban.is_active = False
        ban.revoked_at = now

    new_ban = Ban(
        user_id=user_id,
        reason=reason,
        type=BanType.MANUAL,
        is_active=True,
        is_auto=False,
    )
    db.add(new_ban)
    await db.commit()
    await db.refresh(new_ban)
    return new_ban


async def manual_unban_user(
    db: AsyncSession,
    *,
    user_id: int,
) -> list[Ban]:
    """
    Разбан пользователя (деактивируем все его активные баны).
    """
    res = await db.execute(
        select(Ban).where(Ban.user_id == user_id, Ban.is_active.is_(True))
    )
    now = datetime.now(timezone.utc)
    bans = list(res.scalars().all())
    for ban in bans:
        ban.is_active = False
        ban.revoked_at = now

    await db.commit()
    return bans


async def list_bans(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    is_active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Ban], int]:
    """
    Список банов с фильтрацией по пользователю и активности.
    """
    query = select(Ban)
    if user_id is not None:
        query = query.where(Ban.user_id == user_id)
    if is_active is not None:
        query = query.where(Ban.is_active.is_(is_active))

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = int(total_result.scalar_one())

    query = query.order_by(Ban.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(query)
    items = list(res.scalars().all())
    return items, total


# ---------- Автобан и взаимодействие с долгами ----------


async def set_auto_ban_for_user(
    db: AsyncSession,
    *,
    user_id: int,
    reason: str,
) -> Ban:
    """
    Создать или обновить авто-бан пользователю.
    """
    res = await db.execute(
        select(Ban).where(Ban.user_id == user_id, Ban.is_active.is_(True))
    )
    now = datetime.now(timezone.utc)
    bans = list(res.scalars().all())

    # Если уже есть активный авто-бан — просто обновим причину и оставим его
    for ban in bans:
        if ban.type == BanType.AUTO:
            ban.reason = reason
            ban.is_auto = True
            return ban
        # Ручные активные баны деактивируем
        ban.is_active = False
        ban.revoked_at = now

    auto_ban = Ban(
        user_id=user_id,
        reason=reason,
        type=BanType.AUTO,
        is_auto=True,
        is_active=True,
    )
    db.add(auto_ban)
    return auto_ban


async def unban_user_if_no_open_debts(
    db: AsyncSession,
    user_id: int,
) -> None:
    """
    Снимаем баны, если у пользователя не осталось открытых долгов.
    Используется при закрытии долга (успешная оплата).
    """
    res = await db.execute(
        select(Debt).where(Debt.user_id == user_id, Debt.is_closed.is_(False))
    )
    open_debt = res.scalars().first()
    if open_debt:
        return

    # Если долгов нет — просто разбаниваем (и авто, и ручные активные)
    await manual_unban_user(db, user_id=user_id)


async def autoban_unpaid_enrollments(
    db: AsyncSession,
    *,
    hours_before_start: int = 3,
) -> int:
    """
    Поиск неоплаченных тренировок за N часов до начала.
    Для каждой:
      * создаётся долг (если его ещё нет),
      * ставится авто-бан пользователю.
    Возвращает количество обработанных записей.
    """
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=hours_before_start)

    query = (
        select(Enrollment, Training)
        .join(Training, Enrollment.training_id == Training.id)
        .where(
            Enrollment.status == EnrollmentStatus.ACTIVE,
            Enrollment.is_paid.is_(False),
            Training.start_at <= window_end,
            Training.start_at > now,
        )
    )

    rows = (await db.execute(query)).all()
    processed = 0

    for enrollment, training in rows:
        # Уже есть долг за эту тренировку?
        debt_res = await db.execute(
            select(Debt).where(
                Debt.user_id == enrollment.user_id,
                Debt.training_id == enrollment.training_id,
                Debt.is_closed.is_(False),
            )
        )
        if debt_res.scalar_one_or_none():
            continue

        # Создаём долг
        debt = Debt(
            user_id=enrollment.user_id,
            training_id=enrollment.training_id,
            amount=float(training.price or 0),
            description=f"Неоплаченная тренировка #{training.id}",
            is_auto=True,
            is_closed=False,
        )
        db.add(debt)

        # Ставим авто-бан
        await set_auto_ban_for_user(
            db,
            user_id=enrollment.user_id,
            reason="Автобан за неоплаченную тренировку",
        )

        processed += 1

    await db.commit()
    return processed
