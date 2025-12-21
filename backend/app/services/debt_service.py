# app/services/debt_service.py
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, ErrorCode
from app.models.debt import Debt


async def list_debts(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    is_closed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Debt], int]:
    """
    Список долгов с фильтрацией по пользователю и статусу.
    """
    query = select(Debt)
    if user_id is not None:
        query = query.where(Debt.user_id == user_id)
    if is_closed is not None:
        query = query.where(Debt.is_closed == is_closed)

    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = int(total_result.scalar_one())

    query = query.order_by(Debt.created_at.desc()).limit(limit).offset(offset)
    res = await db.execute(query)
    items = list(res.scalars().all())
    return items, total


async def close_debt(
    db: AsyncSession,
    *,
    debt_id: int,
    auto_unban_callback=None,
) -> Debt:
    """
    Закрыть долг (например, после успешной оплаты).
    auto_unban_callback(db, user_id) — функция, которая может разбанить пользователя,
    если у него не осталось открытых долгов.
    """
    res = await db.execute(select(Debt).where(Debt.id == debt_id))
    debt = res.scalar_one_or_none()
    if debt is None:
        raise AppException(ErrorCode.NOT_FOUND, "Долг не найден")

    if not debt.is_closed:
        debt.is_closed = True
        debt.closed_at = datetime.now(timezone.utc)
        await db.flush()

        if auto_unban_callback is not None:
            await auto_unban_callback(db, debt.user_id)

        await db.commit()
        await db.refresh(debt)

    return debt
