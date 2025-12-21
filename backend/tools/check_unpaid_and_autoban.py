# app/core/deps.py
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import engine  # используем уже настроенный engine

if TYPE_CHECKING:
    from app.models.user import User

# Фабрика сессий поверх существующего engine
_async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для FastAPI: даёт асинхронную сессию БД.
    """
    async with _async_session_factory() as session:
        yield session


def get_current_user(request: Request) -> "User | None":
    """
    Достаём пользователя, которого положил middleware в request.state.user.
    Если пользователь не авторизован по Telegram — вернётся None.
    """
    return getattr(request.state, "user", None)
