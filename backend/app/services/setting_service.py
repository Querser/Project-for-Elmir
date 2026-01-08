from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.setting import Setting


def list_settings(db: Session, *, limit: int, offset: int) -> Tuple[List[Setting], int]:
    total = db.scalar(select(func.count()).select_from(Setting))
    q = select(Setting).order_by(Setting.key.asc()).limit(limit).offset(offset)
    res = db.execute(q)
    items = list(res.scalars().all())
    return items, int(total or 0)


def get_setting(db: Session, *, key: str) -> Optional[Setting]:
    res = db.execute(select(Setting).where(Setting.key == key))
    return res.scalar_one_or_none()


def upsert_setting(db: Session, key: str, value: str, description: str | None):
    s = get_setting(db, key=key)

    if s is None:
        # ВАЖНО: id не передаём
        s = Setting(key=key, value=value, description=description)
        db.add(s)
    else:
        s.value = value
        s.description = description

    db.commit()
    db.refresh(s)
    return s


def delete_setting(db: Session, *, key: str) -> bool:
    obj = get_setting(db, key=key)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True
