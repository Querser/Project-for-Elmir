from __future__ import annotations

from typing import Tuple, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.setting import Setting


async def list_settings(db: AsyncSession, *, limit: int, offset: int) -> Tuple[List[Setting], int]:
    total = await db.scalar(select(func.count()).select_from(Setting))
    q = select(Setting).order_by(Setting.key.asc()).limit(limit).offset(offset)
    res = await db.execute(q)
    items = list(res.scalars().all())
    return items, int(total or 0)


async def get_setting(db: AsyncSession, *, key: str) -> Optional[Setting]:
    res = await db.execute(select(Setting).where(Setting.key == key))
    return res.scalar_one_or_none()


async def upsert_setting(db, key: str, value: str, description: str | None):
    res = await db.execute(select(Setting).where(Setting.key == key))
    s = res.scalar_one_or_none()

    if s is None:
        # ВАЖНО: НЕ передавать id вообще
        s = Setting(key=key, value=value, description=description)
        db.add(s)
    else:
        s.value = value
        s.description = description

    await db.commit()
    await db.refresh(s)
    return s


async def delete_setting(db: AsyncSession, *, key: str) -> bool:
    obj = await get_setting(db, key=key)
    if obj is None:
        return False
    await db.delete(obj)
    await db.commit()
    return True
