from __future__ import annotations

# Base должен быть доступен как app.models.Base (у тебя так делает alembic env.py)
from app.models.base import Base

# ВАЖНО: импортируем модули моделей ради регистрации таблиц в Base.metadata
# (это нужно для alembic --autogenerate)
from . import (  # noqa: F401
    user,
    level,
    location,
    training,
    enrollment,
    payment,
    notification,
    ban,
    debt,        
    setting,
    audit_log,
)

__all__ = ["Base"]
