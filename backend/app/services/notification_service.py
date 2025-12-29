# backend/app/services/notification_service.py
from __future__ import annotations

from typing import Iterable, Optional, Sequence

from sqlalchemy import func, select, text as sa_text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User


def _default_title(ntype: str) -> str:
    t = (ntype or "").upper()
    if t == "TRAINING":
        return "Тренировка"
    if t == "INFO":
        return "Информация"
    if t == "SYSTEM":
        return "Системное уведомление"
    return t or "Уведомление"


async def create_notification(
    db: AsyncSession,
    *,
    user_id: int,
    ntype: str,
    text: str,
    title: Optional[str] = None,
    url: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
) -> Notification:
    # В твоей БД NOT NULL: title/body/text
    final_title = title or _default_title(ntype)
    body = text
    hist_text = text

    notif = Notification(
        user_id=user_id,
        type=ntype,
        title=final_title,
        body=body,
        text=hist_text,
        url=url,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def broadcast_notification(
    db: AsyncSession,
    *,
    ntype: str,
    text: str,
    title: Optional[str] = None,
    url: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    only_active: bool = True,
) -> int:
    q = select(User.id)
    if only_active and hasattr(User, "is_active"):
        q = q.where(User.is_active.is_(True))

    result = await db.execute(q)
    # result.scalars() -> user_ids
    user_ids: Sequence[int] = list(result.scalars().all())

    if not user_ids:
        return 0

    final_title = title or _default_title(ntype)
    rows = [
        dict(
            user_id=uid,
            type=ntype,
            title=final_title,
            body=text,
            text=text,
            url=url,
            entity_type=entity_type,
            entity_id=entity_id,
            is_read=False,
        )
        for uid in user_ids
    ]

    await db.execute(Notification.__table__.insert(), rows)
    await db.commit()
    return len(rows)


async def create_notifications_for_training(
    db: AsyncSession,
    *,
    training_id: int,
    ntype: str,
    text: str,
    title: Optional[str] = None,
    url: Optional[str] = None,
) -> int:
    """
    Делает уведомления всем пользователям, записанным на тренировку.
    Мы специально НЕ завязываемся на конкретную ORM-модель Enrollment — берём user_id через SQL.
    """
    # Поддержка типового enrollments(training_id, user_id)
    res = await db.execute(
        sa_text("SELECT DISTINCT user_id FROM enrollments WHERE training_id = :tid"),
        {"tid": training_id},
    )
    user_ids = [int(r[0]) for r in res.fetchall()]
    if not user_ids:
        return 0

    final_title = title or _default_title(ntype)
    rows = [
        dict(
            user_id=uid,
            type=ntype,
            title=final_title,
            body=text,
            text=text,
            url=url,
            entity_type="TRAINING",
            entity_id=training_id,
            is_read=False,
        )
        for uid in user_ids
    ]
    await db.execute(Notification.__table__.insert(), rows)
    await db.commit()
    return len(rows)


async def list_user_notifications(
    db: AsyncSession,
    *,
    user_id: int,
    limit: int,
    offset: int,
) -> tuple[list[Notification], int]:
    total = await db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user_id))
    q = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    items = list(result.scalars().all())
    return items, int(total or 0)


async def mark_notification_read(db: AsyncSession, *, user_id: int, notification_id: int) -> bool:
    q = (
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
        .execution_options(synchronize_session=False)
    )
    result = await db.execute(q)
    await db.commit()
    return (result.rowcount or 0) > 0
